from . import TrigFunc
from typing import Any


class Triggon:
    def __init__(
        self, label: str | dict[str, Any], /, new: Any = None, 
        *, debug: bool = False,
    ) -> None: ...

    def set_trigger(
        self, label: str | list[str] | tuple[str, ...], /, 
        *, cond: str = None, after: int | float = None,
    ) -> None: ...

    def alter_literal(
        self, label: str | list[str] | tuple[str, ...], /, org: Any, 
        *, index: int = None,
    ) -> Any: ...

    def switch_lit(
        self, label: str | list[str] | tuple[str, ...], /, org: Any, 
        *, index: int = None,
    ) -> Any: ...

    def alter_var(
          self, label: str | dict[str, Any], var: Any = None, /, 
          *, index: int = None,
    ) -> None | Any: ...

    def switch_var(
          self, label: str | dict[str, Any], var: Any = None, /, 
          *, index: int = None,
    ) -> None | Any: ...

    def revert(
            self, 
            label: str | list[str] | tuple[str, ...], 
            /, 
            *, 
            all: bool = False, 
            disable: bool = False, 
            after: int | float = None,
    ) -> None: ...

    def exit_point(self, label: str, func: TrigFunc, /) -> None | Any: ...    

    def trigger_return(
        self, label: str, /, ret: Any=None, 
        *, index: int=None, do_print: bool=False,
    ) -> None | Any: ...

    def trigger_func(self, label: str, func: TrigFunc, /) -> None | Any: ...