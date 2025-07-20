import ast
import linecache
from itertools import count

from ._exceptions import (
   InvalidArgumentError,
   SYMBOL, 
)


LABEL_ERROR = "Label must be a string."
VALUE_TYPE_ERROR = "Provided value is not a variable."
VAR_ERROR = "Local arguments are not supported in this function."
NEST_ERROR = (
   "Variables should not be nested in lists or tuples (e.g. [x, [y]])."
)


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
        # Skip lines where the code is incomplete,
        # such as unfinished multi-line function calls,
        # or lines that would raise an `IndentationError`.
        continue
      else:
        # walk through AST nodes to find function calls
        
        for node in ast.walk(line_range):
          if not isinstance(node, ast.Call):
            continue    

          if (
             not isinstance(node.func, ast.Attribute) 
             or node.func.attr not in ["switch_var", "alter_var"]
          ): 
            continue

          first_arg = node.args[0]

          # handle each argument type differently

          if isinstance(first_arg, ast.Dict):
            result = self._arg_is_dict(first_arg)
          else:
             try:
               second_arg = node.args[1]
             except IndexError:
                raise InvalidArgumentError(
                   "Provide variables as the second argument."
                )
             
             _identify_arg(second_arg)

             label = self._try_search_value(first_arg)

             # check if 'index' keyword is set
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

        # It means that the target function was found at least once.
        if result:
           return

        raise RuntimeError(
           "Call to 'alter_var' or 'switch_var' could not be detected. "
           "This may occur in certain environments " 
           "where the source code is unavailable or dynamically executed."
        )   
  
def _arg_is_dict(self, target: ast.Dict) -> bool:
    arg_list = self._deduplicate_labels(target)
  
    for key, val in arg_list.items():
      label = key.lstrip(SYMBOL)
      index = self._count_symbol(key)

      self._check_exist_label(label)
      self._compare_value_counts(label, index)

      # Handle each argument type differently

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
       # convert to a list for adding values
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

   # (file neme, line number, var name)
   var_refs = (self._file_name, self._lineno, target)

   if target_index is not None:
      if not self._is_new_var(label, index, var_refs):
         # The variable has already been registered
         return True
      
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

    # (file name, line number, attr name, class instance)
    var_refs = (self._file_name, self._lineno, target.attr, instance)

    if target_index is not None:
      if not self._is_new_var(label, index, var_refs):
         # The variable has already been registered
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
      raise InvalidArgumentError("'cond' must be a string if provided.")
   
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
         "The expression passed to `cond` has a syntax error."
      )
   
   scope = {}

   for node in ast.walk(tree):
      if not isinstance(node, allowed):
         raise InvalidArgumentError(
            "Only comparison expressions "
            "(e.g. `x > 10`, `a == b`) are allowed."
         )
      
      if isinstance(node, ast.Name) or isinstance(node, ast.Attribute):
         (var_name, var_value) = self._try_search_var(node)
         scope[var_name] = var_value
    
   return eval(expr, scope)      
   
def _deduplicate_labels(self, target: ast.Dict) -> dict[str, ast.AST]:
    # Remove duplicate labels by converting to a set
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
      (var_name, _) = self._try_search_var(var)

      if var_name.count(".") > 1:
         # When it's an attribute chain
         value = self._get_nested_value(value)
      else:
         instance = self._frame.f_locals[var_name]
         value = instance.__dict__[var.attr]
   elif isinstance(var, ast.Call):
      func_name = self._try_search_var(var.func, get_func=True)

      compiled = compile(func_name, "<string>", "eval")
      value = eval(compiled, self._frame.f_globals, self._frame.f_locals)
   else:
      raise InvalidArgumentError(
         "Only simple values or functions are allowed as labels or index."
      )
   
   return value


def _identify_arg(target: ast.AST) -> None:
    if isinstance(target, ast.Constant):
      raise InvalidArgumentError(VALUE_TYPE_ERROR)
    
      
