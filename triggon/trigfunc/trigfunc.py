from __future__ import annotations
from typing import Any, Mapping, Self

from ._core import TrigCall, TrigFuncCore


TRIGFUNC_ATTR = "__trigfunc__"


class TrigFunc(TrigFuncCore):
    """
    Records attribute and call chains for deferred execution.

    This class does not execute targets or perform name resolution
    or callability checks when building the chain.
    Attribute access and calls are recorded as a chain
    and evaluated only when the chain is executed.

    Examples:
        >>> chain_1 = TrigFunc().func()
        >>> f = TrigFunc()
        >>> chain_2 = f.obj.method(10)
        >>> chain_3 = f.A(10).method(20)

    Raises:
        TypeError: If a call is recorded before any target is bound.
        NameError: If a root name cannot be resolved during execution.
        AttributeError: If a root name cannot be resolved during execution.
    """

    _trigcall: TrigCall | None
    _f_locals: Mapping[str, Any]
    _f_globals: Mapping[str, Any]

    # Marker for functions that use this class
    __trigfunc__ = True

    def __init__(self) -> None:
        self._trigcall = None

        frame = self.get_user_frame("__init__")
        self._f_locals = frame.f_locals
        self._f_globals = frame.f_globals
        frame = None

    @classmethod
    def _clone_with(
        cls,
        tricall: TrigCall,
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
            new_trigcall = TrigCall((("attr", name),), name)
        else:
            new_trigcall = self._trigcall.add_attr(name)

        return type(self)._clone_with(
            new_trigcall,
            self._f_locals,
            self._f_globals,
        )
