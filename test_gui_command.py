"""Unit tests for gui_command.py.

tkinter is eagerly-mocked in ``conftest.py`` so the module can be imported
on any platform.  Individual tests use ``monkeypatch`` or ``patch`` to
wire up specific return values.

Run with: pytest test_gui_command.py -v
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import gui_command
from state import state

# GUI uses ";" as the internal path-list file delimiter (always, not
# platform-dependent).  Test data must use the same separator.
_SEP = ";"


@pytest.fixture(autouse=True)
def _patch_path_list_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Redirect ``gui_command._PATH_LIST_FILE`` to an isolated temp path.

    The real module writes ``path_list.txt`` to the user's app data
    directory.  In tests we want it inside ``tmp_path`` so each test gets
    a clean slate and no real filesystem state is modified.
    """
    monkeypatch.setattr(gui_command, "_PATH_LIST_FILE", tmp_path / "path_list.txt")


@pytest.fixture
def mock_askdirectory() -> MagicMock:
    """Mock tkinter.filedialog.askdirectory to return a fixed path."""
    with patch("gui_command.askdirectory") as mock:
        mock.return_value = "C:\\Users\\Test\\App"
        yield mock


@pytest.fixture
def patch_cmd_path(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Mock cmd_path functions so no real PowerShell calls happen."""
    import cmd_path

    mocks = {
        "get_path": MagicMock(return_value=f"C:\\Windows{_SEP}C:\\Program Files"),
        "add_to_path": MagicMock(),
        "set_path": MagicMock(),
        "save_path_to_file": MagicMock(),
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(cmd_path, name, mock)
    return mocks


# ---------------------------------------------------------------------------
# relative_to_assets
# ---------------------------------------------------------------------------


class TestRelativeToAssets:
    def test_returns_path_under_assets(self) -> None:
        result = gui_command.relative_to_assets("button_1.png")
        # Use os.sep for cross-platform path matching (\ on Windows, / on macOS)
        import os

        expected_suffix = f"assets{os.sep}frame0{os.sep}button_1.png"
        assert str(result).endswith(expected_suffix)


# ---------------------------------------------------------------------------
# create_new_dir
# ---------------------------------------------------------------------------


class TestCreateNewDir:
    def test_shows_info_when_no_directory_selected(
        self, mock_askdirectory: MagicMock
    ) -> None:
        mock_askdirectory.return_value = ""
        with patch.object(gui_command.messagebox, "showinfo") as mock_info:
            gui_command.create_new_dir()
            mock_info.assert_called_once()

    def test_adds_selected_directory_to_path(
        self,
        mock_askdirectory: MagicMock,
        patch_cmd_path: dict[str, MagicMock],
    ) -> None:
        gui_command.create_new_dir()
        patch_cmd_path["add_to_path"].assert_called_once_with("C:\\Users\\Test\\App")

    def test_shows_success_message(
        self,
        mock_askdirectory: MagicMock,
        patch_cmd_path: dict[str, MagicMock],
    ) -> None:
        with patch.object(gui_command.messagebox, "showinfo") as mock_info:
            gui_command.create_new_dir()
            mock_info.assert_called_once()
            assert "Directory Added" in mock_info.call_args[0][0]

    def test_shows_error_on_exception(
        self,
        mock_askdirectory: MagicMock,
        patch_cmd_path: dict[str, MagicMock],
    ) -> None:
        patch_cmd_path["add_to_path"].side_effect = ValueError("Access denied")
        with patch.object(gui_command.messagebox, "showerror") as mock_error:
            gui_command.create_new_dir()
            mock_error.assert_called_once()
            assert "Access denied" in mock_error.call_args[0][1]


# ---------------------------------------------------------------------------
# open_path_editor
# ---------------------------------------------------------------------------


class TestOpenPathEditor:
    def test_shows_info_when_no_path_selected(self) -> None:
        state.selected_path = ""
        with patch.object(gui_command.messagebox, "showinfo") as mock_info:
            gui_command.open_path_editor()
            mock_info.assert_called_once()
            assert "No Path Selected" in mock_info.call_args[0][0]

    def test_creates_popup_when_path_selected(self, tmp_path: Path) -> None:
        state.selected_path = "C:\\Existing\\Path"

        # Create asset files so relative_to_assets succeeds
        assets_dir = tmp_path / "assets" / "frame0"
        assets_dir.mkdir(parents=True)
        (assets_dir / "button_4.png").write_text("")
        (assets_dir / "button_5.png").write_text("")

        with (
            patch("gui_command.Toplevel") as mock_toplevel,
            patch("gui_command.ASSETS_PATH", assets_dir),
        ):
            gui_command.open_path_editor()
            mock_toplevel.assert_called_once()

    def test_loads_button_images(self, tmp_path: Path) -> None:
        state.selected_path = "C:\\Existing\\Path"
        assets_dir = tmp_path / "assets" / "frame0"
        assets_dir.mkdir(parents=True)
        (assets_dir / "button_4.png").write_text("")
        (assets_dir / "button_5.png").write_text("")

        with (
            patch("gui_command.PhotoImage") as mock_img,
            patch("gui_command.ASSETS_PATH", assets_dir),
            patch("gui_command.Toplevel"),
        ):
            gui_command.open_path_editor()
            assert mock_img.call_count >= 2

    def test_shows_error_on_missing_images(self) -> None:
        state.selected_path = "C:\\Existing\\Path"
        with (
            patch("gui_command.Toplevel") as mock_toplevel,
            patch(
                "gui_command.relative_to_assets",
                side_effect=FileNotFoundError("missing"),
            ),
            patch.object(gui_command.messagebox, "showerror") as mock_error,
        ):
            gui_command.open_path_editor()
            mock_error.assert_called_once()
            assert "Asset Error" in mock_error.call_args[0][0]
            mock_toplevel.return_value.destroy.assert_called_once()

    def _run_submit_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        old_path: str = "C:\\Old\\Path",
        new_path_value: str = "C:\\New\\Path",
    ) -> MagicMock:
        """Helper: set up the environment and invoke the submit_path closure.

        Creates the ``path_list.txt`` file in ``gui_command._PATH_LIST_FILE``
        (which is patched to ``tmp_path / path_list.txt`` by the autouse
        ``_patch_path_list_file`` fixture).
        Uses a fresh Button mock to avoid cross-test state pollution from the
        module-level mock in conftest.py.

        Returns the ``set_path`` mock so callers can make assertions.
        """
        state.selected_path = old_path

        # Create the path list file via gui_command's patched path
        path_list = gui_command._PATH_LIST_FILE
        content = f"C:\\Windows{_SEP}{old_path}{_SEP}C:\\Other{_SEP}"
        path_list.write_text(content, encoding="utf-8")

        # Create asset files
        assets_dir = tmp_path / "assets" / "frame0"
        assets_dir.mkdir(parents=True)
        (assets_dir / "button_4.png").write_text("")
        (assets_dir / "button_5.png").write_text("")

        # We need StringVar.get() to return our new path
        mock_stringvar_instance = MagicMock()
        mock_stringvar_instance.get.return_value = new_path_value

        with (
            patch("gui_command.ASSETS_PATH", assets_dir),
            patch("gui_command.Toplevel"),
            patch("gui_command.StringVar", return_value=mock_stringvar_instance),
            patch("gui_command.cmd_path.set_path") as mock_set_path,
            patch("gui_command.Button") as mock_button,
        ):
            gui_command.open_path_editor()

            # Find the submit button by looking for a Button() call with
            # "command" in its kwargs, where the command contains "submit".
            for btn_call in mock_button.call_args_list:
                _, kwargs = btn_call
                cmd = kwargs.get("command")
                if cmd and "submit" in str(cmd).lower():
                    cmd()  # invoke the closure
                    break

        return mock_set_path

    def test_submit_replaces_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Submit replaces the selected path and calls set_path."""
        mock_set_path = self._run_submit_path(tmp_path, monkeypatch)
        mock_set_path.assert_called_once()
        # The new path should be in the call argument
        call_arg = mock_set_path.call_args[0][0]
        assert "C:\\New\\Path" in call_arg
        assert "C:\\Old\\Path" not in call_arg

    def test_submit_updates_path_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Submit writes the updated paths back to the file."""
        path_list = gui_command._PATH_LIST_FILE
        old_content = f"C:\\Windows{_SEP}C:\\Old\\Path{_SEP}C:\\Other{_SEP}"
        path_list.write_text(old_content, encoding="utf-8")

        state.selected_path = "C:\\Old\\Path"
        assets_dir = tmp_path / "assets" / "frame0"
        assets_dir.mkdir(parents=True)
        (assets_dir / "button_4.png").write_text("")
        (assets_dir / "button_5.png").write_text("")

        mock_stringvar = MagicMock()
        mock_stringvar.get.return_value = "C:\\New\\Path"

        with (
            patch("gui_command.ASSETS_PATH", assets_dir),
            patch("gui_command.Toplevel"),
            patch("gui_command.StringVar", return_value=mock_stringvar),
            patch("gui_command.cmd_path.set_path"),
            patch("gui_command.Button") as mock_button,
        ):
            gui_command.open_path_editor()
            for _, kwargs in mock_button.call_args_list:
                cmd = kwargs.get("command")
                if cmd and "submit" in str(cmd).lower():
                    cmd()
                    break

        updated = path_list.read_text(encoding="utf-8")
        assert "C:\\New\\Path" in updated
        assert "C:\\Old\\Path" not in updated

    def test_submit_empty_path_shows_error(self, tmp_path: Path) -> None:
        """Submitting an empty path should show an error."""
        path_list = tmp_path / "path_list.txt"
        path_list.write_text(f"C:\\Windows{_SEP}C:\\Old{_SEP}", encoding="utf-8")

        state.selected_path = "C:\\Old"
        assets_dir = tmp_path / "assets" / "frame0"
        assets_dir.mkdir(parents=True)
        (assets_dir / "button_4.png").write_text("")
        (assets_dir / "button_5.png").write_text("")

        mock_stringvar = MagicMock()
        mock_stringvar.get.return_value = ""  # empty!

        with (
            patch("gui_command.ASSETS_PATH", assets_dir),
            patch("gui_command.Toplevel"),
            patch("gui_command.StringVar", return_value=mock_stringvar),
            patch("gui_command.cmd_path.set_path") as mock_set_path,
            patch.object(gui_command.messagebox, "showerror") as mock_error,
            patch("gui_command.Button") as mock_button,
        ):
            gui_command.open_path_editor()
            for _, kwargs in mock_button.call_args_list:
                cmd = kwargs.get("command")
                if cmd and "submit" in str(cmd).lower():
                    cmd()
                    break

            mock_error.assert_called_once()
            assert "Path cannot be empty" in mock_error.call_args[0][1]
            mock_set_path.assert_not_called()

    def test_cancel_destroys_popup(self, tmp_path: Path) -> None:
        """Cancel button destroys the popup without saving."""
        state.selected_path = "C:\\Existing"
        assets_dir = tmp_path / "assets" / "frame0"
        assets_dir.mkdir(parents=True)
        (assets_dir / "button_4.png").write_text("")
        (assets_dir / "button_5.png").write_text("")

        with (
            patch("gui_command.ASSETS_PATH", assets_dir),
            patch("gui_command.Toplevel") as mock_toplevel,
            patch("gui_command.cmd_path.set_path") as mock_set_path,
            patch("gui_command.Button") as mock_button,
        ):
            gui_command.open_path_editor()
            # Find the cancel button command and invoke it
            for _, kwargs in mock_button.call_args_list:
                cmd = kwargs.get("command")
                if cmd and "cancel" in str(cmd).lower():
                    cmd()
                    break

            mock_toplevel.return_value.destroy.assert_called()
            mock_set_path.assert_not_called()


# ---------------------------------------------------------------------------
# create_scrollable_path_list
# ---------------------------------------------------------------------------


class TestCreateScrollablePathList:
    def test_shows_error_when_get_path_fails(
        self, patch_cmd_path: dict[str, MagicMock]
    ) -> None:
        patch_cmd_path["get_path"].side_effect = ValueError("Access denied")
        with patch.object(gui_command.messagebox, "showerror") as mock_error:
            gui_command.create_scrollable_path_list(MagicMock())
            mock_error.assert_called_once()
            assert "Failed to retrieve PATH" in mock_error.call_args[0][1]

    def test_writes_to_path_list_file(
        self, patch_cmd_path: dict[str, MagicMock], tmp_path: Path
    ) -> None:
        """Verify the path list file is written by create_scrollable_path_list."""
        gui_command.create_scrollable_path_list(MagicMock())
        path_list = tmp_path / "path_list.txt"
        assert path_list.exists()
        content = path_list.read_text(encoding="utf-8")
        assert "C:\\Windows" in content
        assert "C:\\Program Files" in content

    def test_reads_paths_from_file_and_populates_listbox(
        self,
        patch_cmd_path: dict[str, MagicMock],
        tmp_path: Path,
    ) -> None:
        """Verify paths from mocked get_path() are inserted into the listbox.

        ``create_scrollable_path_list`` calls ``get_path()`` and overwrites
        the file before reading it, so the listbox reflects the mocked path
        string, not any pre-written file content.
        """
        with patch("gui_command.Listbox") as mock_listbox_cls:
            mock_listbox = MagicMock()
            mock_listbox_cls.return_value = mock_listbox

            gui_command.create_scrollable_path_list(MagicMock())

            insert_calls = [c for c in mock_listbox.mock_calls if c[0] == "insert"]
            inserted_paths = [str(c[1][1]) for c in insert_calls if len(c[1]) > 1]
            assert "C:\\Windows" in inserted_paths
            assert "C:\\Program Files" in inserted_paths

    def test_shows_error_on_read_failure(
        self,
        patch_cmd_path: dict[str, MagicMock],
        tmp_path: Path,
    ) -> None:
        """When reading the path file fails, show an error."""
        path_list = tmp_path / "path_list.txt"
        path_list.write_text(f"C:\\Windows{_SEP}", encoding="utf-8")

        with (
            patch.object(Path, "read_text", side_effect=PermissionError("denied")),
            patch.object(gui_command.messagebox, "showerror") as mock_error,
        ):
            gui_command.create_scrollable_path_list(MagicMock())
            mock_error.assert_called_once()
            assert "Failed to read path list" in mock_error.call_args[0][1]

    def test_on_select_updates_selected_path(
        self,
        patch_cmd_path: dict[str, MagicMock],
        tmp_path: Path,
    ) -> None:
        """Simulate clicking on an item in the listbox."""
        path_list = tmp_path / "path_list.txt"
        path_list.write_text(
            f"C:\\Windows{_SEP}C:\\Program Files{_SEP}",
            encoding="utf-8",
        )

        # Capture the callback that gets bound to <<ListboxSelect>>
        captured_callback: dict = {}

        def capture_bind(event: str, callback: object) -> None:
            captured_callback["event"] = event
            captured_callback["callback"] = callback

        mock_listbox = MagicMock()
        mock_listbox.bind.side_effect = capture_bind
        mock_listbox.curselection.return_value = (1,)
        mock_listbox.get.return_value = "C:\\Program Files"

        with patch("gui_command.Listbox", return_value=mock_listbox):
            gui_command.create_scrollable_path_list(MagicMock())

            # Now trigger the on_select callback directly
            assert captured_callback["event"] == "<<ListboxSelect>>"
            captured_callback["callback"](None)

            assert state.selected_path == "C:\\Program Files"
