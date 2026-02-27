import builtins
from dataclasses import dataclass
from types import FrameType
from typing import Any, Literal, Self

from ..errors import FrameAccessError
from .._internal import _NO_VALUE, get_target_frame


type AttrArg = tuple[Literal["attr"], str]
type CallArg = tuple[Literal["call"], tuple[Any, ...], dict[str, Any]]


# Internal mixin for TrigFunc
class _Core:
    def get_user_frame(self, name: str) -> FrameType:
        frame = get_target_frame(name)
        user_frame = frame.f_back
        if user_frame is None:
            raise FrameAccessError()

        return user_frame

    def resolve_value(
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

    def run(self) -> Any:
        if self._trigcall is None:
            raise TypeError("no deferred target to execute")

        obj = _NO_VALUE

        for v in self._trigcall.target:
            if v[0] == "attr":
                name = v[1]
                try:
                    if obj is _NO_VALUE:
                        obj = self.resolve_value(name)
                    else:
                        obj = self.resolve_value(name, obj)
                except NameError:
                    # Retry using the current user frame
                    try:
                        frame = self.get_user_frame("run")
                        if obj is _NO_VALUE:
                            obj = self.resolve_value(name, frame=frame)
                        else:
                            obj = self.resolve_value(name, obj, frame=frame)
                    finally:
                        frame = None
            else:
                # 'call'
                args, kwargs = v[1], v[2]
                obj = obj(*args, **kwargs)

        return obj


@dataclass(frozen=True, slots=True)
class _TrigCall:
    target: tuple[AttrArg | CallArg, ...]
    name: str  # Only for debug

    def add_attr(self, name: str) -> Self:
        return _TrigCall(
            self.target + (("attr", name),),
            f"{self.name}.{name}",
        )

    def add_call(
        self,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Self:
        return _TrigCall(
            self.target + (("call", args, dict(kwargs)),),
            self.name + "()",
        )
