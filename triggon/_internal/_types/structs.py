from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Timer
from typing import Any, NamedTuple, TypedDict

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
    scope_name: str
    orig_val: Any
    idx: int


class Callsite(NamedTuple):
    file: str
    lineno: int
    scope_name: str
    lasti: int | None


# TypedDicts


class DebugConfig(TypedDict):
    TRIGGON_LOG_VERBOSITY: int
    TRIGGON_LOG_FILE: Path | None
    TRIGGON_LOG_LABELS: Sequence[str] | None


class RefsByKind(TypedDict):
    glob_var: list[VarRef]
    attr: list[AttrRef]


# Data Classes


@dataclass(slots=True)
class DelayState:
    is_delay: bool = False
    timer: Timer | None = None
    cur_timer_id: int = 0
    labels: tuple[str, ...] | None = None

