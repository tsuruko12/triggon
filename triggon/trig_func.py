import inspect
from typing import Any, Callable


class TrigFunc:
  """
  Delays function execution for use with `trigger_return()` or `trigger_func()`.

  Use this wrapper to pass functions without calling them.

  You must assign the instance (e.g., F = TrigFunc()) 
  before calling the trigger function.
  """

  _func: Callable | None

  def __init__(self, func: Callable = None, /) -> None:
    self._func = func

  def __call__(self, *args, **kwargs) -> "TrigFunc":
    if self._func is None:
      raise ValueError("`func` is None")
    
    return TrigFunc(self._func(*args, **kwargs))
    
  def __getattr__(self, name: str) -> Callable[[], Any]:    
    if self._func is not None:
      target = getattr(self._func, name)
    else:
      frame = inspect.currentframe().f_back
      target = frame.f_locals.get(name) or frame.f_globals.get(name)

    if target is None:
        raise AttributeError(f"'{name}' is not a callable function")
    elif not callable(target):
        return TrigFunc(target)
      
    def _wrapper(*args, **kwargs) -> Callable[[], Any]:
      return lambda: target(*args, **kwargs)
    return _wrapper
