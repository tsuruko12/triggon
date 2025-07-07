import inspect
from typing import Any, Callable


class TrigFunc:
  """
  `trigger_return()` と `trigger_func()`を使う際に、
  引数に入れる関数の実行を遅延させます。
 
  対象関数を包んで引数に渡してください。
 
  必ずクラスインスタンス変数を作成してから使ってください。
  (例： F = TrigFunc()) 
  """

  _func: Callable | None

  def __init__(self, func: Callable=None) -> None:
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
