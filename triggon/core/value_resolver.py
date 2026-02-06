import ast
import inspect
from types import FrameType
from typing import Any

from ..errors import InvalidArgumentError
from .._internal import _NO_VALUE


ALLOWED_FUNCS = {
   "len": len, "abs": abs, 
   "max": max, "min": min, "sum": sum,
   "round": round,
   "any": any, "all": all, 
   "sorted": sorted, 
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
   ast.Call,
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

# ------------------------------------------------------------------------
# is_registered()
# ------------------------------------------------------------------------

# Will update later

def has_matching_var(self, target_name: str, cur_file: str) -> bool:
   try:
      target_ref = self._find_value_and_name(target_name)
   except InvalidArgumentError | NameError:
      return False
   else:
      if target_ref is None:
         return False
      
      for var_refs in self._var_refs.values():
         for ref in var_refs:
            if len(ref) == 3:
               ref = ref[:2]
            else:
               ref = (ref[0], ref[1], ref[3])

            if ref == target_ref:
               return True
      return False
   
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
      except AttributeError as e:
         raise AttributeError(e)
      else:
         if i != n -2:
            parent = value

   if inspect.isclass(value):
      raise InvalidArgumentError(
         f"var: name {full_name!r} must end "
         "with a variable or attribute, not a class"
      )
   return (value, split_names[-1], parent)

# ------------------------------------------------------------------------
# cond
# ------------------------------------------------------------------------

def evaluate_cond(frame: FrameType, expr: str) -> bool:
   try:
      tree = ast.parse(expr, mode="eval")
   except SyntaxError:
      raise InvalidArgumentError(
         "cond: only expressions are allowed"
      ) from None
   
   expr_err = "cond: only comparison or boolean expressions are supported"
   
   body_nodes = tree.body
   if not isinstance(body_nodes, ALLOWED_EXPRS):
      raise InvalidArgumentError(expr_err)

   var_scope = {}

   for node in ast.walk(body_nodes):
      if isinstance(node, DISALLOWED_NODES):
         raise  InvalidArgumentError(expr_err)

      if isinstance(node, ast.Name):
         value = _lookup_value_for_eval(frame, node.id)
         if value is _NO_VALUE:
            continue
         var_scope[node.id] = value
      elif isinstance(node, ast.Attribute):
         v = node.value
         while isinstance(v, ast.Attribute):
            v = v.value

         if isinstance(v, ast.Name):
            value = _lookup_value_for_eval(frame, v.id)
            if value is _NO_VALUE:
               continue
            var_scope[v.id] = value
         else:
            raise InvalidArgumentError(
               "cond: invalid attribute access "
               "(allowed: x.y.z; not allowed: foo().x, (a+b).x)"
            )
      elif isinstance(node, ast.Call):
         _ensure_allowed_call(node)

   builtins = {"__builtins__": {}} | ALLOWED_FUNCS
   try:
      result = eval(expr, builtins, var_scope)
   except AttributeError as e:
      raise AttributeError(f"cond: {e}")
   except TypeError as e:
      raise TypeError(f"cond: {e}")
   else:
      if not isinstance(result, bool):
         raise InvalidArgumentError("cond: expression must evaluate to bool")
      return result


def _lookup_value_for_eval(frame: FrameType, name: str) -> Any:
   if name in ALLOWED_FUNCS:
      return _NO_VALUE
   
   try:
      return frame.f_locals[name]
   except KeyError:
      try:
         return frame.f_globals[name]
      except KeyError:
         raise NameError(f"cond: {name!r} is not defined") from None
      

def _ensure_allowed_call(node: ast.Call) -> None:
   func = node.func
   if isinstance(func, ast.Name):
      func = func.id
      if func not in ALLOWED_FUNCS:
         raise InvalidArgumentError(
            f"cond: function {func!r} is not allowed"
         )
   elif isinstance(func, ast.Attribute):
      func = func.attr
      if func not in ALLOWED_METHODS:
         raise InvalidArgumentError(
            f"cond: method {func!r} is not allowed"
         )
   else:
      raise InvalidArgumentError(
         "cond: dynamic calls are not allowed"
      )

