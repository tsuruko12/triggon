from importlib.metadata import version

from .api import Triggon
from .errors.public import (
    FrameAccessError,
    InvalidArgumentError,
    RollbackNotSupportedError,
    RollbackSourceError,
    UnregisteredLabelError,
    UpdateError,
)
from .trigfunc import TrigFunc

__version__ = version("triggon")

__all__ = [
    "Triggon",
    "TrigFunc",
    "FrameAccessError",
    "InvalidArgumentError",
    "RollbackNotSupportedError",
    "RollbackSourceError",
    "UnregisteredLabelError",
    "UpdateError",
]
