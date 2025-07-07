import ast
import linecache
from itertools import count

from ._exceptions import (
    SYMBOL, 
    InvalidArgumentError, 
    _compare_value_counts,
    _count_symbol, 
)


LABEL_ERROR = "ラベルは文字列で渡してください。"
VALUE_TYPE_ERROR = "`value`には変数を入れてください。"
NEST_ERROR = "この関数では配列内でネストすることは出来ません。"
VAR_ERROR = "ローカル変数は対応していません。"


def _init_arg_list(
      self, change_list, arg_type: ast.AST, index: int=None,
) -> None:
    if index is None:
       has_index = False
    else:
       has_index = True

    # 変数を照合するためのIDを保存
    for key, val in change_list.items():   
        name = key.lstrip(SYMBOL)
        self._check_exist_label(name)

        if not has_index:
          index = _count_symbol(key)
        _compare_value_counts(self._new_value[name], index)

        if isinstance(val, (list, tuple)):
            self._id_list[name][index] = []

            for v in val:
               if isinstance(v, (list, tuple, dict)):
                  raise InvalidArgumentError(NEST_ERROR)                       
               self._id_list[name][index].append(id(v))     

            continue
        elif isinstance(val, dict):
           raise InvalidArgumentError(VALUE_TYPE_ERROR)

        self._id_list[name][index] = id(val)
 
    file_name = self._frame.f_code.co_filename 
    self._trace_func_call(file_name, arg_type)

def _trace_func_call(self, file_name: str, arg_type: ast.AST) -> None:
    lines = []
    
    for i in count(self._lineno):
      line = linecache.getline(file_name, i)
      if not line:
        break
      lines.append(line.lstrip())

      try:
        line_range = ast.parse("".join(lines))

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
             second_arg = node.args[1]
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

             name = label.lstrip(SYMBOL)       

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
                   index = _count_symbol(name)
             else:
                index = _count_symbol(name)
          
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

      # 関数が一行で終わっていない場合、このエラーは無視。
      # （その関数の終わりの行を探すため）
      except SyntaxError:
        continue

    raise RuntimeError(
       "ソースコード内の`alter_var' が見つかりませんでした。"
    )   
  
def _arg_is_dict(self, target: ast.Dict) -> int:
    arg_list = _deduplicate_labels(target)
  
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
    elif not isinstance(target_index, list):
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
      self._var_list[label][index].append((self._lineno, target))
    elif target_index is not None:
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
    if isinstance(target_index, list):
      self._var_list[label][index].append(
         (self._lineno, target.attr, instance)
      )
    elif target_index is not None:
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
         
   
def _deduplicate_labels(target: ast.Dict) -> dict[str, ast.AST]:
    # 重複したラベルを排除する
    sorted_list = {}

    for key, val in zip(target.keys, target.values):
      sorted_list[key.value] = val

    return sorted_list


def _identify_arg(target: ast.AST) -> None:
    if isinstance(target, ast.Constant):
      raise InvalidArgumentError(VALUE_TYPE_ERROR)
      
