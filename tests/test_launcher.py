from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_launch():
    spec = importlib.util.spec_from_file_location("kaizen_launch", ROOT / "scripts" / "launch.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_port_range_is_valid_and_expected():
    launch = _load_launch()
    assert launch.START_PORT == 9550
    assert launch.END_PORT == 9589
    assert launch.START_PORT <= launch.END_PORT


def test_first_free_port_returns_within_range():
    launch = _load_launch()
    port = launch.first_free_port()
    assert 9550 <= port <= 9589


def test_invalid_range_raises_clear_error():
    launch = _load_launch()
    old_start, old_end = launch.START_PORT, launch.END_PORT
    try:
        launch.START_PORT = 10
        launch.END_PORT = 9
        try:
            launch.first_free_port()
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "Invalid local port range" in str(exc)
    finally:
        launch.START_PORT, launch.END_PORT = old_start, old_end

def test_batch_launcher_pauses_on_launch_error():
    text = (ROOT / "START_KAIZEN.bat").read_text(encoding="utf-8")
    assert "python scripts\\launch.py" in text
    assert "if errorlevel 1 goto :error" in text
    assert "pause" in text.lower()
    assert "9550-9589" in text
