import ast
import linecache
from itertools import count
from typing import Any

from ._err_handler import (
   _count_symbol, 
   _ensure_allowed_cond,
   _ensure_index_type,
)
from ._exceptions import (
   InvalidArgumentError, 
   InvalidClassVarError,
   SYMBOL,
)
from ._sentinel import _NO_VALUE


LABEL_ERROR = "ラベルは文字列で渡してください。"
NEST_ERROR = "リストやタプルに変数を入れる際、ネスト構造（例：[x, [y]]）は避けてください。"
VALUE_TYPE_ERROR = "'value'には変数を入れてください。"
VAR_ERROR = "ローカル変数は対応していません。"
INVALID_LABEL_INDEX_TYPE = (
    "ラベルや 'index' キーワードに使用できるのは、"
    "リテラル、変数、または単純な属性アクセスのみです。"
)


# 同じ関数が同じ行で複数回呼び出された場合 (例：比較式内での複数呼び出し)、
# それらすべての呼び出しに含まれる変数は、1回の処理で登録されます。

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
        # インデントエラーや複数行に関数が渡ってる場合のエラーは無視する
        continue
      else:
        # 呼び出されたの関数を見つけるためにASTノードを巡回

        has_looped = False
        
        for node in ast.walk(line_range):
          if not isinstance(node, ast.Call):
            continue    
          if (
             not isinstance(node.func, ast.Attribute) 
             or node.func.attr != "switch_var"
            ): 
            continue

          first_arg = node.args[0]

          # 'index'引数が設定されてるか確認
          if node.keywords:
             for kw in node.keywords:
               index_node = kw.value
               index = self._analyze_index(index_node)
          else:
             index = None
          _ensure_index_type(index, allow_tuple=True)

          # 引数の型によって処理が分岐

          node_types = (ast.List, ast.Tuple, ast.Name, ast.Attribute)

          if isinstance(first_arg, ast.Dict):
            self._arg_is_dict(first_arg, index)
            has_looped = True
          else:
             try:
               second_arg = node.args[1]
             except IndexError:
                raise InvalidArgumentError(
                   "Provide variables as the second argument."
                )
                    
             if isinstance(second_arg, node_types):
               label = self._try_search_value(first_arg)

               if index is None:
                  index = (_count_symbol(label),)

               name = label.lstrip(SYMBOL) 

               self._ensure_label_exists(name)
               self._compare_value_counts(name, index)

               if isinstance(second_arg, (ast.List, ast.Tuple)):
                  self._arg_is_seq(second_arg, name, index)
               elif isinstance(second_arg, ast.Name):
                  self._arg_is_name(second_arg.id, name, index)
               elif isinstance(second_arg, ast.Attribute):
                  self._arg_is_attr(second_arg, name, index)
               else:
                  raise InvalidArgumentError(VALUE_TYPE_ERROR)
               
               has_looped = True

        # 目的の関数が１つ以上見つかった場合
        if has_looped:
           return

        raise RuntimeError(
           "switch_var() の呼び出しを検出できませんでした。"
           "これは、ソースコードが取得できない環境や、"
           "動的に実行される環境で発生する可能性があります。"
        )   
  
def _arg_is_dict(
      self, target: ast.Dict, index: tuple[int, ...] | None,
) -> bool:
    arg_list = self._deduplicate_labels(target)

    if index is not None:
       i = index
  
    for key, val in arg_list.items():
      label = key.lstrip(SYMBOL)

      if index is None:
         i = (_count_symbol(key),)

      _check_var_arg(val)
      self._ensure_label_exists(label)
      self._compare_value_counts(label, i)

      # 引数の型によって処理が分岐

      if isinstance(val, (ast.List, ast.Tuple)):
        _ = self._arg_is_seq(val, label, i)
      elif isinstance(val, ast.Dict):
         raise InvalidArgumentError(VALUE_TYPE_ERROR)
      else:
        _check_var_arg(val)

        if isinstance(val, ast.Name):
          _ = self._arg_is_name(val.id, label, i)
        elif isinstance(val, ast.Attribute):
          _ = self._arg_is_attr(val, label, i)
        else:
           raise InvalidArgumentError(VALUE_TYPE_ERROR)

    return True

def _arg_is_seq(
      self, target: ast.List | ast.Tuple, label: str, index: tuple[int, ...], 
) -> None:
    for i in index:    
      target_index = self._var_refs[label][i] 
      if target_index is None:
         self._var_refs[label][i] = []
      elif isinstance(target_index, tuple):
         # 値を追加するためにリストに変換
         self._var_refs[label][i] = [target_index]

    for val in target.elts:
      _check_var_arg(val)

      if isinstance(val, ast.Name):
         _ = self._arg_is_name(val.id, label, index)
      elif isinstance(val, ast.Attribute):
         _ = self._arg_is_attr(val, label, index)  
      elif isinstance(val, (ast.List, ast.Tuple, ast.Dict)):
         raise InvalidArgumentError(NEST_ERROR)
      else:
         raise InvalidArgumentError(VALUE_TYPE_ERROR)

