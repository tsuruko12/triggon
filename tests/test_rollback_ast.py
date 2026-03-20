import ast
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4

ROOT = str(Path(__file__).resolve().parents[1] / "src")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from triggon import RollbackSourceError
from triggon._internal.rollback_ast import _find_with_node


def test_find_with_node_falls_back_to_module_file():
    source = "def run():\n    with helper():\n        value = 1\n"
    source_path = Path(__file__).with_name(f"_rollback_case_{uuid4().hex}.py")

    try:
        source_path.write_text(source, encoding="utf-8")

        frame = SimpleNamespace(
            f_code=SimpleNamespace(co_filename=str(source_path.with_name("stale_path.py"))),
            f_lineno=2,
            f_globals={"__file__": str(source_path)},
        )

        node = _find_with_node(frame)

        assert isinstance(node, ast.With)
        assert node.lineno == 2
    finally:
        source_path.unlink(missing_ok=True)


def test_find_with_node_raises_on_missing_source():
    frame = SimpleNamespace(
        f_code=SimpleNamespace(co_filename="<stdin>"),
        f_lineno=1,
        f_globals={},
    )

    with pytest.raises(RollbackSourceError, match=r"Triggon\.rollback\(\) could not find"):
        _find_with_node(frame)
