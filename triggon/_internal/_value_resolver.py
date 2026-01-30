import ast
import inspect
from typing import Any

from ._exceptions import InvalidArgumentError


ALLOWED_FUNCS = {
   "len": len, "abs": abs, 
   "max": max, "min": min, "sum": sum,
   "round": round,
   "any": any, "all": all, 
   "sorted": sorted, 
   "isinstance": isinstance,
}

ALLOWED_METHODS = (
   "startswith", "endswith",
   "isascii", "isalpha", "isalnum",
   "isdigit", "isdecimal", "isnumeric",
   "islower", "isupper", "istitle",
   "isspace", "isidentifier", "isprintable",
   "find", "count",
)

ALLOWED_EXPRS = (
   ast.Compare, 
   ast.Name, ast.Attribute, 
   ast.Constant, 
   ast.BoolOp, ast.UnaryOp,
)

DISALLOWED_NODES = (
    ast.Lambda,
    ast.IfExp,
    ast.NamedExpr,
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
    ast.Await, ast.Yield, ast.YieldFrom,
    ast.Import, ast.ImportFrom,
    ast.Global, ast.Nonlocal,
)

    
def _evaluate_cond(self, expr: str) -> bool:
   try:
      tree = ast.parse(expr, mode="eval")
   except SyntaxError:
      raise InvalidArgumentError("only expressions are allowed in 'cond'")
   
   body_nodes = tree.body
   if not isinstance(body_nodes, ALLOWED_EXPRS):
      raise InvalidArgumentError(
         "only comparison or boolean expressions are supported in 'cond'"
      )

   var_scope = {}
   for node in ast.walk(body_nodes):
      if isinstance(node, DISALLOWED_NODES):
         raise  InvalidArgumentError(
            "only comparison or boolean expressions are supported in 'cond'"
         )

      if isinstance(node, ast.Name):
         value = self._lookup_value_for_eval(node.id)
         if value is None:
            continue
         var_scope[node.id] = value
      elif isinstance(node, ast.Attribute):
         v = node.value
         while isinstance(v, ast.Attribute):
            v = v.value

         value = self._lookup_value_for_eval(v.id)
         if value is None:
            continue
         var_scope[v.id] = value
      elif isinstance(node, ast.Call):
         _ensure_allowed_call(node)

   builtins = {"__builtins__": {}} | ALLOWED_FUNCS
   result = eval(expr, builtins, var_scope)
   if not isinstance(result, bool):
      raise InvalidArgumentError("expression in 'cond' must evaluate to bool")
   return result

def _lookup_value_for_eval(self, target_name: str) -> Any:
   try:
      return self._frame.f_locals[target_name]
   except KeyError:
      try:
         return self._frame.f_globals[target_name]
      except KeyError:
         return None
      
def _find_value_and_name(
      self, target_name: str,
) -> tuple[Any, str] | tuple[Any, str, Any] | None:
   if "." in target_name:
      has_attr_chain = True

      split_name = target_name.split(".")
      full_name = target_name
      target_name = split_name[0]
   else:
      has_attr_chain = False
         
   try:
      value = self._frame.f_locals[target_name]
   except KeyError:
      if not has_attr_chain:
         raise InvalidArgumentError(
            f"cannot assign to local variable {target_name!r}"
         )
      try:
         value = self._frame.f_globals[target_name]
      except KeyError:
         return None
   
   if has_attr_chain:
      return _walk_attr_chain(full_name, split_name, value)
   return (value, target_name)


def _walk_attr_chain(
      full_name: str, split_names: list[str], parent: Any,
) -> tuple[Any, str, Any]:
   n = len(split_names)
   value = None
   for i, name in enumerate(split_names[1:]):
      try:
         value = getattr(parent, name)
      except AttributeError:
         failed_at = ".".join(split_names[:i+2])
         _raise_name_err(full_name, failed_at)
      else:
         if i != n -2:
            parent = value

   if inspect.isclass(value):
      raise InvalidArgumentError(
         f"name {full_name!r} in 'var' must end "
         "with a variable or attribute, not a class"
      )
   return (value, split_names[-1], parent)


def _ensure_allowed_call(node: ast.Call) -> None:
   func = node.func
   if isinstance(func, ast.Name):
      func = func.id
      if func not in ALLOWED_FUNCS:
         raise InvalidArgumentError(
            f"function {func!r} is not allowed in 'cond'"
         )
   elif isinstance(func, ast.Attribute):
      func = func.attr
      if func not in ALLOWED_METHODS:
         raise InvalidArgumentError(
            f"method {func!r} is not allowed in 'cond'"
         )
   else:
      raise InvalidArgumentError(
         "dynamic calls are not allowed in 'cond'"
      )
   

def _raise_name_err(name: str, failed_at: str) -> None:
   raise NameError(f"name {name!r} is not defined (failed at {failed_at!r})")
   

# Only used for is_registered()
def _has_matching_var(
      self, target_name: str,
) -> bool:
   try:
      target_refs = self._find_value_and_name(target_name)
   except InvalidArgumentError | NameError:
      return False
   else:
      if target_refs is None:
         return False
      
      for ref in self._var_refs.values():
         for v in ref:
            if v[0] != self._file_name:
               continue
            if v[2:] == target_refs:
               return True
      return False

   