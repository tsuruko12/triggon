def _init_or_not(self, label: str, index: int) -> bool:
    self._get_target_frame(["switch_var", "alter_var"]) # ベータ後に変更予定   
    
    self._check_exist_label(label)  
    self._compare_value_counts(label, index)

    if (
        self._var_list[label][index] is None
        or self._is_new_var(label, index)
    ):  
        # 変数を保存するための初期設定
        self._trace_func_call()
        return True
    
    return False

def _is_new_var(
        self, label: str, index: int, target_ref: tuple[str, ...]=None,
) -> bool:
    # ファイル名と行番号が一致してた場合はすでに登録済みの変数

    var_ref = self._var_list[label][index]

    if isinstance(var_ref, tuple):
        if target_ref is not None:
            if target_ref[:3] == var_ref[:3]:
                return False
            else:
                return True
        elif var_ref[0] == self._file_name:
            return False
        
        return True
    
    for ref in var_ref:
        if target_ref is not None:
            if target_ref[:3] == var_ref[:3]:
                return False
        elif ref[0] == self._file_name and ref[1] == self._lineno:
            return False
        
    return True

def _find_match_var(self, label: str=None, index: int=None) -> None:
    # `revert()`で変数の変更前の値を探す

    # タプル、リストのいずれか
    var_ref = self._var_list[label][index]

    # 同じラベルまで処理を繰り返す
    stop_flag = False

    # `value` はリスト
    for key, value in self._var_list.items():         
        if stop_flag:
            return
        
        if key == label:
            stop_flag = True

        # `list_val` はリスト、タプル、Noneのいずれか
        for i, list_val in enumerate(value):
            if list_val is None:
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
        self, list_val: tuple[str, ...], target_val: tuple[str, ...],
) -> bool:
    if len(list_val) == 3 and len(target_val) == 3:
        return list_val[0] == target_val[0] and list_val[2] == target_val[2]
    elif len(list_val) == 4 and len(target_val) == 4:
        return list_val[2:] == target_val[2:]
    
