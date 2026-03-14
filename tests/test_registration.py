from pathlib import Path
import sys

import pytest

ROOT = str(Path(__file__).resolve().parents[1] / "src")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from triggon import InvalidArgumentError, Triggon
from triggon.errors.public import UnregisteredLabelError


reg_x = 0
reg_y = 0


class Main:
    a = 0
    b = "b"


GLOBAL_MAIN = Main


def _register_split_refs():
    tg = Triggon.from_labels({"A": 1, "B": 2})
    tg.register_refs({"A": {"reg_x": 0}, "B": {"reg_y": 0}})
    return tg


def _register_ref_scope_state():
    tg = Triggon.from_label("A", new_values=1)

    class LocalMain:
        a = 0

    def helper():
        m = LocalMain
        tg.register_ref("A", name="m.a")
        return tg.is_registered("m.a")

    def outer():
        m = LocalMain
        registered_in_helper = helper()
        registered_in_outer = tg.is_registered("m.a")
        return registered_in_helper, registered_in_outer

    return outer()


def _unregister_ref_scope_state():
    tg = Triggon.from_label("A", new_values=1)

    class LocalMain:
        a = 0

    def outer():
        m = LocalMain
        tg.register_ref("A", name="m.a")

        def inner():
            m = LocalMain
            tg.unregister_refs("m.a")
            return tg.is_registered("m.a")

        inner_registered = inner()
        outer_registered_before = tg.is_registered("m.a")
        tg.unregister_refs("m.a")
        outer_registered_after = tg.is_registered("m.a")
        return inner_registered, outer_registered_before, outer_registered_after

    return outer()


def test_register_ref_marks_global_name_as_registered():
    tg = Triggon.from_label("A", new_values=1)

    tg.register_ref("A", name="reg_x")

    assert tg.is_registered("reg_x") is True
    assert tg.is_registered("missing_name") is False


def test_register_refs_marks_multiple_names():
    tg = _register_split_refs()

    assert tg.is_registered("reg_x") is True
    assert tg.is_registered("reg_y") is True


def test_is_registered_checks_multiple_names():
    tg = _register_split_refs()

    assert tg.is_registered("reg_x", "reg_y") is True
    assert tg.is_registered(("reg_x", "missing_name")) is False
    assert tg.is_registered(["reg_x", "missing_name"], match_all=False) is True


def test_is_registered_filters_by_label():
    tg = _register_split_refs()

    assert tg.is_registered("reg_x", label="A") is True
    assert tg.is_registered("reg_x", label="B") is False
    assert tg.is_registered("reg_y", label="B") is True


def test_register_ref_raises_for_unregistered_label():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(UnregisteredLabelError):
        tg.register_ref("B", name="reg_x")


def test_register_ref_raises_for_missing_root_name():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(NameError):
        tg.register_ref("A", name="missing_root.value")


def test_register_ref_rejects_local_names():
    tg = Triggon.from_label("A", new_values=1)

    def run():
        local_value = 1

        with pytest.raises(InvalidArgumentError, match="local variables cannot be registered"):
            tg.register_ref("A", name="local_value")

    run()


def test_register_ref_rejects_class_endings():
    tg = Triggon.from_label("A", new_values=1)

    class Box:
        pass

    def run():
        box = Box()

        with pytest.raises(InvalidArgumentError, match="must end with an attribute, not a class"):
            tg.register_ref("A", name="box.__class__")

    run()


def test_register_refs_rejects_symbol_prefixed_label():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(InvalidArgumentError):
        tg.register_refs({"*A": {"reg_x": 0}})


def test_register_refs_raises_for_unregistered_label():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(UnregisteredLabelError):
        tg.register_refs({"B": {"reg_x": 0}})


def test_register_refs_raises_for_missing_root_name():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(NameError):
        tg.register_refs({"A": {"missing_root.value": 0}})


def test_is_registered_rejects_missing_names():
    tg = Triggon.from_label("A", new_values=1)

    with pytest.raises(InvalidArgumentError):
        tg.is_registered()


def test_is_registered_rejects_invalid_argument_types():
    tg = Triggon.from_label("A", new_values=1)
    tg.register_ref("A", name="reg_x")

    with pytest.raises(TypeError):
        tg.is_registered(1)

    with pytest.raises(TypeError):
        tg.is_registered("reg_x", label=1)

    with pytest.raises(TypeError):
        tg.is_registered("reg_x", match_all="yes")


def test_is_registered_rejects_symbol_labels():
    tg = Triggon.from_label("A", new_values=1)
    tg.register_ref("A", name="reg_x")

    with pytest.raises(InvalidArgumentError):
        tg.is_registered("reg_x", label="*A")


