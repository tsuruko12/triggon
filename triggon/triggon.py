from types import FrameType
from typing import Any

from .trig_func import TrigFunc
from ._internal._err_handler import (
    _count_symbol,
    _ensure_after_type,
    _ensure_index_type,
    _ensure_label_type,
    _ensure_var_type,
    _normalize_arg_types, 
)
from ._internal._exceptions import (
  InvalidArgumentError, 
  SYMBOL,
  _ExitEarly,
)
from ._internal._methods import _bind_to_triggon
from ._internal._sentinel import _NO_VALUE
from ._internal._var_update import _is_delayed_func


class Triggon:
    debug: bool
    _trigger_flags: dict[str, bool]
    _new_values: dict[str, tuple[Any, ...]]
    _org_values: dict[str, list[Any]]
    _var_refs: dict[str, tuple[str, ...] | list[tuple[str, ...]]]
    _delay_info: dict[str, str]
    _disable_flags: dict[str, bool]
    _return_values: tuple[bool, Any] | None
    _file_name: str
    _lineno: int
    _frame: FrameType

    # new_values: 各ラベルはタプルで統一されてる
    # org_values: 各ラベルのインデックスには、リストの中に値が入っている。
    #              未設定の場合はNone。
    # var_refs: 各ラベルのインデックスには、文字列が入ったタプル、
    #             または複数のそのタプルが入ったリストが入っている。
    #             未設定の場合はNone。
    # delay_info: 各ラベルは1つまたは2つの遅延用のフレーム情報を持つリストを保持する。
    #               遅延されていない場合はNone。

    def __init__(
        self, label: str | dict[str, Any], /, new: Any = None, 
        *, debug: bool | str | list[str] | tuple[str, ...] = False,
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

      Keyword Args:
          debug:
              Trueに設定した場合、ラベルのトレースをリアルタイムで出力します。 
              ラベル名が渡された場合は、そのラベルのみを出力します。
      """

      self._trigger_flags = {}
      self._new_values = {}
      self._org_values = {}
      self._var_refs = {}  
      self._delay_info = {}
      self._disable_flags = {}   
      self._return_values = None
      self._file_name = None
      self._lineno = None
      self._frame = None

      changed_items = _normalize_arg_types(label, new)
      self._scan_dict(changed_items)

    def _scan_dict(self, arg_dict: dict[str, Any]) -> None:      
      for key, value in arg_dict.items():          
          index = _count_symbol(key)

          if index != 0:
              raise InvalidArgumentError(
                  f" '{key}' の先頭にある '*' をすべて取り除いてください。"
                  "インデックスを指定するためには、 "
                  "リスト/タプル内に任意のインデックスの位置に値を配置してください。"
              )
  
          self._add_new_label(key, value)

      if not isinstance(self.debug, bool):
        self._ensure_debug_type()

    def _add_new_label(self, label: str, value: Any) -> None:
      # タプルで統一
      if isinstance(value, (list, tuple)):
        length = len(value)
        if length == 0:
          # 空の配列は単一の値として扱う
          length = 1
          self._new_values[label] = (value,)
        else:
          self._new_values[label] = tuple(value)
      else:
        length = 1
        self._new_values[label] = (value,)

      self._trigger_flags[label] = False
      self._disable_flags[label] = False
      # 遅延トリガー用の [発動frame_info, 解除frame_info]。遅延なしならNone
      self._delay_info[label] = [None, None]
        
      # 送られた値のインデックスの数だけNoneを設定する
      # (lengthは必ず１以上になる)
      self._org_values[label] = [None] * length
      self._var_refs[label] = [None] * length

    def set_trigger(
        self, 
        label: str | list[str] | tuple[str, ...] = None, 
        /, 
        *, 
        all: bool = False,
        index: int = None, 
        cond: str = None, 
        after: int | float = None,
    ) -> None:
      """
      ラベルを有効化にします。

      switch_var()によって変数が登録されている場合のみ、
      値の切り替えが行われます。

      Keyword Args:
          all:
              全てのラベルを有効化にします。

          index:
              指定されている全てのラベルのインデックス値を設定します。

              Note:
                  変数がすでにswitch_var()で登録されている場合にのみ適用されます。
                  switch_lit()の場合は適用されません。

          cond:
              ラベルを有効にする条件を設定します。
              有効な比較式である必要があります（例: "x > 10", "obj.count == 5"）。
              その結果がTrueの場合のみラベルを有効化にします。

          after:
              ラベルを有効化するまでの遅延時間（秒）を設定します。

              Note:
                  実行は指定時刻より約0.011秒遅れて行われます。
      """

      _ensure_index_type(index)
      _ensure_after_type(after)
      if not isinstance(all, bool):
        raise TypeError("'all' はbool値でなくてはなりません。")  
      
      if all:
        labels = self._trigger_flags.keys()
      else:
        if label is None:
          raise TypeError("ラベルを指定してください。")
        _ensure_label_type(label)
        
        if isinstance(label, (list, tuple)):
          labels = [v.lstrip(SYMBOL) for v in label]
        else: 
          labels = [label.lstrip(SYMBOL)]

        self._ensure_label_exists(labels)

      if index is not None:
          self._compare_value_counts(labels, index)

      self._update_or_skip(labels, index, cond, after) 
      self._clear_frame()

    def is_triggered(
        self, *label: str,
    ) -> bool | list[bool] | tuple[bool, ...]:
      """
      指定されたラベルが有効状態の場合Trueを返し、そうでない場合はFalseを返します。

      複数のラベルが指定された場合は、入力の型（list または tuple）に合わせて
      ブール値の配列を返します。
      """

      _ensure_label_type(label, unpack=True)
      self._ensure_label_exists(label, unpack=True)

      if isinstance(label[0], list):
        return [self._trigger_flags[v] for v in label[0]]
      if isinstance(label[0], tuple):
        return tuple(self._trigger_flags[v] for v in label[0])
      if len(label) > 1:
        return tuple(self._trigger_flags[v] for v in label)
      return self._trigger_flags[label[0]]

    def switch_lit(
        self, label: str | list[str] | tuple[str, ...], /, org: Any, 
        *, index: int = None,
    ) -> Any:
      """
      ラベルが有効の場合、インスタンス作成時に登録した
      ラベルのインデックスに対応する値に切り替えます。

      また、関数への切り替えにも対応しています。
      TrigFuncによって遅延されている関数は、実行されその戻り値が返されます。

      Note:
          複数のラベルが与えられ、かつ複数が有効の場合、
          配列内でインデックスが小さい方が優先されます。
      """

      self._get_marks(init=True) # デバッグ用

      _ensure_label_type(label)
      _ensure_index_type(index)

      if isinstance(label, (list, tuple)):
        for v in label:
          stripped_label = v.lstrip(SYMBOL)
          self._ensure_label_exists(stripped_label)

          if self._trigger_flags[stripped_label]:
            label = v
            break

        # トリガーが有効なラベルがなかった場合
        if not isinstance(label, str):
          self._get_marks(label, index, org, strip=True)
          return org
      
      name = label.lstrip(SYMBOL)
      self._ensure_label_exists(name)

      if index is None:
        index = _count_symbol(label)
      self._compare_value_counts(name, index)

      flag = self._trigger_flags[name]
      if not flag:
        ret_value = org
        self._get_marks(name, index, org)
      else:
        ret_value = self._new_values[name][index] 
        self._get_marks(name, index, org, ret_value)
    
      if _is_delayed_func(ret_value):
          return ret_value()
      return ret_value

    def switch_var(
          self, label: str | dict[str, Any], var: Any = None, /, 
          *, index: int = None,
    ) -> Any:
        """
        指定されたラベルのインデックに変数の登録を行います。

        最初の登録、かつラベルのいずれかが有効な場合に、
        その変数の値をインスタンス作成時に登録された値に変更します。
 
        式やリテラル以外の変数のみに対応しています。

        Returns:
            単一のラベルが渡された場合に、与えられた変数の値を返します。
            それ以外は、Noneを返します。

            値がTrigFuncによる遅延関数だった場合は、実行しその戻り値を返します。
        """

        # 複数のインデックスが渡せる用に実装されてますが、
        # 実際には使い道がないためエラーになります

        changed_items = _normalize_arg_types(label, var, index)
        has_looped = False

        # タプルに統一
        if index is not None:
          if isinstance(index, int):
            i = (index,)
          elif isinstance(index, range):
            i = tuple(index)
          else:
            i = index

        if len(changed_items) == 1:
          single_key = True
        else:
          single_key = False

        for key, value in changed_items.items():
            name = key.lstrip(SYMBOL)

            if index is None:
              i = (_count_symbol(key),)

            if not has_looped:
              init_flag = self._init_or_not(name, i)        
              if not init_flag:
                if not single_key:
                  continue
                self._clear_frame()

                if _is_delayed_func(value):
                  return value()                
                return value
              
            has_looped = True

            trig_flag = self._trigger_flags[name]
            var_ref = self._var_refs[name][i[0]]  

            if not trig_flag and self._delay_info[name][0] is None:
              if not single_key:
                continue     

              self._clear_frame()

              if _is_delayed_func(value):
                return value()    
              return value

            if self._delay_info[name][0] is None:   
              if isinstance(var_ref, list):
                  for v in var_ref:
                      self._update_var_value(
                          v, label, i[0], self._new_values[name][i[0]],
                      )
              else:
                  self._update_var_value(
                      var_ref, label, i[0], self._new_values[name][i[0]],
                  )
              ret_value = self._new_values[name][i[0]]
            else:
              ret_value = value

            if single_key:
              self._clear_frame()

              if _is_delayed_func(ret_value):
                return ret_value()
              return ret_value

        self._clear_frame()

    def is_registered(
        self, *variable: str,
    ) -> bool | list[bool] | tuple[bool, ...]:
      """
      指定された変数が登録済みの場合Trueを返し、そうでない場合はFalseを返します。

      複数のラベルが指定された場合は、入力の型（list または tuple）に合わせて
      ブール値の配列を返します。
      """

      vars = _ensure_var_type(variable)
      self._get_target_frame("is_registered")

      result = []
      for var in vars:
        is_glob = False
        if "." in var:
          (left, right) = var.split(".")

          class_inst = self._frame.f_locals.get(left)
          if class_inst is None:
              glob_inst = self._frame.f_globals.get(left)
              if glob_inst is None:
                result.append(False)
                continue
              is_glob = True
              class_inst = glob_inst.__name__
          elif isinstance(class_inst, type):
            is_glob = True
            class_inst = class_inst.__name__
          result.append(
            self._check_var_refs(class_inst, right, is_glob)
          )
        else:
          try:
            self._frame.f_globals[var]
          except KeyError:
            result.append(False)
          else:
            result.append(self._check_var_refs(var)) 

      self._clear_frame()

      if len(result) == 1:
        return result[0]
      return result

    def revert(
          self, 
          label: str | list[str] | tuple[str, ...] = None, 
          /, 
          *, 
          all: bool = False, 
          disable: bool = False,
          cond: str = None, 
          after: int | float = None,
    ) -> None:
      """
      ラベルを無効化にします。

      Keyword Args:
          all:
              全てのラベルを無効化にします。

          disable:
              永続的にラベルを無効化にします。
              この状態のラベルは、set_trigger()で無視されます。

          cond:
              ラベルを無効にする条件を設定します。
              有効な比較式である必要があります（例: "x > 10", "obj.count == 5"）。
              その結果がTrueの場合のみラベルを無効化にします。

          after:
              ラベルを無効化するまでの遅延時間（秒）をで設定します。

              Note:
                  実行は指定時刻より約0.011秒遅れて行われます。
      """

      _ensure_after_type(after)
      if not isinstance(disable, bool):
        raise TypeError("'disable' はbool値でなくてはなりません。")
      if not isinstance(all, bool):
        raise TypeError("'all' はbool値でなくてはなりません。")

      if all:
        labels = tuple(self._trigger_flags.keys())
      else:
        if label is None:
          raise InvalidArgumentError("ラベルを指定してください。")
        _ensure_label_type(label)

        if isinstance(label, (list, tuple)):
          labels = [v.lstrip(SYMBOL) for v in label]
        else:
          labels = [label.lstrip(SYMBOL)]

        self._ensure_label_exists(labels)

      self._revert_or_skip(labels, disable, cond, after)  
      self._clear_frame()
    
    def exit_point(self, func: TrigFunc) -> Any:
      """
      trigger_return()によって実行された早期リターンを、
      `func` に渡された関数のところまで処理を戻します。

      Returns:
          trigger_return()の戻り値を返します。
      """

      if not _is_delayed_func(func):
        raise TypeError(
          "'func' はTriguFuncインスタンスでラップされた関数である必要があります。"
        )

      try:
          return func()
      except _ExitEarly:
          if _is_delayed_func(self._return_values):
              return self._return_values()     
          return self._return_values

    def trigger_return(
        self, label: str | list[str] | tuple[str, ...], /, 
        ret: Any = _NO_VALUE, *, index: int = None,
    ) -> Any:
        """
        ラベルが有効の場合、早期リターンを実行と共に
        クラスインスタンス作成時に設定された値を返します。

        Returns:
            クラスインスタンス作成時に設定された値を返します。
            'ret' に値が渡された場合は、それが優先されます。
        """

        _ensure_label_type(label)
        _ensure_index_type(index)

        if isinstance(label, str):
           label = [label]

        for v in label:
          name = v.lstrip(SYMBOL)
          self._ensure_label_exists(name)

          if index is None:
            index = _count_symbol(label)
          self._compare_value_counts(name, index)

          if not self._trigger_flags[name]:
              return 

          if ret is _NO_VALUE:
            ret_value = self._new_values[name][index]
          else:
            ret_value = ret                  
          self._return_values = ret_value

          self._get_target_frame("exit_point", has_exit=True)
          self._debug_trig_return(name)

          raise _ExitEarly 
        
    def trigger_func(
        self, label: str | list[str] | tuple[str, ...], /, func: TrigFunc,
    ) -> Any:
        """
        ラベルのいずれかが有効の場合、'func' に渡された関数を実行します。

        Returns:
            指定された関数の戻り値を返します。
        """

        if not _is_delayed_func(func):
          raise TypeError(
            "'func' はTriguFuncインスタンスでラップされた関数である必要があります。"
          )
        _ensure_label_type(label)

        if isinstance(label, str):
           label = [label]

        for v in label:
          name = v.lstrip(SYMBOL)
          self._ensure_label_exists(name)

          if self._trigger_flags[name]:
              self._debug_trig_func(name, func)              
              return func()


_bind_to_triggon(Triggon)
