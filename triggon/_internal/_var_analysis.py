import ast
import linecache
from itertools import count

from ._exceptions import (
   InvalidArgumentError,
   SYMBOL, 
)


LABEL_ERROR = "ラベルは文字列で渡してください。"
NEST_ERROR = "リストやタプルに変数を入れる際、ネスト構造（例：[x, [y]]）は避けてください。"
VALUE_TYPE_ERROR = "`value`には変数を入れてください。"
VAR_ERROR = "ローカル変数は対応していません。"


def _trace_func_call(self) -> None:
    lines = ""
    
    for i in count(self._lineno):
      line = linecache.getline(self._file_name, i)

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
             or node.func.attr not in ["switch_var", "alter_var"]
            ): 
            continue

          first_arg = node.args[0]

          # 引数の型によって処理が分岐

          if isinstance(first_arg, ast.Dict):
            result = self._arg_is_dict(first_arg)
          else:
             try:
               second_arg = node.args[1]
             except IndexError:
                raise InvalidArgumentError(
                   "引数に変数を設定してください。"
                )
                 
             _identify_arg(second_arg)

             label = self._try_search_value(first_arg)
                 
             # `index`キーワードが設定されてるかの確認
             if 0 < len(node.keywords):
                index = None

                for kw in node.keywords:
                   if kw.arg != "index":
                      continue
                   
                   index_node = kw.value
                   index = self._try_search_value(index_node)               

                if index is None:
                   index = self._count_symbol(label)
             else:
                index = self._count_symbol(label)

             name = label.lstrip(SYMBOL)  
          
             self._check_exist_label(name)
             self._compare_value_counts(name, index)

             if isinstance(second_arg, (ast.List, ast.Tuple)):
                result = self._arg_is_seq(second_arg, name, index)
             elif isinstance(second_arg, ast.Name):
                result = self._arg_is_name(second_arg.id, name, index)
             elif isinstance(second_arg, ast.Attribute):
                result = self._arg_is_attr(second_arg, name, index)
             else:
                raise InvalidArgumentError(VALUE_TYPE_ERROR)

        # 目的の関数が１つ以上見つかった場合
        if result:
           return

        raise RuntimeError(
           "'alter_var' または 'switch_var' の呼び出しを検出できませんでした。"
           "これは、ソースコードが取得できない環境や、"
           "動的に実行される環境で発生する可能性があります。"
        )   
  
def _arg_is_dict(self, target: ast.Dict) -> bool:
    arg_list = self._deduplicate_labels(target)
  
    for key, val in arg_list.items():
      label = key.lstrip(SYMBOL)

      if self._id_list.get(label) is None:
        return 1
      index = self._count_symbol(key)

      # 引数の型によって処理が分岐

      if isinstance(val, (ast.List, ast.Tuple)):
        _ = self._arg_is_seq(val, label, index)
      elif isinstance(val, ast.Dict):
         raise InvalidArgumentError(VALUE_TYPE_ERROR)
      else:
        _identify_arg(val)

        if isinstance(val, ast.Name):
          _ = self._arg_is_name(val.id, label, index)
        elif isinstance(val, ast.Attribute):
          _ = self._arg_is_attr(val, label, index)
        else:
           raise InvalidArgumentError(VALUE_TYPE_ERROR)

    return True

def _arg_is_seq(
      self, target: ast.List | ast.Tuple, label: str, index: int,
) -> bool:
    target_index = self._var_list[label][index] 

    if target_index is None:
      self._var_list[label][index] = []
    elif isinstance(target_index, tuple):
       # 値を追加するためリストに変換
       self._var_list[label][index] = [target_index]

    for val in target.elts:
      _identify_arg(val)

      if isinstance(val, ast.Name):
        _ = self._arg_is_name(val.id, label, index)
      elif isinstance(val, ast.Attribute):
        _ = self._arg_is_attr(val, label, index)  
      elif isinstance(val, (ast.List, ast.Tuple, ast.Dict)):
         raise InvalidArgumentError(NEST_ERROR)
      else:
        raise InvalidArgumentError(VALUE_TYPE_ERROR)

    return True

def _arg_is_name(self, target: str, label: str, index: int,) -> bool:    
   try:
      org_value = self._frame.f_globals[target]
   except KeyError:
      raise InvalidArgumentError(VAR_ERROR)

   target_index = self._var_list[label][index]

   # (ファイル名, 行番号, 変数名)
   var_refs = (self._file_name, self._lineno, target)

   if isinstance(target_index, list):
      if not self._is_new_var(label, index, var_refs):
         # すでに登録済みの変数
         return True
      
      self._var_list[label][index].append(var_refs)
   elif target_index is not None:
      if isinstance(target_index, tuple):
         self._var_list[label][index] = [target_index]

      self._var_list[label][index].append(var_refs)
   else:
      self._var_list[label][index] = var_refs

   self._store_org_value(label, index, org_value)
   self._find_match_var(label, index)

   return True

def _arg_is_attr(
      self, target: ast.Attribute, label: str, index: int,
) -> bool:
    var_name = self._try_search_var(target, err_check=True)
    instance = self._frame.f_locals[var_name]
    
    target_index = self._var_list[label][index]

    # (ファイル名, 行番号, 属性名, クラスインスタンス)
    var_refs = (self._file_name, self._lineno, target.attr, instance)

    if target_index is not None:
      if not self._is_new_var(label, index, var_refs):
         # すでに登録済みの変数
         return True
      
      if isinstance(target_index, tuple):
         self._var_list[label][index] = [target_index]

      self._var_list[label][index].append(var_refs)
    else:
       self._var_list[label][index] = var_refs

    org_value = instance.__dict__[target.attr]
    self._store_org_value(label, index, org_value)
    self._find_match_var(label, index)

    return True
         
def _ensure_safe_cond(self, expr: str) -> bool:
   if not isinstance(expr, str):
      raise InvalidArgumentError("`cond`は文字列で渡してください.")

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
      raise InvalidArgumentError("`cond`に渡された式の構文に誤りがあります。")
   
   scope = {}

   for node in ast.walk(tree):
      if not isinstance(node, allowed):
         raise InvalidArgumentError(
            "比較式のみ許可されています。 (例: `x > 10`, `a == b`)"
         )
      
      if isinstance(node, ast.Name) or isinstance(node, ast.Attribute):
         (var_name, var_value) = self._try_search_var(node)
         scope[var_name] = var_value
    
   return eval(expr, scope)      


def _deduplicate_labels(self, target: ast.Dict) -> dict[str, ast.AST]:
    # 重複したラベルを排除する
    sorted_list = {}

    for key, val in zip(target.keys, target.values):
      label = self._try_search_value(key) 
      sorted_list[label] = val
         
    return sorted_list

def _try_search_value(self, var: ast.AST) -> int | str:
   if isinstance(var, ast.Constant):
      value = var.value
   elif isinstance(var, ast.Name):
      (_, value) = self._try_search_var(var)
   elif isinstance(var, ast.Attribute):
      (var_name, full_name) = self._try_search_var(var, get_full_name=True)

      if full_name.count(".") > 1:
         # 属性が連なっている場合
         value = self._get_nested_value(full_name)
      else:
         instance = self._frame.f_locals[var_name]
         value = instance.__dict__[var.attr]
   else:
      raise InvalidArgumentError(
         "この関数では、ラベルや `index` キーワードに使用できるのは、"
         "リテラル、変数、または単純な属性アクセスのみです。"
      )
   
   return value


def _identify_arg(target: ast.AST) -> None:
    if isinstance(target, ast.Constant):
      raise InvalidArgumentError(VALUE_TYPE_ERROR)
    
      