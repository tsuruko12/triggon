import ast
import linecache
from collections.abc import Mapping, Sequence
from types import FrameType

from ..core.value_resolver import AttrResult, VarResult, resolve_ref_info
from ..errors.public import InvalidArgumentError, RollbackSourceError, UpdateError
from .keys import GLOB_VAR, LOC_VAR


def collect_rollback_refs(
    frame: FrameType,
    target_names: Sequence[str] | None,
) -> Mapping[str, VarResult | AttrResult]:
    node = _find_with_node(frame)

    if target_names is None:
        target_names = _collect_assigned_ref_names(node)

    name_to_refs = {}
    for name in target_names:
        try:
            value = resolve_ref_info(name, frame, allow_loc_var=True)
            name_to_refs[name] = value
        except (InvalidArgumentError, NameError):
            continue

    return name_to_refs


def revert_targets(frame: FrameType, name_to_refs: Mapping[str, VarResult | AttrResult]) -> None:
    for name, ref in name_to_refs.items():
        if isinstance(ref, AttrResult):
            try:
                setattr(ref.parent_obj, ref.attr_name, ref.value)
            except (AttributeError, TypeError, ValueError) as e:
                raise UpdateError(name, e) from None
        elif isinstance(ref, VarResult):
            if ref.kind == GLOB_VAR:
                frame.f_globals[name] = ref.value
            elif ref.kind == LOC_VAR:
                frame.f_locals[name] = ref.value
            else:
                raise AssertionError(f"unreachable ref type: {type(ref)!r}")


def _find_with_node(frame: FrameType) -> ast.With:
    lineno = frame.f_lineno
    source, source_name = _load_source(frame)
    tree = ast.parse(source, filename=source_name)

    with_node = None

    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            node_start = getattr(node, "lineno", None)
            node_end = getattr(node, "end_lineno", None)

            if node_start is None or node_end is None:
                continue
            if node_start <= lineno <= node_end:
                with_node = node

    if with_node is None:
        raise RuntimeError("failed to locate the target rollback block")
    return with_node


def _load_source(frame: FrameType) -> tuple[str, str]:
    filename = frame.f_code.co_filename
    lines = linecache.getlines(filename, frame.f_globals)
    if lines:
        return "".join(lines), filename

    module_file = frame.f_globals.get("__file__")
    if isinstance(module_file, str):
        lines = linecache.getlines(module_file, frame.f_globals)
        if lines:
            return "".join(lines), module_file

    raise RollbackSourceError(filename)


def _collect_assigned_ref_names(node: ast.With) -> list[str]:
    vars_and_attrs = []

    for child in ast.walk(node):
        if isinstance(child, ast.Assign):
            for target in child.targets:
                name = _get_target_name(target)
                if name is not None:
                    vars_and_attrs.append(name)
        elif isinstance(child, ast.AnnAssign):
            name = _get_target_name(child.target)
            if name is not None:
                vars_and_attrs.append(name)
        elif isinstance(child, ast.AugAssign):
            name = _get_target_name(child.target)
            if name is not None:
                vars_and_attrs.append(name)

    return vars_and_attrs


def _get_target_name(target: ast.expr) -> str | None:
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return ast.unparse(target)

    return None
