from collections.abc import MutableMapping
from dataclasses import dataclass
from threading import Timer
from typing import Any, NamedTuple, TypedDict

from ..keys import GLOB_VAR
from .aliases import LogFile, TargetLabels, VarKey, Verbosity

# NamedTuples


class VarRef(NamedTuple):
    ref_id: int
    var_name: str


class AttrRef(NamedTuple):
    ref_id: int
    attr_name: str
    parent_obj: Any
    full_name: str


class RefMeta(NamedTuple):
    file: str
    func_name: str
    orig_val: Any
    idx: int


class Callsite(NamedTuple):
    file: str
    lineno: int
    func_name: str
    lasti: int | None


# TypedDicts


class DebugConfig(TypedDict):
    TRIGGON_LOG_VERBOSITY: Verbosity
    TRIGGON_LOG_FILE: LogFile
    TRIGGON_LOG_LABELS: TargetLabels


class RefsByKind(TypedDict):
    loc_var: list[VarRef]
    glob_var: list[VarRef]
    attr: list[AttrRef]


# Data Classes


@dataclass(slots=True)
class DelayState:
    is_delay: bool = False
    timer: Timer | None = None
    cur_timer_id: int = 0
    labels: tuple[str, ...] | None = None


@dataclass(slots=True)
class FrameContext:
    f_globals: MutableMapping[str, Any]
    f_locals: MutableMapping[str, Any]
    callsite: Callsite

    def get_var_scope(self, kind: VarKey) -> MutableMapping[str, Any]:
        if kind == GLOB_VAR:
            return self.f_globals
        else:
            # 'loc_var'
            return self.f_locals
