from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import logging
import threading
from typing import Any, Self

from ._internal._types.aliases import (
    DebugArg,
    DelayKey,
    IndexArg,
    LabelArg,
    LabelToRefs,
    NameArg,
)
from ._internal._types.structs import (
    DebugConfig,
    DelayState,
    RefMeta,
    RefsByKind,
)

@dataclass(slots=True)
class EarlyReturnResult:
    triggered: bool = False
    value: Any = None

class Triggon:
    debug: DebugConfig
    _logger: logging.Logger | None
    _label_is_active: dict[str, bool]
    _label_delay_state: dict[str, dict[DelayKey, DelayState]]
    _label_is_perm_disabled: dict[str, bool]
    _new_values: dict[str, tuple[Any, ...]]
    _label_refs: dict[str, RefsByKind]
    _id_meta: dict[int, RefMeta]
    _latest_id: int
    _return_val_stack: list[Any]
    _lock: threading.Lock
    @classmethod
    def from_label(
        cls,
        label: str,
        /,
        new_values: Any,
        *,
        debug: DebugArg = False,
    ) -> Self: ...
    @classmethod
    def from_labels(
        cls,
        label_values: Mapping[str, Any],
        *,
        debug: DebugArg = False,
    ) -> Self: ...
    def add_label(self, label: str, /, new_values: Any = None) -> None: ...
    def add_labels(self, label_values: Mapping[str, Any], /) -> None: ...
    def set_trigger(
        self,
        labels: LabelArg | None = None,
        /,
        *,
        indices: IndexArg | None = None,
        all: bool = False,
        cond: str = "",
        after: int | float = 0,
        reschedule: bool = False,
    ) -> None: ...
    def is_triggered(self, *labels: LabelArg, match_all: bool = True) -> bool: ...
    def switch_lit(
        self,
        labels: LabelArg,
        /,
        original_val: Any,
        *,
        indices: IndexArg | None = None,
    ) -> Any: ...
    def register_ref(
        self,
        label: str,
        /,
        name: str,
        *,
        index: int | None = None,
    ) -> None: ...
    def register_refs(self, label_to_refs: LabelToRefs, /) -> None: ...
    def unregister_refs(self, names: NameArg, /, *, labels: LabelArg | None = None) -> None: ...
    def is_registered(
        self,
        *names: NameArg,
        label: str | None = None,
        match_all: bool = True,
    ) -> bool: ...
    def revert(
        self,
        labels: LabelArg | None = None,
        /,
        *,
        all: bool = False,
        disable: bool = False,
        cond: str = "",
        after: int | float = 0,
        reschedule: bool = False,
    ) -> None: ...
    @staticmethod
    @contextmanager
    def rollback(targets: NameArg | None = None) -> Generator[None]: ...
    @contextmanager
    def capture_return(self) -> Generator[EarlyReturnResult]: ...
    def trigger_return(
        self,
        labels: LabelArg,
        /,
        *,
        value: Any = None,
    ) -> None: ...
    def trigger_call(
        self,
        labels: LabelArg,
        /,
        target: TrigFunc,
    ) -> Any: ...

class TrigFunc:
    def __init__(self) -> None: ...
