from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Self

from ._internal._types.aliases import (
    DebugArg,
    IndexArg,
    LabelArg,
    LabelToRefs,
    NameArg,
)

@dataclass(slots=True)
class EarlyReturnResult:
    triggered: bool = False
    value: Any = None

class Triggon:
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
    def rollback(targets: NameArg | None = None) -> Any: ...
    @contextmanager
    def capture_return(self) -> Any: ...
    def trigger_return(
        self,
        labels: LabelArg,
        /,
        *,
        indices: IndexArg | None = None,
        value: Any = None,
    ) -> Any: ...
    def trigger_call(
        self,
        labels: LabelArg,
        /,
        target: TrigFunc,
    ) -> Any: ...

class TrigFunc:
    def __init__(self) -> None: ...
