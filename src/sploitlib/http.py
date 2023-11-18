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
            if sploitcfg.per_request_conn == default:
                per_request_conn = False
            else:
                per_request_conn = sploitcfg.per_request_conn

        if user_agent is None:
            if sploitcfg.user_agent == default:
                user_agent = UserAgent.default
            else:
                user_agent = sploitcfg.user_agent

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