def test_is_registered_rejects_unknown_labels():
    tg = Triggon.from_label("A", new_values=1)
    tg.register_ref("A", name="reg_x")

    with pytest.raises(UnregisteredLabelError):
        tg.is_registered("reg_x", label="B")


def test_unregister_refs_accepts_single_name_string():
    tg = Triggon.from_label("A", new_values=1)
    tg.register_ref("A", name="reg_x")

    assert tg.is_registered("reg_x") is True

    tg.unregister_refs("reg_x")

    assert tg.is_registered("reg_x") is False


def test_unregister_refs_removes_multiple_names_in_one_call():
    tg = Triggon.from_labels({"A": 1, "B": 2, "C": 3})

    tg.register_ref("A", name="reg_x")
    tg.register_ref("B", name="reg_y")
    tg.register_ref("C", name="GLOBAL_MAIN.a")

    assert tg.is_registered("reg_x", "reg_y", "GLOBAL_MAIN.a") is True

    tg.unregister_refs(("reg_x", "reg_y", "GLOBAL_MAIN.a"))

    assert tg.is_registered("reg_x") is False
    assert tg.is_registered("reg_y") is False
    assert tg.is_registered("GLOBAL_MAIN.a") is False


def test_unregister_refs_filters_targets_by_label():
    tg = Triggon.from_labels({"A": 1, "B": 2})

    tg.register_ref("A", name="reg_x")
    tg.register_ref("B", name="reg_y")

    tg.unregister_refs(("reg_x", "reg_y"), labels="A")

    assert tg.is_registered("reg_x", label="A") is False
    assert tg.is_registered("reg_y", label="B") is True


def test_unregister_refs_rejects_invalid_argument_types():
    tg = Triggon.from_label("A", new_values=1)
    tg.register_ref("A", name="reg_x")

    with pytest.raises(TypeError):
        tg.unregister_refs(1)

    with pytest.raises(TypeError):
        tg.unregister_refs("reg_x", labels=1)


def test_unregister_refs_rejects_symbol_labels():
    tg = Triggon.from_label("A", new_values=1)
    tg.register_ref("A", name="reg_x")

    with pytest.raises(InvalidArgumentError):
        tg.unregister_refs("reg_x", labels="*A")


def test_unregister_refs_rejects_unknown_labels():
    tg = Triggon.from_label("A", new_values=1)
    tg.register_ref("A", name="reg_x")

    with pytest.raises(UnregisteredLabelError):
        tg.unregister_refs("reg_x", labels="B")


def test_is_registered_separates_nested_attr_scopes():
    tg = Triggon.from_label("A", new_values=1)

    class LocalMain:
        a = 0

    def outer():
        m = LocalMain
        tg.register_ref("A", name="m.a")

        def inner():
            m = LocalMain
            return tg.is_registered("m.a")

        return tg.is_registered("m.a"), inner()

    outer_registered, inner_registered = outer()

    assert outer_registered is True
    assert inner_registered is False


def test_register_refs_separates_nested_attr_scopes():
    tg = Triggon.from_label("A", new_values=1)

    class LocalMain:
        a = 0

    def outer():
        m = LocalMain
        tg.register_refs({"A": {"m.a": 0}})

        def inner():
            m = LocalMain
            return tg.is_registered("m.a")

        return tg.is_registered("m.a"), inner()

    outer_registered, inner_registered = outer()

    assert outer_registered is True
    assert inner_registered is False


def test_glob_attr_registration_is_shared_across_funcs():
    tg = Triggon.from_label("A", new_values=1)
    GLOBAL_MAIN.a = 0

    def register_from_one_scope():
        tg.register_ref("A", name="GLOBAL_MAIN.a")

    def inspect_from_other_scope():
        return tg.is_registered("GLOBAL_MAIN.a")

    register_from_one_scope()

    assert inspect_from_other_scope() is True

    tg.unregister_refs("GLOBAL_MAIN.a")

    assert inspect_from_other_scope() is False


def test_register_ref_marks_helper_scope_attr():
    registered_in_helper, _ = _register_ref_scope_state()

    assert registered_in_helper is True


def test_register_ref_does_not_mark_outer_scope_attr():
    registered_in_helper, registered_in_outer = _register_ref_scope_state()

    assert registered_in_helper is True
    assert registered_in_outer is False


def test_unregister_refs_inner_scope_does_not_clear_outer_attr():
    inner_registered, outer_registered_before, outer_registered_after = _unregister_ref_scope_state()

    assert inner_registered is False
    assert outer_registered_before is True


def test_unregister_refs_clears_outer_attr_in_outer_scope():
    inner_registered, outer_registered_before, outer_registered_after = _unregister_ref_scope_state()

    assert inner_registered is False
    assert outer_registered_before is True
    assert outer_registered_after is False
