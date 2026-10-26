"""The effect registry: every scene of the demo, in running order."""

from .loader import Loader
from .logo import Logo
from .plasma import Plasma
from .mode7 import Mode7
from .tunnel import Tunnel
from .scroller import Scroller
from .vector import VectorTorus
from .road import NeonRoad
from .copper import Copper
from .fire import Fire
from .finale import Finale

#: the show, in the order the scenes play
ALL = (Loader, Logo, Plasma, Mode7, Tunnel, Scroller,
       VectorTorus, NeonRoad, Copper, Fire, Finale)

BY_NAME = {cls.name: cls for cls in ALL}


def build(names=None):
    """Instantiate effects; ``names=None`` means the whole show."""
    if names is None:
        return [cls() for cls in ALL]
    return [BY_NAME[n]() for n in names]


__all__ = ["ALL", "BY_NAME", "build",
           "Loader", "Logo", "Plasma", "Mode7", "Tunnel", "Scroller",
           "VectorTorus", "NeonRoad", "Copper", "Fire", "Finale"]
