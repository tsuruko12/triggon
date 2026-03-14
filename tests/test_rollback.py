from pathlib import Path
import sys

import pytest

ROOT = str(Path(__file__).resolve().parents[1] / "src")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from triggon import InvalidArgumentError, RollbackNotSupportedError, Triggon, UpdateError


def _run_explicit_restore_on_err():
    x = 1

    class Holder:
        value = 2

    holder = Holder()

    def run():
        nonlocal x

        with pytest.raises(RuntimeError, match="boom"):
            with Triggon.rollback(("x", "holder.value")):
                x = 10
                holder.value = 20
                raise RuntimeError("boom")

        return x, holder.value

    return run()


def _run_auto_collect_assignments():
    x = 1
    total = 10

    class Holder:
        value = 2

    holder = Holder()

    def run():
        nonlocal x, total

        with Triggon.rollback():
            x = 5
            total += 7
            holder.value = 20

            inside = (x, total, holder.value)

        outside = (x, total, holder.value)
        return inside, outside

    return run()


def _run_auto_collect_with_new_local():
    x = 1

    def run():
        nonlocal x

        with Triggon.rollback():
            x = 5
            created = 7

            inside = (x, created)

        outside = (x, created)
        return inside, outside

    return run()


def _run_nested_rollback_state():
    x = 1

    def run():
        nonlocal x

        with Triggon.rollback(("x",)):
            x = 2

            with Triggon.rollback(("x",)):
                x = 3
                inner = x

            after_inner = x

        after_outer = x
        return inner, after_inner, after_outer

    return run()


def test_rejects_invalid_targets_type():
    with pytest.raises(TypeError):
        with Triggon.rollback(123):
            pass


def test_rejects_empty_targets():
    with pytest.raises(InvalidArgumentError):
        with Triggon.rollback(()):
            pass


def test_raises_on_unsupported_python(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 12, 9))

    with pytest.raises(RollbackNotSupportedError):
        with Triggon.rollback():
            pass


def test_restores_explicit_loc_target_after_exc():
    x, _ = _run_explicit_restore_on_err()

    assert x == 1


def test_restores_explicit_attr_target_after_exc():
    x, holder_value = _run_explicit_restore_on_err()

    assert holder_value == 2


def test_accepts_single_str_target():
    x = 1

    def run():
        nonlocal x

        with Triggon.rollback("x"):
            x = 5
            assert x == 5

        assert x == 1

    run()


def test_auto_collect_restores_loc_assignments():
    inside, outside = _run_auto_collect_assignments()

    assert inside[0] == 5
    assert outside[0] == 1


def test_auto_collect_restores_augassigns():
    inside, outside = _run_auto_collect_assignments()

    assert inside[1] == 17
    assert outside[1] == 10


def test_auto_collect_restores_attr_assignments():
    inside, outside = _run_auto_collect_assignments()

    assert inside[2] == 20
    assert outside[2] == 2


def test_auto_collect_restores_annotated_assignments():
    def run():
        x = 1

        with Triggon.rollback():
            x: int = 5
            assert x == 5

        assert x == 1

    run()


def test_auto_collect_restores_existing_locals():
    inside, outside = _run_auto_collect_with_new_local()

    assert inside[0] == 5
    assert outside[0] == 1


def test_auto_collect_keeps_new_locals():
    inside, outside = _run_auto_collect_with_new_local()

    assert inside[1] == 7
    assert outside[1] == 7


def test_ignores_unresolvable_targets():
    x = 1

    def run():
        nonlocal x

        with Triggon.rollback(("x", "missing_name", "missing_root.value")):
            x = 5
            assert x == 5

        assert x == 1

    run()


def test_nested_restores_inner_scope_state():
    inner, after_inner, _ = _run_nested_rollback_state()

    assert inner == 3
    assert after_inner == 2


def test_nested_restores_outer_scope_state():
    _, _, after_outer = _run_nested_rollback_state()

    assert after_outer == 1


def test_raises_update_err_when_attr_restore_fails():
    class WriteOnce:
        def __init__(self):
            self._value = 1

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, new_value):
            if new_value == 1 and self._value != 1:
                raise ValueError("cannot restore original value")
            self._value = new_value

    box = WriteOnce()

    with pytest.raises(UpdateError, match="failed to update 'box.value'"):
        with Triggon.rollback(("box.value",)):
            box.value = 5
