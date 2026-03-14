from .debug.logger import DebugLogger
from .label import LabelValidator
from .debug.setup import LogSetup


class _Internal(LabelValidator, LogSetup, DebugLogger):
    """Internal mixin bundle."""
