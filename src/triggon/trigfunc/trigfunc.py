from collections.abc import Mapping
from typing import Any, Self

from ._core import _Core, _TrigCall
from .._internal.frames import get_target_frame

TRIGFUNC_ATTR = "__trigfunc__"


class TrigFunc(_Core):
    """Record deferred attribute and call chains.

    `TrigFunc` stores attribute access and call steps without resolving or
    executing them while the chain is being built. The recorded chain can be
    passed to APIs that execute deferred targets later.

    Examples:
        >>> chain_1 = TrigFunc().func()
        >>> f = TrigFunc()
        >>> chain_2 = f.obj.method(10)
        >>> chain_3 = f.A(10).method(20)

    Raises:
        TypeError:
            If a call is recorded before any target is bound, or if the
            deferred chain is executed before a target is bound or does not end
            with a call.
        NameError:
            If a root name in the deferred chain does not exist when the chain
            is executed.
        AttributeError:
            If an attribute in the deferred chain does not exist when the chain
            is executed.
    """

    _trigcall: _TrigCall | None
    _f_locals: Mapping[str, Any]
    _f_globals: Mapping[str, Any]

    # Marker for functions that use this class
    __trigfunc__ = True

    def __init__(self) -> None:
        self._trigcall = None

        frame = get_target_frame()
        self._f_locals = frame.f_locals
        self._f_globals = frame.f_globals
        frame = None

    @classmethod
    def _clone_with(
        cls,
        tricall: _TrigCall,
        f_locals: Mapping[str, Any],
        f_globals: Mapping[str, Any],
    ) -> Self:
        new_cls = cls.__new__(cls)
        new_cls._trigcall = tricall
        new_cls._f_locals = f_locals
        new_cls._f_globals = f_globals
        return new_cls

    def __call__(self, *args: Any, **kwargs: Any) -> Self:
        if self._trigcall is None:
            raise TypeError("TrigFunc instance is not bound to a callable")

        new_trigcall = self._trigcall.add_call(args, kwargs)
        return type(self)._clone_with(
            new_trigcall,
            self._f_locals,
            self._f_globals,
        )

    def __getattr__(self, name: str) -> Self:
        if self._trigcall is None:
            new_trigcall = _TrigCall((("attr", name),), name)
        else:
            new_trigcall = self._trigcall.add_attr(name)

        return type(self)._clone_with(
            new_trigcall,
            self._f_locals,
            self._f_globals,
        )
