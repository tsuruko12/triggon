from pathlib import Path
import sys

import pytest

ROOT = str(Path(__file__).resolve().parents[1] / "src")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from triggon import TrigFunc


def glob_trigfunc_target(prefix: str, *, suffix: str) -> str:
    return f"{prefix}global{suffix}"


def test_runs_builtin_len():
    f = TrigFunc()

    assert f.len("abcd")._run() == 4


def test_runs_builtin_sum():
    f = TrigFunc()

    assert f.sum([1, 2, 3])._run() == 6


def test_clones_remain_independent():
    f = TrigFunc()

    len_call = f.len("abcd")
    sum_call = f.sum([1, 2, 3])

    assert len_call._run() == 4
    assert sum_call._run() == 6


def test_runs_glob_callable_with_kwargs():
    f = TrigFunc()

    assert f.glob_trigfunc_target("(", suffix=")")._run() == "(global)"


def test_runs_loc_method_chain():
    f = TrigFunc()

    class Greeter:
        def __init__(self, name: str):
            self.name = name

        def wrap(self, prefix: str, *, suffix: str) -> str:
            return f"{prefix}{self.name}{suffix}"

    greeter = Greeter("neo")

    assert f.greeter.wrap("<", suffix=">")._run() == "<neo>"


def test_retries_lookup_for_late_loc():
    f = TrigFunc()
    deferred = f.make_value("!")

    def inner():
        def make_value(suffix: str) -> str:
            return f"late{suffix}"

        return deferred._run()

    assert inner() == "late!"


def test_rejects_unbound_call():
    with pytest.raises(TypeError, match="not bound to a callable"):
        TrigFunc()()


def test_rejects_running_without_target():
    with pytest.raises(TypeError, match="no deferred target to execute"):
        TrigFunc()._run()


def test_rejects_missing_call_suffix():
    f = TrigFunc()

    with pytest.raises(TypeError, match="must end with a function or method call"):
        f.len._run()


def test_raises_for_missing_root_name():
    f = TrigFunc()

    with pytest.raises(NameError, match=r"'missing_target' is not defined"):
        f.missing_target()._run()


def test_raises_for_missing_attr():
    f = TrigFunc()

    class Box:
        pass

    box = Box()

    with pytest.raises(AttributeError, match=r"object has no attribute 'missing'"):
        f.box.missing()._run()
