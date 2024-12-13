from dataclasses import dataclass
from typing import Callable, Optional, Union


class Default:
    """Marker to specify that the default value should be used."""

    def __repr__(self) -> str:
        return "default"


default = Default()


@dataclass
class Config:
    """SploitLib configuration class for setting various defaults."""

    session_per_request_conns: Union[Default, bool] = default
    session_round_robin_conns: Union[Default, int] = default
    session_user_agent: Union[Default, Callable[[], Optional[str]]] = default
    cache_proxy_url: Optional[str] = None
    cache_auth_key: Optional[str] = None
    cache_duration: Optional[str] = None

    def set(self, cfg: "Config"):
        """Set this config from another one."""
        self.session_per_request_conns = cfg.session_per_request_conns
        self.session_round_robin_conns = cfg.session_round_robin_conns
        self.session_user_agent = cfg.session_user_agent
        self.cache_proxy_url = cfg.cache_proxy_url
        self.cache_auth_key = cfg.cache_auth_key
        self.cache_duration = cfg.cache_duration


sploitcfg = Config()
