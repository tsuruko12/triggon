from .label_flag_switch import LabelFlagController
from .refs.registry import RefRegistrar
from .value_update import ValueUpdater


class _Core(LabelFlagController, ValueUpdater, RefRegistrar):
    """Core mixin bundle."""