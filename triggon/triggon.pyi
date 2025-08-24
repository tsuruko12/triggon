from typing import Any

from . import TrigFunc


class Triggon:
    def __init__(
        self, label: str | dict[str, Any], /, new: Any = None, 
        *, debug: bool | str | list[str] | tuple[str, ...] = False,
    ) -> None: ...

    def set_trigger(
        self, 
        label: str | list[str] | tuple[str, ...] = None, 
        /, 
        *, 
        all: bool = False,
        index: int = None, 
        cond: str = None, 
        after: int | float = None,
    ) -> None: ...

    def is_triggered(
            self, *label: str,
    ) -> bool | list[bool] | tuple[bool, ...]: ...

    def switch_lit(
        self, label: str | list[str] | tuple[str, ...], /, org: Any, 
        *, index: int = None,
    ) -> Any: ...

    def switch_var(
          self, label: str | dict[str, Any], var: Any = None, /, 
          *, index: int = None,
    ) -> Any: ...

    def is_registered(
        self, *variable: str,
    ) -> bool | list[bool] | tuple[bool, ...]: ...

    def revert(
            self, 
            label: str | list[str] | tuple[str, ...], 
            /, 
            *, 
            all: bool = False, 
            disable: bool = False, 
            cond: str = None,
            after: int | float = None,
    ) -> None: ...

    def exit_point(self, func: TrigFunc) -> Any: ...    

    def trigger_return(
        self, label: str | list[str] | tuple[str, ...], /, 
        ret: Any = ..., *, index: int = None,
    ) -> Any: ...

    def trigger_func(
        self, label: str | list[str] | tuple[str, ...], /, func: TrigFunc,
    ) -> Any: ...

class TrigFunc:
    def __init__(self) -> None: ...