import ast
import copy
import linecache
from itertools import count

from ._err_handler import (
   _compare_value_counts, 
   _count_symbol,
)
from ._exceptions import SYMBOL, InvalidArgumentError
from ._switch_var import _is_mult_vars


LABEL_ERROR = "ラベルは文字列で渡してください。"
NEST_ERROR = "この関数では配列内でネストすることは出来ません。"
VALUE_TYPE_ERROR = "`value`には変数を入れてください。"
VAR_ERROR = "ローカル変数は対応していません。"


def _init_arg_list(
      self, change_list, arg_type: ast.AST, index: int=None,
) -> None:
    if index is None:
       has_index = False
    else:
       has_index = True
        
    # 最後にIDを入れた部分をリセットしてNoneの状態にするため(初期状態)
    copied_dict = copy.deepcopy(self._id_list)

    # 変数を照合するためのIDを保存
    for key, val in change_list.items():   
        name = key.lstrip(SYMBOL)
        self._check_exist_label(name)   

        if not has_index:
          index = _count_symbol(key)
        _compare_value_counts(self._new_value[name], index)

        if self._id_list[name][index] is None and _is_mult_vars(val):
            self._id_list[name][index] = []
            self._id_list[name][index].extend([id(v) for v in val])    

            continue
        elif isinstance(val, dict):
           raise InvalidArgumentError(VALUE_TYPE_ERROR)
        
        target_index = self._id_list[name][index]

        if target_index is None:
           self._id_list[name][index] = id(val)         
        else:
          if not isinstance(target_index, list):
             self._id_list[name][index] = [target_index]
             
          self._id_list[name][index].append(id(val))
 
    file_name = self._frame.f_code.co_filename 
    self._trace_func_call(file_name, arg_type)

    self._id_list = copied_dict

def _trace_func_call(self, file_name: str, arg_type: ast.AST) -> None:
    lines = ""
    
    for i in count(self._lineno):
      line = linecache.getline(file_name, i)
      if not line:
        break
      lines += line

      try:
        line_range = ast.parse(lines.lstrip())  
      except SyntaxError:
        # インデントエラーや複数行に関数が渡ってる場合のエラーは無視する。
        continue
      else:
        # 呼び出されたの関数を見つけるためにASTノードを巡回
        
        for node in ast.walk(line_range):
          if not isinstance(node, ast.Call):
            continue    

          if (
             not isinstance(node.func, ast.Attribute) 
             or node.func.attr != "alter_var"
            ): 
            continue

          first_arg = node.args[0]

          # 引数の型によって処理が分岐

          if arg_type == ast.Dict and isinstance(first_arg, ast.Dict):
            result = self._arg_is_dict(first_arg)
          else:
             try:
               second_arg = node.args[1]
             except IndexError:
                raise InvalidArgumentError(
                   "引数に変数を設定してください。"
                )
                 
             _identify_arg(second_arg)

             if isinstance(first_arg, ast.Name):
                try:
                  label = self._frame.f_locals[first_arg.id]
                except KeyError:
                   label = self._frame.f_globals[first_arg.id]
             elif isinstance(first_arg, ast.Attribute):
                instance = self._frame.f_locals[first_arg.value.id]
                field = instance.__dict__[first_arg.attr]

                label = field
             elif isinstance(first_arg, ast.Constant):
                label = first_arg.value
             else:
                linecache.clearcache()
                break     
                 
             # `index`キーワードが設定されてるかの確認
             if 0 < len(node.keywords) <= 3:
                index = None

                for kw in node.keywords:
                   if kw.arg != "index":
                      continue
                   
                   index_node = kw.value

                   if isinstance(index_node, ast.Constant):
                      index = index_node.value
                   else:
                      # 現在は`index`にはリテラル値のみ使えますが、
                      # 将来的に変数にも対応するかもしれません。
                      raise InvalidArgumentError(
                         "`index` キーワードにはリテラル値を入れてください。"    
                      )                    

                if index is None:
                   index = _count_symbol(label)
             else:
                index = _count_symbol(label)

             name = label.lstrip(SYMBOL)  
          
             if (
                arg_type == ast.List 
                and isinstance(second_arg, (ast.List, ast.Tuple))
             ):
                result = self._arg_is_seq(second_arg, name, index)
             elif arg_type == ast.Name and isinstance(second_arg, ast.Name):
                result = self._arg_is_name(second_arg.id, name, index)
             elif (
                arg_type == ast.Name 
                and isinstance(second_arg, ast.Attribute)
             ):
                result = self._arg_is_attr(second_arg, name, index)
             else:
                linecache.clearcache()
                break

          # resultが１の場合は目的の関数ではない
          if result == 1:
            linecache.clearcache()
            break     
          return

    raise RuntimeError(
       "ソースコード内の`alter_var' が見つかりませんでした。"
    )   
  
def _arg_is_dict(self, target: ast.Dict) -> int:
    arg_list = self._deduplicate_labels(target)
  
    for key, val in arg_list.items():
      label = key.lstrip(SYMBOL)

      if self._id_list.get(label) is None:
        return 1
      index = _count_symbol(key)

      # 引数の型によって処理が分岐

      if isinstance(val, (ast.List, ast.Tuple)):
        result = self._arg_is_seq(val, label, index)
        if result == 1:
          return 1
      elif isinstance(val, ast.Dict):
         raise InvalidArgumentError(VALUE_TYPE_ERROR)
      else:
        _identify_arg(val)

        if isinstance(val, ast.Name):
          result = self._arg_is_name(val.id, label, index)
        else:
          result = self._arg_is_attr(val, label, index)

        if result == 1:
          return 1

    return 0

