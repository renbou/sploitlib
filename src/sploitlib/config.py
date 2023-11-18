from dataclasses import dataclass
from typing import Callable, Optional, Union


class Default:
    """Marker to specify that the default value should be used."""

    pass


default = Default()


@dataclass
class Config:
    """SploitLib configuration class for setting various defaults."""

    per_request_conn: Union[Default, bool] = default
    user_agent: Union[Default, Callable[[], Optional[str]]] = default


sploitcfg = Config()
