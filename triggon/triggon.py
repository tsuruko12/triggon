from types import FrameType
from typing import Any

from .trig_func import TrigFunc
from ._internal import (
  _debug,
  _err_handler,
  _var_analysis,
  _var_update,
  _switch_var,
)
from ._internal._err_handler import (
  _check_label_type,
  _handle_arg_types, 
)
from ._internal._exceptions import (
  InvalidArgumentError,
  SYMBOL,
  _ExitEarly,
)
from ._internal._sentinel import _no_value


class Triggon:
    debug: bool
    _debug_var: dict[str, tuple[int, str] | list[tuple[int, str]]]
    _trigger_flag: dict[str, bool]
    _new_value: dict[str, tuple[Any, ...]]
    _org_value: dict[str, list[Any]]
    _var_list: dict[str, tuple[str, ...] | list[tuple[str, ...]]]
    _disable_label: dict[str, bool]
    _return_value: tuple[bool, Any] | None
    _file_name: str
    _lineno: int
    _frame: FrameType

    # `new_value`: 各ラベルはタプルで統一されてる
    # `org_value`: 各ラベルのインデックスには、リストの中に値が入っている。
    #              未設定の場合はNone。
    # `var_list`: 各ラベルのインデックスには、文字列が入ったタプル、
    #             または複数のそのタプルが入ったリストが入っている。
    #             未設定の場合はNone。

    def __init__(
        self, label: str | dict[str, Any], /, new: Any=None, 
        *, debug: bool=False,
    ) -> None:
      """
      ラベルとその値を登録します。
 
      値は配置位置に基づいてインデックスが割り振られます。
      配列を１つの値として設定したい場合は、さらに別の配列に入れてください。

      対応形式:
      - label, value
      - label, [value]
      - label, (value,)
      - {label: value}
      - {label: [value]}
      - {label: (value,)}
      """

      self.debug = debug
      self._trigger_flag = {}
      self._new_value = {}
      self._org_value = {}
      self._var_list = {}  
      self._disable_label = {}   
      self._return_value = None
      self._file_name = None
      self._lineno = None
      self._frame = None

      change_list = _handle_arg_types(label, new)
      self._scan_dict(change_list)

    def _scan_dict(self, arg_dict: dict[str, Any]) -> None:      
      for key, value in arg_dict.items():          
          index = self._count_symbol(key)

          if index != 0:
              raise InvalidArgumentError(
                  f" `{key}`の先頭にある `*` をすべて取り除いてください。 "
                  "インデックスを指定するためには, "
                  "リスト/タプル内に任意のインデックスの位置に値を配置してください。"
              )

          self._add_new_label(key, value)

    def _add_new_label(self, label: str, value: Any, /) -> None:
      # 値はタプルで統一させる
      if isinstance(value, (list, tuple)):
        length = len(value)

        if length == 0:
          # 空の配列は単一の値として扱う
          length = 1
          self._new_value[label] = (value,)
        else:
          self._new_value[label] = tuple(value)
      else:
        length = 1
        self._new_value[label] = (value,)

      self._trigger_flag[label] = False
      self._disable_label[label] = False
        
      self._trigger_flag[label] = False
      self._disable_label[label] = False

      # 送られた値のインデックスの数だけ`None`を設定する
      # (`length`は必ず１以上になる)
      self._org_value[label] = [None] * length
      self._var_list[label] = [None] * length

    def set_trigger(
        self, label: str | list[str] | tuple[str, ...], /, *, cond: str=None,
    ) -> None:
      """
      引数のラベルのフラグをTrueに設定します。
 
      `alter_var()`によって変数が登録されてる場合, 
      この関数内で値が更新されます。

      キーワード引数の`cond`には比較文を設定できます。
      （例： `"x > 10"`, `"obj.count == 5"`)
      結果がTrueの場合にラベルのフラグをTrueに設定します。
      """

      if isinstance(label, (list, tuple)):
        for name in label:
          _check_label_type(name, allow_dict=False)    
          self._check_label_flag(name, cond)
      else:
        _check_label_type(label, allow_dict=False)
        self._check_label_flag(label, cond)
      
      self._clear_frame()

    def switch_lit(
        self, label: str | list[str] | tuple[str, ...], /, org: Any, 
        *, index: int=None,
    ) -> Any:
      """
      引数のラベルのフラグがTrueの場合、その値を変更します。
 
      変数以外の式やリテラルのみ対応しています。

      Note:
        複数のラベルを渡す際に、同じラベル名が含まれている場合、  
        `set_trigger()` はインデックスに関係なくラベル単位でフラグを True にするため、  
        配列内でインデックスが小さい方のラベルが優先されます。 
        また、異なるラベルで複数のフラグが同時に True になった場合も同様です。
      """

      cur_functions = ["switch_lit", "alter_literal"] # ベータ後に変更予定

      _check_label_type(label, allow_dict=False)

      if isinstance(label, (list, tuple)):
        for v in label:
          stripped_label = v.lstrip(SYMBOL)
          self._check_exist_label(stripped_label)

          if self._trigger_flag[stripped_label]:
            label = v
            break

        # トリガーが有効なラベルがなかった場合
        if not isinstance(label, str):
          return org
      
      name = label.lstrip(SYMBOL)
      self._check_exist_label(name)

      if index is None:
        index = self._count_symbol(label)
      self._compare_value_counts(name, index)

      flag = self._trigger_flag[name]

      if not flag:
        ret_value = org
        new_val = _no_value # デバッグ用
      else:
        ret_value = self._new_value[name][index] 
        new_val = self._new_value[name][index] # デバッグ用

      if self.debug:
        self._get_target_frame(cur_functions)
        self._print_val_debug(name, index, flag, org, new_val)

      return ret_value

    def switch_var(
          self, label: str | dict[str, Any], var: Any=None, /, 
          *, index: int=None,
    ) -> None | Any:
        """
        引数のラベルのフラグがTrueの場合、
        その変数の値を変更します。
 
        変数のみ対応しています。（式やリテラル以外）
 
        対応変数の種類:
        - グローバル変数
        - クラス変数
        """

        change_list = _handle_arg_types(label, var, index)
        init_flag = False

        if len(change_list) == 1:
          # 単一のラベルの場合
          label = next(iter(change_list))
          name = label.lstrip(SYMBOL)     

          if index is None:
            index = self._count_symbol(label)

          if not init_flag:
            init_flag = self._init_or_not(name, index)

          trig_flag = self._trigger_flag[name]
          vars = self._var_list[name][index]

          if not trig_flag:
            self._clear_frame()
            return var
          elif not init_flag:
             return var
          
          self._update_var_value(
            vars, name, index, self._new_value[name][index],
          )     
          self._clear_frame()

          return var
        else:
           # 複数のラベルの場合（辞書）
          if index is not None:
            raise InvalidArgumentError(
              "`dict`で渡す場合は、`index`引数は使用できません。" 
              "代わりに`*`を使用してください。" 
            )
          
          for key in change_list.keys():
            name = key.lstrip(SYMBOL)
            index = self._count_symbol(key)

            if not init_flag:
              self._check_exist_label(name)
              self._compare_value_counts(name, index)

            if not init_flag:
              init_flag = self._init_or_not(name, index)
            
            if not init_flag:
              continue

            trig_flag = self._trigger_flag[name]
            vars = self._var_list[name][index]  

            if not trig_flag:
              continue          

            self._update_var_value(
              vars, name, index, self._new_value[name][index],
            )
            
          self._clear_frame()


    def revert(
          self, label: str | list[str] | tuple[str, ...]=None, /, 
          *, all: bool=False, disable: bool=False,
    ) -> None:
      """
      `set_trigger()`によってTrueにされたフラグを、Falseに戻します。

      一括で全てのラベルのフラグを無効にしたい場合は、`all`引数をTrueに設定してください。
      `disable`がTrueに設定された場合、永続的にフラグを無効化します。
      """
      
      if label is None:
        if not all:
          raise InvalidArgumentError("引数にラベルを設定してください。")

        for key in self._new_value.keys():
          self._revert_label(key, disable)      
      elif isinstance(label, (list, tuple)):
        for name in label:
          self._revert_label(name, disable)
      else:
        self._revert_label(label, disable)  

      self._clear_frame()      

    def _revert_label(self, label: str, disable: bool) -> None:
      _check_label_type(label, allow_dict=False)

      name = label.lstrip(SYMBOL)
      self._check_exist_label(name)

      if not self._trigger_flag[name]:
        return

      if disable:
        state = "disable" # デバッグ用
        self._disable_label[name] = True
      else:
        state = "inactive" # デバッグ用
      self._trigger_flag[name] = False

      self._label_has_var(name, "revert", to_org=True)

      if self.debug:
        self._get_target_frame("revert")
        self._print_flag_debug(name, state)    
    
    def exit_point(self, label: str, func: TrigFunc, /) -> None | Any:
      """
      引数と同じラベルの`trigger_return()`によって実行された早期リターンは、
      `func`に渡された関数のところまで処理が戻ります。
      """

      name = label.lstrip(SYMBOL)
      self._check_exist_label(name)

      try:
          return func()
      except _ExitEarly:
          if not self._return_value[0]:
              return self._return_value[1]
          
          print(self._return_value[1])

    def trigger_return(
        self, label: str, /, *, index: int=None, do_print: bool=False,
    ) -> None | Any:
        """
        引数のラベルのフラグがTrueの場合、
        早期リターンを実行と共に設定された値を返します。
 
        `do_print`がTrueの場合、早期リターンで設定された値を出力します。
        値が文字列でない場合、`InvalidArgumentError`が発生します。
        """

        name = label.lstrip(SYMBOL)
        self._check_exist_label(name)

        if index is None:
           index = self._count_symbol(label)

        if not self._trigger_flag[name]:
            return 
            
        if do_print:
            if not isinstance(self._new_value[name][index], str):
              raise InvalidArgumentError(
                 "値は文字列である必要がありますが、"
                 f"`{type(self._new_value[name][index]).__name__}`が渡されました。"
              )         
        self._return_value = (do_print, self._new_value[name][index])

        if self.debug:
          self._get_target_frame("trigger_return")
          self._print_trig_debug(name, "Return")

        self._get_target_frame("exit_point", has_exit=True)

        raise _ExitEarly 
        
    def trigger_func(self, label: str, func: TrigFunc, /) -> None | Any:
        """
        引数のラベルのフラグがTrueの場合、`func`に渡された関数を実行します。
        """

        name = label.lstrip(SYMBOL)
        self._check_exist_label(name)

        if self._trigger_flag[name]:
            if self.debug:
              self._get_target_frame("trigger_func")
              self._print_trig_debug(name, "Trigger a function") 
                    
            return func()

    # 旧関数
    alter_literal = switch_lit
    alter_var = switch_var


modules = [_debug, _err_handler, _var_analysis, _var_update, _switch_var]

for module in modules:
  for name, func in vars(module).items():
      if callable(func):
          setattr(Triggon, name, func)
