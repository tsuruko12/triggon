import ast
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import FrameType
from typing import Any

from ..core.value_resolver import resolve_ref_info
from ..errors.public import InvalidArgumentError, UpdateError
from .keys import ATTR, GLOB_VAR, LOC_VAR


def collect_rollback_refs(
    frame: FrameType,
    target_names: Sequence[str] | None,
) -> Mapping[str, Any]:
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno
    node = _find_with_node(filename, lineno)

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


def revert_targets(frame: FrameType, name_to_refs: Mapping[str, Any]) -> None:
    for name, ref in name_to_refs.items():
        if ref[0] == ATTR:
            kind, value, attr_name, parent_obj = ref
            try:
                setattr(parent_obj, attr_name, value)
            except (AttributeError, TypeError, ValueError) as e:
                raise UpdateError(name, e) from None
        else:
            kind, value = ref
            if kind == GLOB_VAR:
                frame.f_globals[name] = value
            elif kind == LOC_VAR:
                frame.f_locals[name] = value
            else:
                raise AssertionError(f"unreachable kind key: {kind!r}")


def _find_with_node(filename: str, lineno: int) -> ast.With:
    source = Path(filename).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=filename)

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
