from pathlib import Path
import sys
from time import monotonic, sleep

ROOT = str(Path(__file__).resolve().parents[1] / "src")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from triggon import TrigFunc, Triggon


debug_registered_value = 0


def wait_until(predicate, timeout: float = 0.4, interval: float = 0.005) -> None:
    deadline = monotonic() + timeout

    while monotonic() < deadline:
        if predicate():
            return
        sleep(interval)

    assert predicate()


def _flush_debug_handlers(tg: Triggon) -> None:
    logger = tg._logger
    if logger is None:
        return

    for handler in logger.handlers:
        handler.flush()


def _close_debug_handlers(tg: Triggon) -> None:
    logger = tg._logger
    if logger is None:
        return

    for handler in list(logger.handlers):
        handler.flush()
        handler.close()
        logger.removeHandler(handler)


def _capture_debug_stderr(tg: Triggon, capsys, action, clear_before: bool = True) -> str:
    try:
        if clear_before:
            capsys.readouterr()
        action()
        _flush_debug_handlers(tg)
        return capsys.readouterr().err
    finally:
        _close_debug_handlers(tg)


def test_level_1_logs_trigger(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "1")
    tg = Triggon.from_label("A", new_values=10, debug=True)

    def action():
        tg.set_trigger("A")

    err = _capture_debug_stderr(tg, capsys, action)

    assert "Label 'A' is active" in err


def test_level_1_omits_switch_values(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "1")
    tg = Triggon.from_label("A", new_values=10, debug=True)

    def action():
        tg.set_trigger("A")
        tg.switch_lit("A", original_val=0)

    err = _capture_debug_stderr(tg, capsys, action)

    assert "0 -> 10" not in err


def test_level_2_logs_value_update(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "2")
    tg = Triggon.from_label("A", new_values=10, debug=True)
    global debug_registered_value
    debug_registered_value = 0

    def action():
        tg.register_ref("A", name="debug_registered_value")
        tg.set_trigger("A")

    err = _capture_debug_stderr(tg, capsys, action)

    assert "Label 'A' is active" in err
    assert "debug_registered_value: 0 -> 10" in err


def test_level_2_logs_switch_lit(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "2")
    tg = Triggon.from_label("A", new_values=10, debug=True)

    def read_value():
        return tg.switch_lit("A", original_val=0)

    def action():
        assert read_value() == 0
        tg.set_trigger("A")
        assert read_value() == 10
        tg.revert("A")
        assert read_value() == 0

    err = _capture_debug_stderr(tg, capsys, action)

    assert "0 -> 10" in err
    assert "10 -> 0" in err


def test_level_1_logs_inactive(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "1")
    tg = Triggon.from_label("A", new_values=10, debug=True)

    def action():
        tg.set_trigger("A")
        tg.revert("A")

    err = _capture_debug_stderr(tg, capsys, action)

    assert "Label 'A' is inactive" in err


def test_level_1_logs_disabled(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "1")
    tg = Triggon.from_label("A", new_values=10, debug=True)

    def action():
        tg.set_trigger("A")
        tg.revert("A", disable=True)

    err = _capture_debug_stderr(tg, capsys, action)

    assert "Label 'A' is disabled" in err


def test_level_3_logs_register(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "3")
    tg = Triggon.from_label("A", new_values=10, debug=True)
    global debug_registered_value
    debug_registered_value = 0

    def action():
        tg.register_ref("A", name="debug_registered_value")

    err = _capture_debug_stderr(tg, capsys, action)

    assert "'debug_registered_value' was registered under label 'A'" in err


def test_level_3_logs_unregister(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "3")
    tg = Triggon.from_label("A", new_values=10, debug=True)
    global debug_registered_value
    debug_registered_value = 0

    def action():
        tg.register_ref("A", name="debug_registered_value")
        tg.unregister_refs("debug_registered_value")

    err = _capture_debug_stderr(tg, capsys, action)

    assert "'debug_registered_value' was unregistered from label 'A'" in err


def test_level_3_logs_delayed_trigger(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "3")
    tg = Triggon.from_label("A", new_values=10, debug=True)

    def action():
        tg.set_trigger("A", after=0.01)
        wait_until(lambda: tg.is_triggered("A"))

    err = _capture_debug_stderr(tg, capsys, action)

    assert "Label 'A' will be active after 0.01s" in err
    assert "Label 'A' is active" in err


