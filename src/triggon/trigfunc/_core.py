from __future__ import annotations

import builtins
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import FrameType
from typing import Any, Literal, cast

from .._internal.frames import get_target_frame
from .._internal.sentinel import _NO_VALUE

type AttrArg = tuple[Literal["attr"], str]
type CallArg = tuple[Literal["call"], tuple[Any, ...], dict[str, Any]]


class _Core:
    """Internal mixin for TrigFunc"""

    _trigcall: _TrigCall | None
    _f_locals: Mapping[str, Any]
    _f_globals: Mapping[str, Any]

    def _resolve_value(
        self,
        name: str,
        obj: Any = _NO_VALUE,
        frame: FrameType | None = None,
    ) -> Any:
        if frame is None:
            f_locals = self._f_locals
            f_globals = self._f_globals
        else:
            f_locals = frame.f_locals
            f_globals = frame.f_globals

        if obj is _NO_VALUE:
            value = f_locals.get(name, _NO_VALUE)
            if value is _NO_VALUE:
                value = f_globals.get(name, _NO_VALUE)
            if value is _NO_VALUE:
                value = getattr(builtins, name, _NO_VALUE)
            if value is _NO_VALUE:
                raise NameError(f"{name!r} is not defined")
        else:
            value = getattr(obj, name, _NO_VALUE)
            if value is _NO_VALUE:
                raise AttributeError(f"{type(obj).__name__!r} object has no attribute {name!r}")

        return value

    def _run(self) -> Any:
        if self._trigcall is None:
            raise TypeError("no deferred target to execute")
        if self._trigcall.target[-1][0] != "call":
            raise TypeError("deferred target must end with a function or method call")

        obj = _NO_VALUE

        for v in self._trigcall.target:
            if v[0] == "attr":
                name = v[1]
                try:
                    if obj is _NO_VALUE:
                        obj = self._resolve_value(name)
                    else:
                        obj = self._resolve_value(name, obj)
                except NameError:
                    # retry using the current user frame
                    try:
                        frame = get_target_frame()
                        if obj is _NO_VALUE:
                            obj = self._resolve_value(name, frame=frame)
                        else:
                            obj = self._resolve_value(name, obj, frame=frame)
                    finally:
                        frame = None
            elif v[0] == "call":
                args, kwargs = v[1], v[2]
                obj = cast(Callable[..., Any], obj)(*args, **kwargs)
            else:
                raise AssertionError(f"unreachable kind key: {v[0]!r}")

        return obj


@dataclass(frozen=True, slots=True)
class _TrigCall:
    target: tuple[AttrArg | CallArg, ...]
    name: str  # only for debug

    def add_attr(self, name: str) -> _TrigCall:
        attr_arg: AttrArg = ("attr", name)
        return _TrigCall(
            self.target + (attr_arg,),
            f"{self.name}.{name}",
        )

    def add_call(
        self,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> _TrigCall:
        call_arg: CallArg = ("call", args, dict(kwargs))

        arg_parts = [repr(arg) for arg in args]
        kwarg_parts = [f"{k}={v!r}" for k, v in kwargs.items()]
        joined = ", ".join(arg_parts + kwarg_parts)

        return _TrigCall(
            self.target + (call_arg,),
            f"{self.name}({joined})",
        )