def _arg_is_seq(
      self, target: ast.List | ast.Tuple, label: str, index: int,
) -> tuple[int, int]:
    target_index = self._var_list[label][index] 

    if target_index is None:
      self._var_list[label][index] = []
    elif isinstance(target_index, tuple):
       # 値を追加するためリストに変換
       self._var_list[label][index] = [target_index]

    for i, val in enumerate(target.elts):
      _identify_arg(val)

      if isinstance(val, ast.Name):
        _ = self._arg_is_name(val.id, label, index, i)
      elif isinstance(val, ast.Attribute):
        result = self._arg_is_attr(val, label, index, i)  
        if result == 1:
          return 1
      else:
        raise InvalidArgumentError(NEST_ERROR)

    return 0

def _arg_is_name(
      self, target: str, label: str, index: int, inner_index: int=None,
) -> int:
   self._check_exist_label(label)   
   _compare_value_counts(self._new_value[label], index)

   target_id = self._get_list_id(label, index, inner_index)
   if target_id is None:
      return 1
    
   try:
      self._frame.f_globals[target]
   except KeyError:
      raise InvalidArgumentError(VAR_ERROR)

   target_index = self._var_list[label][index]

   # (行番号, 変数名)
   if isinstance(target_index, list):
      if self._find_match_var(target_ref=(self._lineno, target), init=True):
         return 0
      
      self._var_list[label][index].append((self._lineno, target))
   elif target_index is not None:
      if isinstance(target_index, tuple):
         self._var_list[label][index] = [target_index]

      self._var_list[label][index].append((self._lineno, target))
   else:
      self._var_list[label][index] = (self._lineno, target)

   return 0

def _arg_is_attr(
      self, target: ast.Attribute, label: str, 
      index: int, inner_index: int=None,
) -> int:
    self._check_exist_label(label)      
    _compare_value_counts(self._new_value[label], index)

    target_id = self._get_list_id(label, index, inner_index)
    if target_id is None:
       return 1

    instance = self._frame.f_locals[target.value.id]
    field = instance.__dict__[target.attr]

    if id(field) != target_id:
      return 1
    
    target_index = self._var_list[label][index]

    # (行番号, 属性名, クラスインスタンス)
    if target_index is not None:
      if (
         self._find_match_var(
            target_ref=(self._lineno, target.attr, instance), init=True,
         )
      ):
         return 0
      
      if isinstance(target_index, tuple):
         self._var_list[label][index] = [target_index]

      self._var_list[label][index].append(
         (self._lineno, target.attr, instance)
      )
    else:
       self._var_list[label][index] = (self._lineno, target.attr, instance)

    return 0
      
def _get_list_id(
      self, label: str, index: int, inner_index: int=None,
) -> int | None:
    target_id = self._id_list[label][index]

    if isinstance(target_id, list):
       if inner_index is not None and len(target_id) > inner_index:
         return target_id[inner_index]
       return None
    elif inner_index is not None:
      return None
    else:
      return target_id
         
def _ensure_safe_cond(self, expr: str) -> None | bool:
   if not isinstance(expr, str):
      raise InvalidArgumentError("'expr' must be a string if provided.")

   allowed = (
        ast.Expression,
        ast.Compare, ast.Name, ast.Attribute, ast.Constant, 
        ast.Is, ast.IsNot, ast.In, ast.NotIn,
        ast.Load, ast.Eq, ast.NotEq, ast.Lt, 
        ast.Gt, ast.LtE, ast.GtE, ast.BoolOp, 
        ast.And, ast.Or, ast.UnaryOp, ast.Not,
   )

   try:
      tree = ast.parse(expr, mode="eval")
   except SyntaxError:
      raise InvalidArgumentError(
         "Invalid expression syntax. "
         "Please ensure the expression is valid."
      )
   
   scope = {}

   for node in ast.walk(tree):
      if not isinstance(node, allowed):
         raise InvalidArgumentError(
            "Only comparison expressions "
            "(e.g. `x > 10`, `a == b`) are allowed."
         )
      
      if isinstance(node, ast.Name):
         try:
            var_value = self._frame.f_locals[node.id]
         except KeyError:
            pass
         else:
            scope[node.id] = var_value

      if isinstance(node, ast.Attribute):
         instance = self._frame.f_locals[node.value.id]
         
         scope[node.value.id] = instance
    
   return eval(expr, scope)


def _deduplicate_labels(self, target: ast.Dict) -> dict[str, ast.AST]:
    # 重複したラベルを排除する
    sorted_list = {}

    for key, val in zip(target.keys, target.values):
      if isinstance(key, ast.Constant):
        sorted_list[key.value] = val
      else:
         label = self._try_search_label(key)

         if label is None:
            raise ValueError("ラベルが見つかりませんでした。")
            
         sorted_list[label] = val

    return sorted_list

def _try_search_label(self, var: ast.Name | ast.Attribute) -> None | str:
   if isinstance(var, ast.Attribute):
      instance = self._frame.f_locals[var.value.id]
      field = instance.__dict__[var.attr]
      return field
   
   try:
      label = self._frame.f_locals[var.id]
   except KeyError:
      label = self._frame.f_globals[var.id]
   except AttributeError:
      return

   return label


def _identify_arg(target: ast.AST) -> None:
    if isinstance(target, ast.Constant):
      raise InvalidArgumentError(VALUE_TYPE_ERROR)
      