def _arg_is_name(
      self, target: str, label: str, index: tuple[int, ...],
) -> None: 
   try:
      org_value = self._frame.f_globals[target]
   except KeyError:
      raise InvalidArgumentError(VAR_ERROR)

   for i in index:
      target_index = self._var_refs[label][i]

      # (ファイル名, 行番号, 変数名)
      var_refs = (self._file_name, self._lineno, target)

      result = self._find_match_var(label, var_refs)
      if result is _NO_VALUE:
         self._store_org_value(label, i, org_value)
      else:
         self._store_org_value(label, i, result)

      if target_index is not None:
         if not self._is_new_var(label, i, var_refs):
            # すでに登録済みの変数
            return
         
         if isinstance(target_index, tuple):
            self._var_refs[label][i] = [target_index]
         self._var_refs[label][i].append(var_refs)
      else:
         self._var_refs[label][i] = var_refs

def _arg_is_attr(
      self, target: ast.Attribute, label: str, index: tuple[int, ...],
) -> None:
    var_name = self._try_search_var(target, err_check=True)
    
    instance = self._frame.f_locals.get(var_name)
    if instance is None or isinstance(instance, type):
       raise InvalidClassVarError()
    
    for i in index:
      target_index = self._var_refs[label][i]

      # (ファイル名, 行番号, 属性名, クラスインスタンス)
      var_refs = (self._file_name, self._lineno, target.attr, instance)
      org_value = instance.__dict__[target.attr] 

      result = self._find_match_var(label, var_refs)
      if result is _NO_VALUE:
         self._store_org_value(label, i, org_value)
      else:
         self._store_org_value(label, i, result)

      if target_index is not None:
         if not self._is_new_var(label, index, var_refs):
            # すでに登録済みの変数
            return
         
         if isinstance(target_index, tuple):
            self._var_refs[label][i] = [target_index]
         self._var_refs[label][i].append(var_refs)
      else:
         self._var_refs[label][i] = var_refs 
         
def _get_cond_result(self, expr: Any) -> bool:
   if not isinstance(expr, str):
      raise TypeError("'cond'は文字列で渡してください.")

   try:
      tree = ast.parse(expr, mode="eval")
   except SyntaxError:
      raise InvalidArgumentError(
         "比較文のみ許可されています。"
         "if文、代入文、ループなどのステートメントは許可されていません。"
      )
   
   scope = {}

   nodes = []
   for node in ast.walk(tree):
      if isinstance(node, ast.Call):
         raise InvalidArgumentError(
            "'cond' 内での関数呼び出しは許可されていません。"
         )
       
      nodes.append(node)
      if isinstance(node, ast.Name) or isinstance(node, ast.Attribute):
         (var_name, var_value) = self._try_search_var(node)
         scope[var_name] = var_value

   # 許可: 比較式、または単体bool値
   _ensure_allowed_cond(scope, nodes)
   return eval(expr, scope)       

def _deduplicate_labels(self, target: ast.Dict) -> dict[str, ast.AST]:
    # 重複したラベルを排除する
    sorted_list = {}
    for key, val in zip(target.keys, target.values):
      label = self._try_search_value(key) 
      sorted_list[label] = val     
    return sorted_list

def _analyze_index(self, index: ast.AST) -> tuple[int, ...]:
   if isinstance(index, ast.Tuple):
      indexes = []
      for v in index.elts:
         value = self._try_search_value(v)
         indexes.append(value)
      return tuple(indexes)
   if isinstance(index, ast.Call):
      if index.func.id != "range":
         raise InvalidArgumentError(INVALID_LABEL_INDEX_TYPE)
      
      indexes = []
      for arg in index.args:
         value = self._try_search_value(arg)
         indexes.append(value)

      if len(indexes) == 1:
         to_range = range(indexes[0])
      elif len(indexes) == 2:
         to_range = range(indexes[0], indexes[1])
      else:
         to_range = range(indexes[0], indexes[1], indexes[2])      
      return tuple(to_range)
   if isinstance(index, ast.Constant):
      return (index.value,)

   raise InvalidArgumentError(INVALID_LABEL_INDEX_TYPE)

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
      raise InvalidArgumentError(INVALID_LABEL_INDEX_TYPE)
   
   return value


def _check_var_arg(target: ast.AST) -> None:
    if isinstance(target, ast.Constant):
      raise InvalidArgumentError(VALUE_TYPE_ERROR)
    
      