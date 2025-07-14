from types import FrameType
from typing import Any

from ._exceptions import (
    _ExitEarly,
    InvalidArgumentError,
    _check_label_type,
    _compare_value_counts,
    _count_symbol,
    _handle_arg_types,
    LABEL_TYPE_ERROR,
    SYMBOL,
)
from . import _debug
from . import _var_analysis
from . import _var_update
from .trig_func import TrigFunc


class Triggon:
    debug: bool
    _debug_var: dict[str, tuple[int, str] | list[tuple[int, str]]]
    _trigger_flag: dict[str, bool]
    _new_value: dict[str, tuple[Any]]
    _org_value: dict[str, tuple[Any]]
    _var_list: dict[str, tuple[str]]
    _disable_label: dict[str, bool]
    _id_list: dict[str, int | tuple[int]]
    _return_value: tuple[bool, Any] | None = None
    _lineno: int = None
    _frame: FrameType = None

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
      self._id_list = {}

      change_list = _handle_arg_types(label, new)
      self._scan_dict(change_list)

    def _scan_dict(self, arg_dict: dict[str, Any]) -> None:      
      for key, value in arg_dict.items():          
          label = key.lstrip(SYMBOL)
          index = _count_symbol(key)

          if index != 0:
              raise InvalidArgumentError(
                  f" `{key}`の先頭にある '*' をすべて取り除いてください。 "
                  "インデックスを指定するために, "
                  "リスト/タプル内に任意のインデックスの位置に値を配置してください。"
              )

          try:
            self._new_value[label]

            raise InvalidArgumentError(
              f"`{label}`はすでに登録済みです"
              "この関数では重複したラベルは登録できません。"
            ) 
          except KeyError:
            self._add_new_label(label, value)

    def _add_new_label(self, label: str, value: Any, /) -> None:
      if isinstance(value, (list, tuple)):
        length = len(value)
      else:
        length = 1

      if isinstance(value, list) and length > 1: 
        self._new_value[label] = tuple(value)
      elif isinstance(value, tuple) and length > 1:
        self._new_value[label] = value
      elif isinstance(value, list) and length == 1:
        if isinstance(value[0], (list, tuple)):
          self._new_value[label] = value
        else:
          self._new_value[label] = (value[0],)
      elif isinstance(value, tuple) and length == 1:
        if isinstance(value[0], (list, tuple)):
          self._new_value[label] = value 
        else:
          self._new_value[label] = value
      else:
        # 配列ではない単一の値
        self._new_value[label] = (value,)
        
      self._trigger_flag[label] = False
      self._disable_label[label] = False

      # 送られた値のインデックスの数だけNoneを設定する
      self._org_value[label] = [None] * length
      self._var_list[label] = [None] * length
      self._id_list[label] = [None] * length

    def set_trigger(
        self, label: str | list[str] | tuple[str, ...], /, *, cond: str=None,
    ) -> None:
      """
      引数のラベルのフラグをTrueに設定します。
 
      `alter_var()`によって変数が登録されてる場合, 
      この関数内で値が更新されます。

      キーワード引数の`cond`には比較文を設定できます。
      （例： `"x > 10"`, `"obj.count == 5"`）
      結果がTrueの場合にラベルのフラグをTrueに設定します。
      """

      if isinstance(label, (list, tuple)):
        for name in label:
          if not isinstance(name, str):
             raise InvalidArgumentError(LABEL_TYPE_ERROR)

          self._check_label_flag(name, cond)
      elif isinstance(label, str):
        self._check_label_flag(label, cond)       
      else:
        raise InvalidArgumentError(LABEL_TYPE_ERROR)
      
      self._clear_frame()

    def switch_lit(
        self, label: str, /, org: Any, *, index: int=None,
    ) -> Any:
      """
      引数のラベルのフラグがTrueの場合、その値を変更します。
 
      変数以外の式やリテラルのみ対応しています。
      """

      _check_label_type(label)
      
      name = label.lstrip(SYMBOL)
      self._check_exist_label(name)

      if index is None:
        index = _count_symbol(label)
      _compare_value_counts(self._new_value[name], index)

      self._org_value[name][index] = org
      flag = self._trigger_flag[name]

      if self.debug:
        self._get_target_frame(["switch_lit", "alter_literal"]) # ベータ後に変更予定
        self._print_val_debug(name, index, flag, org)
        self._clear_frame()

      if not flag:
        return self._org_value[name][index]

      return self._new_value[name][index]

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

        cur_functions = ["switch_var", "alter_var"] # ベータ後に変更予定

        (change_list, arg_type) = _handle_arg_types(label, var, index, True)
        init_flag = False

        if len(change_list) == 1:
          # 単一のラベルの場合
          label = next(iter(change_list))
          _check_label_type(label)

          name = label.lstrip(SYMBOL)
          self._check_exist_label(name)

          if index is None:
            index = _count_symbol(label)
          _compare_value_counts(self._new_value[name], index)

          if (
            self._var_list[name][index] is None 
            or self._is_new_var(name, index, var)
          ):
            self._get_target_frame(cur_functions)
            self._lineno = self._frame.f_lineno     

            self._store_org_value(name, index, change_list[label])   

            # 変数保存の初回処理
            self._init_arg_list(change_list, arg_type, index)
            
            init_flag = True

          if init_flag:
            self._find_match_var(name, index)

          trig_flag = self._trigger_flag[name]
          vars = self._var_list[name][index]

          if not trig_flag:
            if self.debug:
              self._get_target_frame(cur_functions)

              self._print_var_debug(
                vars, name, index, trig_flag, change_list[label],
              )   
            self._clear_frame()

            return var
          elif not init_flag:
             return var

          self._update_var_value(vars, self._new_value[name][index])  

          if self.debug:
            self._print_var_debug(
              vars, name, index, trig_flag, change_list[label], 
              self._new_value[name][index], change=True,
            )
          self._clear_frame()

          return var
        else:
           # 複数のラベルの場合（辞書）
          if index is not None:
            raise InvalidArgumentError(
              "Cannot use the `index` keyword with a dictionary. " 
              "Use '*' in the label instead." 
            )
          
          for key, val in change_list.items():
            _check_label_type(key)
            
            name = key.lstrip(SYMBOL)
            index = _count_symbol(key)

            self._check_exist_label(name)
            _compare_value_counts(self._new_value[name], index)

            if self._org_value[name][index] is None:
              self._store_org_value(name, index, val)

            if (
               not init_flag
               and (self._var_list[name][index] is None 
               or self._is_new_var(name, index, val))
            ):    
              self._get_target_frame(cur_functions)
              self._lineno = self._frame.f_lineno

               # 変数保存の初回処理
              self._init_arg_list(change_list, arg_type)
              self._find_match_var(name, index)

              init_flag = True
            
            if not init_flag:
              continue

            trig_flag = self._trigger_flag[name]
            vars = self._var_list[name][index]  

            if not trig_flag:
              if self.debug:
                self._get_target_frame(cur_functions)
                self._print_var_debug(vars, name, index, trig_flag, val)

              continue          

            self._update_var_value(vars, self._new_value[name][index])

            if self.debug:
              self._get_target_frame(cur_functions)

              self._print_var_debug(
                vars, name, index, trig_flag, val, 
                self._new_value[name][index], change=True,
              )
            
          self._clear_frame()

    def revert(
          self, label: str | list[str] | tuple[str, ...], /, 
          *, disable: bool=False,
    ) -> None:
      """
      引数のラベルのフラグをFalseに設定します。
      'disable'がTrueに設定された場合、永続的にフラグをFalseにします。
      """
      
      if isinstance(label, (list, tuple)):
        for name in label:
          if not isinstance(name, str):
            raise InvalidArgumentError(LABEL_TYPE_ERROR)
          
          self._revert_label(name, disable)
      elif isinstance(label, str):
        self._revert_label(label, disable)
      else:
        raise InvalidArgumentError(LABEL_TYPE_ERROR)   

　  def _revert_label(self, label: str, disable: bool) -> None:
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

      self._label_has_var(name, "revert", True)

      if self.debug:
        self._get_target_frame("revert")
        self._print_flag_debug(name, state)    
        self._clear_frame()  
    
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
           index = _count_symbol(label)

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


for name, func in vars(_var_analysis).items():
    if callable(func):
        setattr(Triggon, name, func)


for name, func in vars(_debug).items():
    if callable(func):
        setattr(Triggon, name, func)


for name, func in vars(_var_update).items():
    if callable(func):
        setattr(Triggon, name, func)
