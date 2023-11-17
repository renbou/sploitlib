import warnings
from typing import Optional

from requests.adapters import DEFAULT_POOLBLOCK, HTTPAdapter
from requests_toolbelt.sessions import BaseUrlSession
from urllib3 import HTTPConnectionPool, HTTPSConnectionPool, PoolManager
from urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter("ignore", InsecureRequestWarning)


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
        Note that streaming requests are not supported.
    """

    def __init__(self, base_url: Optional[str] = None, per_request_conn: bool = False):
        super().__init__(base_url=base_url)
        self.verify = False
        self.per_request_conn = per_request_conn

        if per_request_conn:
            self.mount("https://", PerRequestAdapter())
            self.mount("http://", PerRequestAdapter())
            self.headers["Connection"] = None


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
