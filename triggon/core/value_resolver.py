import ast
import inspect
from types import FrameType
from typing import Any

from ..errors import InvalidArgumentError
from .._internal import _NO_VALUE


type AttrResult = tuple[Any, str, Any]  # (value, attr name, parent_obj)


ALLOWED_FUNCS = {
    "len": len,
    "abs": abs,
    "max": max,
    "min": min,
    "sum": sum,
    "round": round,
    "any": any,
    "all": all,
    "sorted": sorted,
}

ALLOWED_METHODS = (
    "startswith",
    "endswith",
    "isascii",
    "isalpha",
    "isalnum",
    "isdigit",
    "isdecimal",
    "isnumeric",
    "islower",
    "isupper",
    "istitle",
    "isspace",
    "isidentifier",
    "isprintable",
    "find",
    "count",
)

ALLOWED_EXPRS = (
    ast.Compare,
    ast.Name,
    ast.Attribute,
    ast.Constant,
    ast.BoolOp,
    ast.UnaryOp,
    ast.Call,
)

DISALLOWED_NODES = (
    ast.Lambda,
    ast.IfExp,
    ast.NamedExpr,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
    ast.Await,
    ast.Yield,
    ast.YieldFrom,
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
)


def evaluate_cond(frame: FrameType, expr: str) -> bool:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise InvalidArgumentError("cond: only expressions are allowed") from None

    expr_err = "cond: only comparison or boolean expressions are supported"

    body_nodes = tree.body
    if not isinstance(body_nodes, ALLOWED_EXPRS):
        raise InvalidArgumentError(expr_err)

    var_scope = {}

    for node in ast.walk(body_nodes):
        if isinstance(node, DISALLOWED_NODES):
            raise InvalidArgumentError(expr_err)

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
            raise InvalidArgumentError(f"cond: function {func!r} is not allowed")
    elif isinstance(func, ast.Attribute):
        func = func.attr
        if func not in ALLOWED_METHODS:
            raise InvalidArgumentError(f"cond: method {func!r} is not allowed")
    else:
        raise InvalidArgumentError("cond: dynamic calls are not allowed")


def resolve_ref_info(target_name: str, frame: FrameType) -> Any | AttrResult:
    if "." in target_name:
        has_attr_chain = True

        split_names = target_name.split(".")
        full_name = target_name
        target_name = split_names[0]
    else:
        has_attr_chain = False

    value = frame.f_locals.get(target_name, _NO_VALUE)
    if not has_attr_chain and value is not _NO_VALUE:
        raise InvalidArgumentError(f"cannot assign to local variable {target_name!r}")
    if value is _NO_VALUE:
        value = frame.f_globals.get(target_name, _NO_VALUE)
        if value is _NO_VALUE:
            raise NameError(f"{target_name!r} is not defined")

    if has_attr_chain:
        return _walk_attr_chain(full_name, split_names, value)
    return value


def _walk_attr_chain(
    full_name: str,
    split_names: list[str],
    parent_obj: Any,
) -> AttrResult:
    n = len(split_names)
    value = _NO_VALUE

    for i, name in enumerate(split_names[1:]):
        value = getattr(parent_obj, name)
        if i != n - 2:
            parent_obj = value

    if inspect.isclass(value):
        raise InvalidArgumentError(f"name {full_name!r} must end with an attribute, not a class")

    return value, split_names[-1], parent_obj
