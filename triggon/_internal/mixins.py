from .debug import DebugLogger
from .label import LabelValidator
from .log_setup import LogSetup


class _Internal(LabelValidator, LogSetup, DebugLogger):
    """Internal mixin bundle."""