def test_level_3_logs_delayed_revert(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "3")
    tg = Triggon.from_label("A", new_values=10, debug=True)

    def action():
        tg.set_trigger("A")
        tg.revert("A", after=0.01)
        wait_until(lambda: not tg.is_triggered("A"))

    err = _capture_debug_stderr(tg, capsys, action)

    assert "Label 'A' will be inactive after 0.01s" in err
    assert "Label 'A' is inactive" in err


def test_level_3_logs_delayed_disable(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "3")
    tg = Triggon.from_label("A", new_values=10, debug=True)

    def action():
        tg.set_trigger("A")
        tg.revert("A", after=0.01, disable=True)
        wait_until(lambda: not tg.is_triggered("A"))

    err = _capture_debug_stderr(tg, capsys, action)

    assert "Label 'A' will be disabled after 0.01s" in err
    assert "Label 'A' is disabled" in err


def test_level_1_logs_early_return(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "1")
    tg = Triggon.from_label("A", new_values=10, debug=True)

    def action():
        with tg.capture_return():
            tg.set_trigger("A")
            tg.trigger_return("A", value=123)

    err = _capture_debug_stderr(tg, capsys, action)

    assert "Early return triggered (return_value=123)" in err


def test_level_1_logs_trigger_call(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "1")
    tg = Triggon.from_label("A", new_values=10, debug=True)
    f = TrigFunc()

    def action():
        tg.set_trigger("A")
        tg.trigger_call("A", f.len("abc"))

    err = _capture_debug_stderr(tg, capsys, action)

    assert "Trigger call executed (target=len('abc'))" in err


def test_env_label_filter(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "1")
    monkeypatch.setenv("TRIGGON_LOG_LABELS", "B")
    tg = Triggon.from_labels({"A": 10, "B": 20}, debug=True)

    def action():
        tg.set_trigger(("A", "B"))

    err = _capture_debug_stderr(tg, capsys, action)

    assert "Label 'B' is active" in err
    assert "Label 'A' is active" not in err


def test_invalid_label_filter_warns(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "1")
    monkeypatch.setenv("TRIGGON_LOG_LABELS", "missing, B")
    tg = Triggon.from_labels({"A": 10, "B": 20}, debug=True)

    def action():
        tg.set_trigger(("A", "B"))

    err = _capture_debug_stderr(tg, capsys, action, clear_before=False)

    assert "label 'missing' is not registered" in err


def test_invalid_label_filter_keeps_valid_labels(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "1")
    monkeypatch.setenv("TRIGGON_LOG_LABELS", "missing, B")
    tg = Triggon.from_labels({"A": 10, "B": 20}, debug=True)

    def action():
        tg.set_trigger(("A", "B"))

    err = _capture_debug_stderr(tg, capsys, action, clear_before=False)

    assert "Label 'B' is active" in err
    assert "Label 'A' is active" not in err


def test_string_filter(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "1")
    tg = Triggon.from_labels({"A": 10, "B": 20}, debug="B")

    def action():
        tg.set_trigger(("A", "B"))

    err = _capture_debug_stderr(tg, capsys, action)

    assert "Label 'B' is active" in err
    assert "Label 'A' is active" not in err


def test_file_output(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "1")
    log_file = Path(__file__).with_name("_debug_env_output.log")
    if log_file.exists():
        log_file.unlink()
    monkeypatch.setenv("TRIGGON_LOG_FILE", str(log_file))
    tg = Triggon.from_label("A", new_values=10, debug=True)

    try:
        def action():
            tg.set_trigger("A")

        err = _capture_debug_stderr(tg, capsys, action)

        assert err == ""
        assert "Label 'A' is active" in log_file.read_text(encoding="utf-8")
    finally:
        if log_file.exists():
            log_file.unlink()


def test_invalid_file_falls_back_to_terminal(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "1")
    monkeypatch.setenv("TRIGGON_LOG_FILE", str(Path(__file__).parent))
    tg = Triggon.from_label("A", new_values=10, debug=True)

    def action():
        tg.set_trigger("A")

    err = _capture_debug_stderr(tg, capsys, action, clear_before=False)

    assert "Failed to create the debug log file:" in err
    assert "Falling back to terminal output." in err
    assert "Label 'A' is active" in err


def test_false_ignores_env_logging(monkeypatch, capsys):
    monkeypatch.setenv("TRIGGON_LOG_VERBOSITY", "3")
    tg = Triggon.from_label("A", new_values=10, debug=False)

    capsys.readouterr()
    tg.set_trigger("A")
    captured = capsys.readouterr()

    assert captured.err == ""
