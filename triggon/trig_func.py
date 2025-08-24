import builtins
import inspect
from typing import Any, Callable

from ._internal._exceptions import InvalidArgumentError
from ._internal._sentinel import _NO_VALUE


class TrigFunc:
  """
  関数を即時に実行せずに呼び出します。

  パフォーマンスを向上させるため、
  対象の関数を呼び出す前にインスタンスを作成して変数に代入してください。

  Triggonクラスの関数で正常に機能させるためには、
  対象の関数を呼び出す際に必ず '()' を付けてください（例: F = TrigFunc(), F.test())。
  """

  _func: Any | object

  def __init__(
      self, _func: Any | object = _NO_VALUE, _chain: bool = False,
  ) -> None:
    if _func is not _NO_VALUE and not _chain:
      raise InvalidArgumentError("引数は渡せません。")

  def __call__(self, *args: Any, **kwargs: Any) -> "TrigFunc":
    if self._func is _NO_VALUE:
      raise TypeError("関数が渡されていません。")
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
        raise AttributeError(f"'{name}' は呼び出し可能の関数ではありません。")
    if not callable(target):
        return TrigFunc(target, _chain=True)
      
    def _wrapper(*args: Any, **kwargs: Any) -> Callable[..., Any]:
      func = lambda: target(*args, **kwargs)
      func._trigfunc = True # このクラスが使われてるかの確認用

      # デバッグ用
      func._trigfunc_name = name
      func._trigfunc_args = args
      func._trigfunc_kwargs = kwargs

      return func
    return _wrapper