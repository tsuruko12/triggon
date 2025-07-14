import inspect
from typing import Any

from ._exceptions import SYMBOL


def _store_org_value(
    self, label: str, index: int, org_value: Any,
) -> None:
    if isinstance(org_value, (list, tuple)):
      self._org_value[label][index] = []  

      for v in org_value:
          self._org_value[label][index].append(v)
    else:
      self._org_value[label][index] = org_value

def _update_var_value(
    self, 
    var_ref: tuple[Any] | list[tuple[Any]], update_value: Any,
) -> None:
    # 変数情報:
    # - グローバル変数 -> (行番号, 変数名)
    # - クラス変数 -> (行番号, 属性名, クラスインスタンス)
    # またはリストにこれらが複数入っている

    if isinstance(var_ref, list):
        # 複数の値の場合は、リストに入っている
        for value in var_ref:
            if len(value) == 3:
                cur_value = var_ref[2].__dict__[var_ref[1]]
                if cur_value == update_value:
                    continue

                setattr(value[2], value[1], update_value)
            else:
                cur_value = self._frame.f_globals[value[1]]
                if cur_value == update_value:
                    continue 

                self._frame.f_globals[value[1]] = update_value   
    else:     
        if len(var_ref) == 3:
            cur_value = var_ref[2].__dict__[var_ref[1]]
            if cur_value == update_value:
                return
            
            setattr(var_ref[2], var_ref[1], update_value)
        else:  
            cur_value = self._frame.f_globals[var_ref[1]]
            if cur_value == update_value:
                return
            
            self._frame.f_globals[var_ref[1]] = update_value

def _check_exist_label(self, label: str) -> None:
    try:
        self._new_value[label]
    except KeyError:
        raise KeyError(f"`{label}` has not been set.")

def _check_label_flag(self, label: str, cond: str | None) -> None:
    name = label.lstrip(SYMBOL)
    self._check_exist_label(name)

    if self._disable_label[name] or self._trigger_flag[name]:
        return
    
    if cond is not None:
        self._get_target_frame("set_trigger")

        if not self._ensure_safe_cond(cond):
            return
        
        self._trigger_flag[name] = True
    else:
        self._trigger_flag[name] = True
    
    self._label_has_var(name, "set_trigger", False)

    if self.debug:
        self._get_target_frame("set_trigger")
        self._print_flag_debug(name, "active", reset=False)

def _label_has_var(
    self, label: str, called_func: str, to_org: bool,
) -> None:
    if self._var_list[label] is None:
        return
    
    if to_org:
        update_value = self._org_value[label]
    else:
        update_value = self._new_value[label]

    self._get_target_frame(called_func)

    # 特定ラベルの全ての登録されてる変数を、
    # 元の値または、設定された値に更新する
    for i in range(len(self._var_list[label])):
        arg = self._var_list[label][i]

        if arg is None:
            continue
        elif isinstance(arg, list):
            for i_2, v in enumerate(arg):
                if not isinstance(update_value[i], (list, tuple)):
                    self._update_var_value(v, update_value[i])
                    continue            

                self._update_var_value(v, update_value[i][i_2])
        else:
            self._update_var_value(arg, update_value[i])  

def _is_new_var(self, label: str, index: int, value: Any) -> bool:
    if self._trigger_flag[label]:
        if isinstance(value, (list, tuple)):
            if self._new_value[label][index] in value:
                return False
        else:  
            self._new_value[label][index] == value
            return False
        
        return True  
        
    if isinstance(value, list):
        if self._org_value[label][index] == value:
            return False
    elif isinstance(value, tuple):
        if tuple(self._org_value[label][index]) == value:
            return False
    elif self._org_value[label][index] == value:
            return False
    
    return True

def _find_match_var(self, label: str, index: int) -> None:
    # `revert()`で変数の変更前の値を探す

    # `var_ref` は リスト
    var_ref = self._var_list[label][index]
    stop_flag = False

    # `value` はリスト
    for key, value in self._var_list.items(): 
        # `list_val` はリスト、タプル、Noneのいずれか
        for i, list_val in enumerate(value):
            if stop_flag:
                break

            if key == label:
                stop_flag = True
            elif list_val is None:
                continue
            elif isinstance(list_val, tuple) and isinstance(var_ref, tuple):
                if self._is_ref_match(list_val, var_ref):
                    self._org_value[label][index] = self._org_value[key][i]                 
            elif isinstance(list_val, tuple) and isinstance(var_ref, list):
                for i_2, ref_v in enumerate(var_ref):
                    if self._is_ref_match(list_val, ref_v):
                        self._org_value[label][index][i_2] = (
                            self._org_value[key][i]
                        )
            elif isinstance(list_val, list) and isinstance(var_ref, tuple):
                for i_2, l_v in enumerate(list_val):
                    if self._is_ref_match(l_v, var_ref):
                        self._org_value[label][index] = (
                            self._org_value[key][i][i_2]
                        )
            else:
                for ref_i, ref_val in enumerate(var_ref):
                    for list_i, v in enumerate(list_val):
                        if self._is_ref_match(v, ref_val):                           
                            self._org_value[label][index][ref_i] = (
                                self._org_value[key][i][list_i]
                            )

def _is_ref_match(
        self,
        list_val: tuple[str, ...], target_val: tuple[str, ...],
) -> bool:
    if len(list_val) == 2 and len(target_val) == 2:
        return list_val[1] == target_val[1]

    elif len(list_val) == 3 and len(target_val) == 3:
        return list_val[1:] == target_val[1:]

def _get_target_frame(self, target_name: str) -> None:
   if self._frame is not None:
      return
   
   frame = inspect.currentframe()

   while frame:
      if frame.f_code.co_name == target_name:
         self._frame = frame.f_back
         return
      frame = frame.f_back

def _clear_frame(self) -> None:
   # メモリリークを防ぐために、処理後に`None`に設定する
   self._frame = None
   self._lineno = None

