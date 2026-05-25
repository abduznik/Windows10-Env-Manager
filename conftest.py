"""Shared pytest fixtures for the Windows10-Env-Manager test suite.

This module mocks tkinter at import time so that ``gui_command`` can be
imported on systems without a display or the ``_tkinter`` C extension.

Why real classes instead of MagicMock for tkinter stubs?
---------------------------------------------------------
Using ``MagicMock`` as tkinter widget classes causes
``InvalidSpecError`` when the GUI code passes a MagicMock instance as a
positional argument (e.g. ``Label(popup, …)``), because MagicMock
interprets positional args as a potential ``spec``.

Simple classes avoid this entirely while still being lightweight.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Lightweight tkinter stubs – callable, pass positional args without error
# ---------------------------------------------------------------------------


class _StubWidget:
    """Callable stub that returns a MagicMock, ignoring positional args."""

    def __new__(cls, *args: object, **kwargs: object) -> MagicMock:
        return MagicMock()


class _StubToplevel(_StubWidget):
    """Toplevel with extra attributes used by gui_command."""

    def __new__(cls, *args: object, **kwargs: object) -> MagicMock:
        inst = MagicMock()
        inst.submit_image = None
        inst.cancel_image = None
        inst.destroy = MagicMock()
        return inst


class _StubStringVar:
    """Lightweight StringVar replacement."""

    def __init__(self, **kwargs: object) -> None:
        self._value: str = kwargs.get("value", "")

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


class _StubMessageBox:
    """Messagebox stub – accepts positional args like the real API."""

    @staticmethod
    def showinfo(*args: object, **kwargs: object) -> None:
        pass

    @staticmethod
    def showerror(*args: object, **kwargs: object) -> None:
        pass

    @staticmethod
    def showwarning(*args: object, **kwargs: object) -> None:
        pass

    @staticmethod
    def askyesno(*args: object, **kwargs: object) -> bool:
        return True


class _StubFileDialog:
    """Filedialog stub."""

    @staticmethod
    def askdirectory(*args: object, **kwargs: object) -> str:
        return ""


# -- Build the stub module object and insert into sys.modules ---------------

_tkinter_stub = MagicMock()
_tkinter_stub.Tk = _StubWidget
_tkinter_stub.Canvas = _StubWidget
_tkinter_stub.Button = _StubWidget
_tkinter_stub.PhotoImage = _StubWidget
_tkinter_stub.Frame = _StubWidget
_tkinter_stub.Listbox = _StubWidget
_tkinter_stub.Toplevel = _StubToplevel
_tkinter_stub.Entry = _StubWidget
_tkinter_stub.Label = _StubWidget
_tkinter_stub.StringVar = _StubStringVar
_tkinter_stub.SINGLE = "single"
_tkinter_stub.messagebox = _StubMessageBox
_tkinter_stub.filedialog = _StubFileDialog

sys.modules.setdefault("tkinter", _tkinter_stub)
sys.modules.setdefault("tkinter.filedialog", _StubFileDialog)
sys.modules.setdefault("tkinter.messagebox", _StubMessageBox)


@pytest.fixture(autouse=True)
def mock_windll(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock ctypes.windll so all tests work on non-Windows platforms."""
    import ctypes

    mock_shell32 = MagicMock()
    mock_shell32.IsUserAnAdmin.return_value = True
    monkeypatch.setattr(ctypes, "windll", MagicMock(shell32=mock_shell32), raising=False)


@pytest.fixture(autouse=True)
def _reset_selected_path() -> None:
    """Reset selected_path before each test to avoid cross-test leakage."""
    import state as _state_module

    _state_module.state.selected_path = ""


@pytest.fixture
def tmp_project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Change to a temporary directory for file-based tests."""
    monkeypatch.chdir(tmp_path)
    return tmp_path
