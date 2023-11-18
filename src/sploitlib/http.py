import warnings
from typing import Callable, Optional

import requests
from requests.adapters import DEFAULT_POOLBLOCK, HTTPAdapter
from requests_toolbelt.sessions import BaseUrlSession
from requests_toolbelt.utils.user_agent import UserAgentBuilder
from urllib3 import HTTPConnectionPool, HTTPSConnectionPool, PoolManager
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util import SKIP_HEADER

from .config import default, sploitcfg

warnings.simplefilter("ignore", InsecureRequestWarning)


class UserAgent:
    """
    Class containing common user agent configurations as static methods.
    """

    @staticmethod
    def none() -> Optional[str]:
        """
        User Agent configuration which always return `urllib3.util.SKIP_HEADER`,
        meaning that no user agent will be sent.
        """
        return SKIP_HEADER

    @staticmethod
    def default() -> Optional[str]:
        """
        User Agent configuration which returns the default
        python-requests/version user agent string.
        """
        return UserAgentBuilder("python-requests", requests.__version__).build()


class RequestsSession(BaseUrlSession):
    """
    A `requests.Session` providing:
    - a base URL to combine all request URLs with using `urllib.parse.urljoin`;
    - disabled SSL verification by default;
    - customizable User-Agent header with a few commonly used configurations provided;
    - per-request connections to avoid HTTP stream recovery in network analysis tools.

    :param base_url: The base URL to use for all requests.
    :param per_request_conn: Whether to use per-request connections,
        which automatically close after the request has completed.
        The "Connection" header is set to None on the session instance,
        meaning it will not be sent. If instead "close" should be sent,
        override the "Connection" header on the headers property manually.
    :param user_agent: Callable returning an optional string which will be
        used for all requests made to set a user agent string.
        Some common configurations are provided through the UserAgent class.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        per_request_conn: Optional[bool] = None,
        user_agent: Optional[Callable[[], Optional[str]]] = None,
    ):
        super().__init__(base_url=base_url)

        if per_request_conn is None:
            if sploitcfg.session_per_request_conn == default:
                per_request_conn = False
            else:
                per_request_conn = sploitcfg.session_per_request_conn

        if user_agent is None:
            if sploitcfg.session_user_agent == default:
                user_agent = UserAgent.default
            else:
                user_agent = sploitcfg.session_user_agent

        self.verify = False
        self.per_request_conn = per_request_conn
        self.user_agent = user_agent

        if per_request_conn:
            self.mount("https://", PerRequestAdapter())
            self.mount("http://", PerRequestAdapter())
            self.headers["Connection"] = None

    def prepare_request(self, request: requests.Request, *args, **kwargs):
        """
        Prepare the request, generating the complete URL and setting the User-Agent header.
        """

        request.headers["User-Agent"] = self.user_agent()
        return super().prepare_request(request, *args, **kwargs)


class CacheProxySession(requests.Session):
    """
    A `requests.Session` which sends all HTTP and HTTPS requests
    through the `S4DFarm` cacheproxy in order to cache the responses.
    Note that currently caching is performed by URL, so all requests
    to the same URL should result in similar responses,
    i.e. not depend on cookies and other parameters.

    :param proxy_url: URL of the cacheproxy instance.
    :param auth_key: Authorization key for the cacheproxy.
    :param duration: Caching duration specified as Go's `time.Duration` string representation.
    """

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        auth_key: Optional[str] = None,
        duration: Optional[str] = None,
    ):
        super().__init__()

        if proxy_url is None:
            if sploitcfg.cache_proxy_url is None:
                raise ValueError(
                    "proxy_url is None and sploitcfg.cache_proxy_url is None too, at least one must be set"
                )

            proxy_url = sploitcfg.cache_proxy_url

        if auth_key is None:
            if sploitcfg.cache_auth_key is None:
                raise ValueError(
                    "auth_key is None and sploitcfg.cache_auth_key is None too, at least one must be set"
                )

            auth_key = sploitcfg.cache_auth_key

        if duration is None:
            if sploitcfg.cache_duration is None:
                raise ValueError(
                    "duration is None and sploitcfg.cache_duration is None too, at least one must be set"
                )

            duration = sploitcfg.cache_duration

        self.headers = {
            "X-Cache-Auth-Key": auth_key,
            "X-Cache-Duration": duration,
        }

        self.proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }

        self.verify = False


class PerRequestAdapter(HTTPAdapter):
    """
    Overridden `HTTPAdapter` that users a `urllib3.PoolManager` with
    our custom connection pools, which always close the returned connections.
    Automatic closing doesn't work with proxies (for now?).
    """

    def init_poolmanager(
        self, connections, maxsize, block=DEFAULT_POOLBLOCK, **pool_kwargs
    ):
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            strict=True,
            **pool_kwargs,
        )

        self.poolmanager.pool_classes_by_scheme = {
            "http": PerRequestHTTPPool,
            "https": PerRequestHTTPSPool,
        }


class PerRequestHTTPPool(HTTPConnectionPool):
    def _put_conn(self, conn):
        if conn:
            conn.close()


class PerRequestHTTPSPool(HTTPSConnectionPool):
    def _put_conn(self, conn):
        if conn:
            conn.close()
