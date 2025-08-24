import builtins
import inspect
from typing import Any, Callable

from ._internal._exceptions import InvalidArgumentError
from ._internal._sentinel import _NO_VALUE


class TrigFunc:
  """
  Call a function without executing it immediately.

  For better performance, create and assign an instance first 
  before calling the target function.

  To work correctly in functions of the Triggon class, always add '()' 
  when calling the target function (e.g., F = TrigFunc(), F.test()).
  """

  _func: Any | None

  def __init__(
      self, _func: Any | None = _NO_VALUE, _chain: bool = False,
  ) -> None:
    if _func is not _NO_VALUE and not _chain:
      raise InvalidArgumentError("Arguments cannot be passed.")
    
    self._func = _func

  def __call__(self, *args: Any, **kwargs: Any) -> "TrigFunc":
    if self._func is _NO_VALUE:
      raise TypeError("No function was provided.")
    return TrigFunc(self._func(*args, **kwargs), _chain=True)
    
  def __getattr__(self, name: str) -> Callable[..., Any] | "TrigFunc":  
    if self._func is not _NO_VALUE:
      target = getattr(self._func, name, None)
      if target is None:
        target = getattr(builtins, name, None)
    else:
      frame = inspect.currentframe().f_back
      target = frame.f_locals.get(name)

      if target is None:
        target = frame.f_globals.get(name)
        if target is None:
          target = getattr(builtins, name, None)

      frame = None

    if target is None:
        raise AttributeError(f"'{name}' is not a callable function.")
    if not callable(target):
        return TrigFunc(target, _chain=True)
      
    def _wrapper(*args: Any, **kwargs: Any) -> Callable[..., Any]:
      func = lambda: target(*args, **kwargs)
      func._trigfunc = True # For checking if this class is used.
      
      # For debug
      func._trigfunc_name = name
      func._trigfunc_args = args
      func._trigfunc_kwargs = kwargs

      return func
    return _wrapper
