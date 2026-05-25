"""Unit tests for cmd_path.py.

Tests are designed to run on any platform (non-Windows tests mock the
PowerShell calls to avoid actual system modifications).

Run with: pytest test_cmd_path.py -v

Note: ``ctypes.windll`` is mocked globally by the ``mock_windll`` fixture in
``conftest.py``.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import cmd_path


@pytest.fixture(autouse=True)
def _patch_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force Windows code paths for all tests in this file.

    ``cmd_path._IS_WINDOWS`` controls whether the module uses PowerShell
    (Windows) or ``os.environ`` / shell config (Unix).  On non-Windows CI
    runners we want to test the PowerShell code paths, so we set the flag
    to ``True`` for every test.
    """
    monkeypatch.setattr(cmd_path, "_IS_WINDOWS", True)


@pytest.fixture(autouse=True)
def _patch_backup_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Redirect the backup directory to a temporary path.

    ``cmd_path._backup_dir()`` normally returns the user's app data
    directory (e.g. ``~/Library/Application Support/…``).  In tests we
    want versioned backup files to be written to the isolated ``tmp_path``
    instead.
    """
    monkeypatch.setattr(cmd_path, "_backup_dir", lambda: tmp_path)


# ---------------------------------------------------------------------------
# check_admin
# ---------------------------------------------------------------------------


class TestCheckAdmin:
    def test_returns_true_when_admin(self) -> None:
        assert cmd_path.check_admin() is True

    @patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=False)
    def test_returns_false_when_not_admin(self, mock_is_admin: MagicMock) -> None:
        assert cmd_path.check_admin() is False

    @patch("ctypes.windll.shell32.IsUserAnAdmin", side_effect=AttributeError)
    def test_handles_attribute_error(self, mock_is_admin: MagicMock) -> None:
        """When ctypes.windll is unavailable (e.g. non-Windows), returns False."""
        result = cmd_path.check_admin()
        assert result is False


# ---------------------------------------------------------------------------
# get_path
# ---------------------------------------------------------------------------


class TestGetPath:
    @patch("subprocess.run")
    def test_returns_stdout_on_success(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "C:\\Windows;C:\\Program Files\n"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = cmd_path.get_path()
        assert result == "C:\\Windows;C:\\Program Files"

    @patch("subprocess.run")
    def test_raises_on_failure(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "Access denied"
        mock_run.return_value = mock_process

        with pytest.raises(ValueError, match="Failed to retrieve PATH"):
            cmd_path.get_path()

    @patch("subprocess.run")
    def test_defaults_to_machine_scope(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.get_path()
        # Verify the command includes 'Machine'
        command = mock_run.call_args[0][0]
        assert "Machine" in " ".join(command)

    @patch("subprocess.run")
    def test_uses_user_scope(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.get_path(scope="User")
        command = mock_run.call_args[0][0]
        assert "User" in " ".join(command)


# ---------------------------------------------------------------------------
# set_path
# ---------------------------------------------------------------------------


class TestSetPath:
    @patch("subprocess.run")
    def test_sets_path_successfully(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.set_path("C:\\MyApp")
        # subprocess.run is called by backup_path->get_path AND set_path
        assert mock_run.call_count >= 2

    @patch("subprocess.run")
    def test_raises_on_failure(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = "Access denied"
        mock_run.return_value = mock_process

        with pytest.raises(ValueError, match="Failed to set PATH"):
            cmd_path.set_path("C:\\Test")

    @patch("subprocess.run")
    def test_escapes_double_quotes(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        path_with_quotes = 'C:\\My"App'
        cmd_path.set_path(path_with_quotes)

        # Last subprocess call should be the set_path PowerShell command
        last_call = mock_run.call_args_list[-1]
        command_str = " ".join(last_call[0][0])
        assert '\\\\"' in command_str or 'My\\"App' in command_str


# ---------------------------------------------------------------------------
# save_path_to_file
# ---------------------------------------------------------------------------


class TestSavePathToFile:
    def test_writes_path_string_to_file(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_path.txt"
        cmd_path.save_path_to_file("C:\\Path1;C:\\Path2", str(test_file))
        assert test_file.read_text(encoding="utf-8") == "C:\\Path1;C:\\Path2"

    def test_creates_file_if_not_exists(self, tmp_path: Path) -> None:
        test_file = tmp_path / "new_path_list.txt"
        assert not test_file.exists()
        cmd_path.save_path_to_file("C:\\Test", str(test_file))
        assert test_file.exists()

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        test_file = tmp_path / "overwrite_test.txt"
        test_file.write_text("old content", encoding="utf-8")
        cmd_path.save_path_to_file("new content", str(test_file))
        assert test_file.read_text(encoding="utf-8") == "new content"


# ---------------------------------------------------------------------------
# clear_path
# ---------------------------------------------------------------------------


class TestClearPath:
    @patch("subprocess.run")
    def test_clears_path_successfully(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.clear_path(confirm=True)
        # subprocess.run is called by backup_path->get_path AND clear_path
        assert mock_run.call_count >= 2

    @patch("subprocess.run")
    def test_raises_on_failure(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = "Access denied"
        mock_run.return_value = mock_process

        with pytest.raises(ValueError, match="Failed to clear PATH"):
            cmd_path.clear_path(confirm=True)


# ---------------------------------------------------------------------------
# add_to_path
# ---------------------------------------------------------------------------


class TestAddToPath:
    @patch("cmd_path.get_path")
    @patch("cmd_path.set_path")
    def test_adds_new_path(
        self,
        mock_set_path: MagicMock,
        mock_get_path: MagicMock,
    ) -> None:
        mock_get_path.return_value = "C:\\Windows;C:\\Program Files"
        cmd_path.add_to_path("C:\\MyApp")
        mock_set_path.assert_called_once_with(
            "C:\\Windows;C:\\Program Files;C:\\MyApp;", "Machine"
        )

    @patch("cmd_path.get_path")
    @patch("cmd_path.set_path")
    def test_skips_duplicate_path(
        self,
        mock_set_path: MagicMock,
        mock_get_path: MagicMock,
    ) -> None:
        mock_get_path.return_value = "C:\\Windows;C:\\MyApp"
        cmd_path.add_to_path("C:\\MyApp")
        mock_set_path.assert_not_called()

    @patch("cmd_path.get_path")
    @patch("cmd_path.set_path")
    def test_handles_multiple_new_paths(
        self,
        mock_set_path: MagicMock,
        mock_get_path: MagicMock,
    ) -> None:
        mock_get_path.return_value = "C:\\Windows"
        cmd_path.add_to_path("C:\\App1;C:\\App2")
        mock_set_path.assert_called_once_with(
            "C:\\Windows;C:\\App1;C:\\App2;", "Machine"
        )

    @patch("cmd_path.get_path")
    @patch("cmd_path.set_path")
    def test_skips_duplicates_in_multiple_paths(
        self,
        mock_set_path: MagicMock,
        mock_get_path: MagicMock,
    ) -> None:
        mock_get_path.return_value = "C:\\Windows;C:\\Existing"
        cmd_path.add_to_path("C:\\Existing;C:\\NewApp")
        mock_set_path.assert_called_once_with(
            "C:\\Windows;C:\\Existing;C:\\NewApp;", "Machine"
        )

    @patch("cmd_path.get_path")
    @patch("cmd_path.set_path")
    def test_uses_user_scope(
        self,
        mock_set_path: MagicMock,
        mock_get_path: MagicMock,
    ) -> None:
        mock_get_path.return_value = "C:\\Windows"
        cmd_path.add_to_path("C:\\MyApp", system_wide=False)
        mock_set_path.assert_called_once_with("C:\\Windows;C:\\MyApp;", "User")

    def test_raises_on_empty_path(self) -> None:
        with pytest.raises(ValueError, match="Cannot add an empty path"):
            cmd_path.add_to_path("")

    def test_raises_on_only_whitespace(self) -> None:
        with pytest.raises(ValueError, match="Cannot add an empty path"):
            cmd_path.add_to_path("   ")

    @patch("cmd_path.get_path")
    def test_raises_on_no_valid_paths(self, mock_get_path: MagicMock) -> None:
        mock_get_path.return_value = "C:\\Windows"
        with pytest.raises(ValueError, match="No valid paths"):
            cmd_path.add_to_path(";;;")


# ---------------------------------------------------------------------------
# Protection: set_path rejects empty / separator-only values
# ---------------------------------------------------------------------------


class TestSetPathProtection:
    """``set_path`` must refuse values that would effectively delete PATH."""

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError, match="empty value"):
            cmd_path.set_path("")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="empty value"):
            cmd_path.set_path("   \t\n")

    def test_rejects_only_separators(self) -> None:
        with pytest.raises(ValueError, match="separators"):
            cmd_path.set_path(";;;")

    def test_rejects_mixed_separators_and_whitespace(self) -> None:
        with pytest.raises(ValueError, match="separators"):
            cmd_path.set_path(" ; ; \n")

    @patch("subprocess.run")
    def test_accepts_valid_path(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        # Should not raise
        cmd_path.set_path("C:\\Windows")
        assert mock_run.call_count >= 2


# ---------------------------------------------------------------------------
# Protection: clear_path requires explicit confirm flag
# ---------------------------------------------------------------------------


class TestClearPathProtection:
    """``clear_path`` must refuse without an explicit ``confirm=True``."""

    @patch("subprocess.run")
    def test_refuses_without_confirm(self, mock_run: MagicMock) -> None:
        with pytest.raises(ValueError, match="confirm"):
            cmd_path.clear_path()
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_refuses_with_explicit_false(self, mock_run: MagicMock) -> None:
        with pytest.raises(ValueError, match="confirm"):
            cmd_path.clear_path(confirm=False)
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_accepts_with_confirm_true(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.clear_path(confirm=True)
        assert mock_run.call_count >= 2


# ---------------------------------------------------------------------------
# Protection: add_to_path must never accidentally wipe PATH
# ---------------------------------------------------------------------------


class TestAddToPathProtection:
    """``add_to_path`` must not be able to produce an empty result."""

    @patch("cmd_path.get_path")
    def test_cannot_add_all_separators(self, mock_get_path: MagicMock) -> None:
        mock_get_path.return_value = "C:\\Windows"
        with pytest.raises(ValueError, match="No valid paths"):
            cmd_path.add_to_path(";;;")

    @patch("cmd_path.get_path")
    def test_cannot_add_all_whitespace(self, mock_get_path: MagicMock) -> None:
        mock_get_path.return_value = "C:\\Windows"
        with pytest.raises(ValueError, match="Cannot add an empty path"):
            cmd_path.add_to_path("   \t\n")

    @patch("cmd_path.get_path")
    def test_raises_on_empty_path(self, mock_get_path: MagicMock) -> None:
        mock_get_path.return_value = "C:\\Windows"
        with pytest.raises(ValueError, match="Cannot add an empty path"):
            cmd_path.add_to_path("")

    @patch("cmd_path.get_path")
    def test_cannot_wipe_existing_by_adding_nothing(
        self, mock_get_path: MagicMock
    ) -> None:
        """Even if the current path is also empty, add_to_path must raise."""
        mock_get_path.return_value = ""
        with pytest.raises(ValueError, match="Cannot add an empty path"):
            cmd_path.add_to_path("")

    @patch("cmd_path.get_path")
    @patch("cmd_path.set_path")
    def test_never_calls_set_path_with_separator_only(
        self,
        mock_set_path: MagicMock,
        mock_get_path: MagicMock,
    ) -> None:
        """If the current path is empty but valid entries are added."""
        mock_get_path.return_value = ""
        cmd_path.add_to_path("C:\\NewApp")
        mock_set_path.assert_called_once()
        # Must not be just separators
        args, _ = mock_set_path.call_args
        assert args[0].strip(";"), f"PATH should not be empty: {args[0]!r}"


# ---------------------------------------------------------------------------
# save_path_to_file (default filename)
# ---------------------------------------------------------------------------


class TestSavePathToFileDefault:
    def test_writes_to_default_filename(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify default file name is path_list.txt."""
        defaults = tmp_path / "path_list.txt"
        monkeypatch.chdir(tmp_path)
        assert not defaults.exists()

        cmd_path.save_path_to_file("C:\\Test")
        assert defaults.exists()
        assert defaults.read_text(encoding="utf-8") == "C:\\Test"


# ---------------------------------------------------------------------------
# Backup / Restore
# ---------------------------------------------------------------------------


class TestBackupPath:
    """Versioned backups via ``backup_path`` and ``restore_path`` on Windows."""

    @patch("subprocess.run")
    def test_backup_creates_versioned_file(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "C:\\Windows;C:\\Program Files\n"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = cmd_path.backup_path()

        assert result == "C:\\Windows;C:\\Program Files"

        # Should create a versioned file: path_backup_20260525T120000.json
        files = list(tmp_path.glob("path_backup_*.json"))
        assert len(files) == 1

        import json

        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["path"] == "C:\\Windows;C:\\Program Files"
        assert data["scope"] == "Machine"
        assert "timestamp" in data

    @patch("subprocess.run")
    def test_backup_returns_current_path(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "C:\\MyPath\n"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = cmd_path.backup_path()
        assert result == "C:\\MyPath"

    def test_restore_raises_when_no_backup(self) -> None:
        with pytest.raises(FileNotFoundError, match="No PATH backups"):
            cmd_path.restore_path()

    @patch("subprocess.run")
    def test_restore_sets_path_from_newest_backup(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "C:\\Original\n"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.backup_path()
        cmd_path.restore_path()

        last_call = mock_run.call_args
        command_str = " ".join(last_call[0][0])
        assert "C:\\Original" in command_str

    @patch("subprocess.run")
    def test_multiple_backups_create_separate_files(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Each call to backup_path creates a distinct file."""
        call_count: int = 0
        responses: list[str] = [
            "C:\\First",
            "C:\\Second",
            "C:\\Third",
        ]

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            mp = MagicMock()
            mp.returncode = 0
            mp.stdout = responses[call_count] + "\n"
            mp.stderr = ""
            call_count += 1
            return mp

        mock_run.side_effect = side_effect

        cmd_path.backup_path()
        cmd_path.backup_path()
        cmd_path.backup_path()

        files = sorted(tmp_path.glob("path_backup_*.json"))
        assert len(files) == 3, f"Expected 3 backup files, got {len(files)}: {files}"

    @patch("subprocess.run")
    def test_restore_at_index_picks_correct_backup(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """restore_at_index(1) restores the second-newest backup."""
        call_count: int = 0
        responses: list[str] = ["C:\\Oldest", "C:\\Middle", "C:\\Newest"]

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            mp = MagicMock()
            mp.returncode = 0
            mp.stdout = responses[call_count] + "\n"
            mp.stderr = ""
            call_count += 1
            return mp

        mock_run.side_effect = side_effect

        cmd_path.backup_path()  # Oldest
        cmd_path.backup_path()  # Middle
        cmd_path.backup_path()  # Newest

        mock_run.reset_mock()
        mock_run.side_effect = None
        # Set a fresh return_value for the auto-backup + set_path calls
        fresh_process = MagicMock()
        fresh_process.returncode = 0
        fresh_process.stdout = "C:\\Dummy\n"
        fresh_process.stderr = ""
        mock_run.return_value = fresh_process

        # Restore the middle one (index 1 = second newest in sorted order)
        cmd_path.restore_at_index(1)

        last_call = mock_run.call_args
        command_str = " ".join(last_call[0][0])
        assert "C:\\Middle" in command_str

    @patch("subprocess.run")
    def test_restore_at_index_raises_on_bad_index(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "C:\\Test\n"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.backup_path()

        with pytest.raises(IndexError, match="out of range"):
            cmd_path.restore_at_index(99)

        with pytest.raises(IndexError, match="out of range"):
            cmd_path.restore_at_index(-1)

    @patch("subprocess.run")
    def test_auto_backup_before_set_path(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "C:\\BeforeChange\n"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.set_path("C:\\NewPath")

        files = list(tmp_path.glob("path_backup_*.json"))
        assert len(files) >= 1
        import json

        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["path"] == "C:\\BeforeChange"

    @patch("subprocess.run")
    def test_auto_backup_before_clear_path(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "C:\\ToBeCleared\n"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.clear_path(confirm=True)

        files = list(tmp_path.glob("path_backup_*.json"))
        assert len(files) >= 1
        import json

        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["path"] == "C:\\ToBeCleared"


# ---------------------------------------------------------------------------
# End-to-end integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    """End-to-end flows that combine multiple cmd_path operations."""

    @patch("subprocess.run")
    def test_backup_modify_restore_cycle(
        self, mock_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Full cycle: backup PATH → modify → restore → original is back."""
        monkeypatch.chdir(tmp_path)

        # Each call to get_path will return the latest "current" path
        call_count: int = 0
        responses: list[str] = [
            "C:\\OriginalPath;C:\\SecondPath",  # backup_path -> get_path
            "C:\\OriginalPath;C:\\SecondPath",  # set_path -> backup_path -> get_path
            "",  # clear_path -> backup_path -> get_path
            "",  # clear_path -> set_path
            "C:\\OriginalPath;C:\\SecondPath",  # restore_path -> set_path -> backup_path -> get_path
            "C:\\OriginalPath;C:\\SecondPath",  # restore_path -> set_path
        ]

        def mock_run_side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            mp = MagicMock()
            mp.returncode = 0
            mp.stdout = responses[call_count] + "\n"
            mp.stderr = ""
            call_count += 1
            return mp

        mock_run.side_effect = mock_run_side_effect

        # Step 1: Ensure backup exists (auto-backup in set_path)
        cmd_path.set_path("C:\\ModifiedPath")

        # Step 2: Restore
        cmd_path.restore_path()

        # Step 3: Verify the last set_path call restored the original
        # The last PowerShell command should contain the original path
        all_calls = [c[0][0] for c in mock_run.call_args_list]
        last_command = " ".join(all_calls[-1])
        assert "OriginalPath" in last_command, (
            f"Expected original path in restore: {last_command}"
        )

    @patch("subprocess.run")
    def test_add_path_then_restore(
        self, mock_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Add a path, then restore to revert the change."""
        monkeypatch.chdir(tmp_path)

        call_count: int = 0
        responses: list[str] = [
            "C:\\Original",  # add_to_path -> get_path
            "C:\\Original",  # add_to_path -> backup_path -> get_path (auto-backup in set_path)
            "",  # set_path Powershell command
            "C:\\Original",  # restore_path -> set_path -> backup_path -> get_path
            "C:\\Original",  # restore_path -> set_path Powershell
        ]

        def mock_run_side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            mp = MagicMock()
            mp.returncode = 0
            mp.stdout = responses[call_count] + "\n"
            mp.stderr = ""
            call_count += 1
            return mp

        mock_run.side_effect = mock_run_side_effect

        # Add a path (auto-backup preserves original)
        cmd_path.add_to_path("C:\\AddedPath")

        # Restore
        cmd_path.restore_path()

        # Verify the last call restored original
        all_calls = [c[0][0] for c in mock_run.call_args_list]
        last_command = " ".join(all_calls[-1])
        assert "C:\\Original" in last_command
        assert "C:\\AddedPath" not in last_command


# ---------------------------------------------------------------------------
# Unix / macOS code paths (``_IS_WINDOWS = False``)
# ---------------------------------------------------------------------------


class UnixMixin:
    """Mixin that sets up safe Unix/macOS code paths for testing.

    - Patches ``_IS_WINDOWS`` to ``False``
    - Redirects ``Path.home()`` to ``tmp_path`` so ``_update_shell_config``
      **never** touches the real ``~/.zshrc`` / shell config file
    """

    @pytest.fixture(autouse=True)
    def _patch_unix(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(cmd_path, "_IS_WINDOWS", False)
        # CRITICAL: prevent writes to the user's actual ~/.zshrc
        monkeypatch.setattr(Path, "home", lambda: tmp_path)


@pytest.mark.skipif(
    not hasattr(os, "geteuid"),
    reason="os.geteuid() not available on Windows",
)
class TestCheckAdminUnix(UnixMixin):
    """check_admin when running on Unix / macOS."""

    @patch("os.geteuid", return_value=0)
    def test_returns_true_when_root(self, mock_geteuid: MagicMock) -> None:
        assert cmd_path.check_admin() is True

    @patch("os.geteuid", return_value=1000)
    def test_returns_false_when_not_root(self, mock_geteuid: MagicMock) -> None:
        assert cmd_path.check_admin() is False

    @patch("os.geteuid", side_effect=OSError)
    def test_handles_os_error(self, mock_geteuid: MagicMock) -> None:
        assert cmd_path.check_admin() is False


class TestGetPathUnix(UnixMixin):
    """get_path when running on Unix / macOS."""

    def test_returns_os_environ_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PATH", "/usr/bin:/bin:/usr/local/bin")
        result = cmd_path.get_path()
        assert result == "/usr/bin:/bin:/usr/local/bin"

    def test_returns_empty_string_when_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("PATH", raising=False)
        result = cmd_path.get_path()
        assert result == ""


class TestSetPathUnix(UnixMixin):
    """set_path when running on Unix / macOS."""

    def test_updates_os_environ(self) -> None:
        cmd_path.set_path("/usr/local/bin:/usr/bin")
        assert os.environ["PATH"] == "/usr/local/bin:/usr/bin"

    def test_updates_shell_config(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Verify _update_shell_config is called (creates/updates rc file)."""
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        monkeypatch.setenv("SHELL", "/bin/zsh")

        cmd_path.set_path("/opt/myapp/bin:/usr/bin")

        rc_file = fake_home / ".zshrc"
        assert rc_file.exists()
        content = rc_file.read_text(encoding="utf-8")
        assert "export PATH=" in content
        assert "/opt/myapp/bin:/usr/bin" in content

    def test_replaces_existing_path_in_shell_config(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Calling set_path twice should not duplicate export lines."""
        fake_home = tmp_path / "fake_home2"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        monkeypatch.setenv("SHELL", "/bin/zsh")

        cmd_path.set_path("/first/path")
        cmd_path.set_path("/second/path")

        rc_file = fake_home / ".zshrc"
        content = rc_file.read_text(encoding="utf-8")
        assert content.count("export PATH=") == 1
        assert "/second/path" in content
        assert "/first/path" not in content


class TestClearPathUnix(UnixMixin):
    """clear_path when running on Unix / macOS."""

    def test_clears_os_environ(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PATH", "/usr/bin:/bin")
        cmd_path.clear_path(confirm=True)
        assert os.environ["PATH"] == ""


class TestAddToPathUnix(UnixMixin):
    """add_to_path when running on Unix / macOS."""

    @patch("cmd_path.get_path")
    @patch("cmd_path.set_path")
    def test_adds_new_path_with_colon_separator(
        self,
        mock_set_path: MagicMock,
        mock_get_path: MagicMock,
    ) -> None:
        mock_get_path.return_value = "/usr/bin:/usr/local/bin"
        cmd_path.add_to_path("/opt/myapp/bin")
        mock_set_path.assert_called_once_with(
            "/usr/bin:/usr/local/bin:/opt/myapp/bin:", "Machine"
        )

    @patch("cmd_path.get_path")
    @patch("cmd_path.set_path")
    def test_handles_multiple_new_paths_with_colon(
        self,
        mock_set_path: MagicMock,
        mock_get_path: MagicMock,
    ) -> None:
        mock_get_path.return_value = "/usr/bin"
        cmd_path.add_to_path("/opt/app1:/opt/app2")
        mock_set_path.assert_called_once_with(
            "/usr/bin:/opt/app1:/opt/app2:", "Machine"
        )

    def test_empty_path_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot add an empty path"):
            cmd_path.add_to_path("")


# ---------------------------------------------------------------------------
# Protection: set_path rejects empty / separator-only (Unix)
# ---------------------------------------------------------------------------


class TestSetPathProtectionUnix(UnixMixin):
    """``set_path`` safety guards on Unix / macOS (uses ``:`` separator)."""

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError, match="empty value"):
            cmd_path.set_path("")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="empty value"):
            cmd_path.set_path("   \t\n")

    def test_rejects_only_separators_unix(self) -> None:
        with pytest.raises(ValueError, match="separators"):
            cmd_path.set_path(":::")

    def test_rejects_mixed_separators_and_whitespace_unix(self) -> None:
        with pytest.raises(ValueError, match="separators"):
            cmd_path.set_path(" : : \n")

    def test_accepts_valid_path_unix(self) -> None:
        # Should not raise
        cmd_path.set_path("/usr/bin:/usr/local/bin")
        assert os.environ["PATH"] == "/usr/bin:/usr/local/bin"


# ---------------------------------------------------------------------------
# Protection: clear_path requires explicit confirm (Unix)
# ---------------------------------------------------------------------------


class TestClearPathProtectionUnix(UnixMixin):
    """``clear_path`` safety guards on Unix / macOS."""

    def test_refuses_without_confirm(self) -> None:
        with pytest.raises(ValueError, match="confirm"):
            cmd_path.clear_path()

    def test_refuses_with_explicit_false(self) -> None:
        with pytest.raises(ValueError, match="confirm"):
            cmd_path.clear_path(confirm=False)

    def test_accepts_with_confirm_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PATH", "/usr/bin")
        cmd_path.clear_path(confirm=True)
        assert os.environ["PATH"] == ""


# ---------------------------------------------------------------------------
# Protection: add_to_path must never accidentally wipe PATH (Unix)
# ---------------------------------------------------------------------------


class TestAddToPathProtectionUnix(UnixMixin):
    """``add_to_path`` safety guards on Unix / macOS."""

    @patch("cmd_path.get_path")
    def test_cannot_add_all_separators_unix(self, mock_get_path: MagicMock) -> None:
        mock_get_path.return_value = "/usr/bin"
        with pytest.raises(ValueError, match="No valid paths"):
            cmd_path.add_to_path(":::")

    @patch("cmd_path.get_path")
    def test_cannot_add_all_whitespace(self, mock_get_path: MagicMock) -> None:
        mock_get_path.return_value = "/usr/bin"
        with pytest.raises(ValueError, match="Cannot add an empty path"):
            cmd_path.add_to_path("   \t\n")

    @patch("cmd_path.get_path")
    def test_raises_on_empty_path_unix(self, mock_get_path: MagicMock) -> None:
        mock_get_path.return_value = "/usr/bin"
        with pytest.raises(ValueError, match="Cannot add an empty path"):
            cmd_path.add_to_path("")

    @patch("cmd_path.get_path")
    def test_cannot_wipe_existing_by_adding_nothing_unix(
        self, mock_get_path: MagicMock
    ) -> None:
        mock_get_path.return_value = ""
        with pytest.raises(ValueError, match="Cannot add an empty path"):
            cmd_path.add_to_path("")

    @patch("cmd_path.get_path")
    @patch("cmd_path.set_path")
    def test_never_calls_set_path_with_separator_only_unix(
        self,
        mock_set_path: MagicMock,
        mock_get_path: MagicMock,
    ) -> None:
        """If current PATH is empty but valid entries are added."""
        mock_get_path.return_value = ""
        cmd_path.add_to_path("/opt/newapp")
        mock_set_path.assert_called_once()
        args, _ = mock_set_path.call_args
        assert args[0].strip(":"), f"PATH should not be empty: {args[0]!r}"


# ---------------------------------------------------------------------------
# Backup / Restore (Unix)
# ---------------------------------------------------------------------------


class TestBackupPathUnix(UnixMixin):
    """backup_path and restore_path on Unix / macOS."""

    def test_backup_saves_current_path_to_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PATH", "/usr/bin:/bin:/usr/local/bin")

        result = cmd_path.backup_path()

        assert result == "/usr/bin:/bin:/usr/local/bin"
        files = list(tmp_path.glob("path_backup_*.json"))
        assert len(files) == 1, f"Expected 1 backup file, got {len(files)}"

        import json

        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["path"] == "/usr/bin:/bin:/usr/local/bin"
        assert "timestamp" in data

    def test_backup_returns_current_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PATH", "/opt/myapp/bin")
        result = cmd_path.backup_path()
        assert result == "/opt/myapp/bin"

    def test_restore_raises_when_no_backup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with pytest.raises(FileNotFoundError, match="No PATH backup"):
            cmd_path.restore_path()

    def test_restore_sets_path_from_backup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PATH", "/usr/bin:/original/path")

        cmd_path.backup_path()

        # Modify PATH
        monkeypatch.setenv("PATH", "/tmp/modified")

        # Restore should bring back the saved value
        cmd_path.restore_path()

        assert os.environ["PATH"] == "/usr/bin:/original/path"

    def test_auto_backup_before_set_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PATH", "/usr/bin:/before/change")

        cmd_path.set_path("/new/path")

        files = list(tmp_path.glob("path_backup_*.json"))
        assert len(files) >= 1
        import json

        data = json.loads(files[-1].read_text(encoding="utf-8"))
        assert data["path"] == "/usr/bin:/before/change"

    def test_auto_backup_before_clear_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PATH", "/usr/bin:/tobe/cleared")

        cmd_path.clear_path(confirm=True)

        files = list(tmp_path.glob("path_backup_*.json"))
        assert len(files) >= 1
        import json

        data = json.loads(files[-1].read_text(encoding="utf-8"))
        assert data["path"] == "/usr/bin:/tobe/cleared"


# ---------------------------------------------------------------------------
# list_backups / restore_at_index / suggest_restore
# ---------------------------------------------------------------------------


class TestListBackups:
    """Tests for ``list_backups()`` on Windows."""

    @patch("subprocess.run")
    def test_list_backups_empty_when_none_exist(self, mock_run: MagicMock) -> None:
        result = cmd_path.list_backups()
        assert result == []

    @patch("subprocess.run")
    def test_list_backups_returns_metadata(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "C:\\Windows;C:\\Program Files\n"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.backup_path()
        backups = cmd_path.list_backups()
        assert len(backups) == 1
        assert backups[0]["path"] == "C:\\Windows;C:\\Program Files"
        assert backups[0]["scope"] == "Machine"
        assert "timestamp" in backups[0]
        assert backups[0]["index"] == "0"

    @patch("subprocess.run")
    def test_multiple_backups_ordered_newest_first(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        call_count: int = 0
        responses: list[str] = ["C:\\Old", "C:\\Middle", "C:\\Newest"]

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            mp = MagicMock()
            mp.returncode = 0
            mp.stdout = responses[call_count] + "\n"
            mp.stderr = ""
            call_count += 1
            return mp

        mock_run.side_effect = side_effect

        cmd_path.backup_path()  # Old
        cmd_path.backup_path()  # Middle
        cmd_path.backup_path()  # Newest

        backups = cmd_path.list_backups()
        # Since filenames sort lexicographically by timestamp (newer = later),
        # the reverse sort puts Newest first
        assert len(backups) == 3
        # Verify ordering by index
        assert int(backups[0]["index"]) == 0  # Newest
        assert int(backups[1]["index"]) == 1
        assert int(backups[2]["index"]) == 2  # Oldest

    @patch("subprocess.run")
    def test_restore_at_index_picks_correct_backup(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        call_count: int = 0
        responses: list[str] = ["C:\\A", "C:\\B", "C:\\C"]

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            mp = MagicMock()
            mp.returncode = 0
            mp.stdout = responses[call_count] + "\n"
            mp.stderr = ""
            call_count += 1
            return mp

        mock_run.side_effect = side_effect

        cmd_path.backup_path()
        cmd_path.backup_path()
        cmd_path.backup_path()

        mock_run.reset_mock()
        mock_run.side_effect = None
        # Set a fresh return_value for the auto-backup + set_path calls
        fresh_process = MagicMock()
        fresh_process.returncode = 0
        fresh_process.stdout = "C:\\Dummy\n"
        fresh_process.stderr = ""
        mock_run.return_value = fresh_process

        cmd_path.restore_at_index(1)

        # Should restore the 2nd newest backup
        # After sorting by filename (newest first), index 1 is the middle one
        # which was "C:\\B"
        last_call = mock_run.call_args
        command_str = " ".join(last_call[0][0])
        assert "C:\\B" in command_str

    @patch("subprocess.run")
    def test_suggest_restore_none_when_few_backups(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """suggest_restore returns None with fewer than 3 backups."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "C:\\Windows\n"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.backup_path()
        cmd_path.backup_path()
        assert cmd_path.suggest_restore() is None

    @patch("subprocess.run")
    def test_suggest_restore_returns_info_when_3_or_more(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """suggest_restore returns dict with count/newest/oldest when >= 3."""
        call_count: int = 0

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            mp = MagicMock()
            mp.returncode = 0
            mp.stdout = f"C:\\Path{call_count}\n"
            mp.stderr = ""
            call_count += 1
            return mp

        mock_run.side_effect = side_effect

        cmd_path.backup_path()
        cmd_path.backup_path()
        cmd_path.backup_path()

        result = cmd_path.suggest_restore()
        assert result is not None
        assert result["count"] == 3
        assert "time" in result["newest"] or "T" in result["newest"]
        assert "time" in result["oldest"] or "T" in result["oldest"]


# ---------------------------------------------------------------------------
# Dry-run mode tests (Windows)
# ---------------------------------------------------------------------------


class TestDryRun:
    """dry_run parameter prevents any real modifications."""

    @patch("subprocess.run")
    def test_set_path_dry_run_does_not_modify(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "C:\\OldPath\n"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.set_path("C:\\NewPath", dry_run=True)
        # subprocess.run is NOT called for the actual set_path in dry-run mode.
        # Only the backup_path->get_path call happens if any, but dry_run
        # short-circuits before that.
        assert mock_run.call_count == 0, (
            f"Expected 0 subprocess calls in dry-run, got {mock_run.call_count}"
        )

    @patch("subprocess.run")
    def test_clear_path_dry_run_does_not_modify(self, mock_run: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "C:\\OldPath\n"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        cmd_path.clear_path(confirm=True, dry_run=True)
        # get_path() is called for the informational message in dry-run mode
        assert mock_run.call_count == 1, (
            f"Expected 1 subprocess call (get_path) in dry-run, "
            f"got {mock_run.call_count}"
        )

    def test_backup_path_dry_run_does_not_write_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        # First back up for real to create a file
        with patch("subprocess.run") as mock_run:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = "C:\\RealPath\n"
            mock_process.stderr = ""
            mock_run.return_value = mock_process
            cmd_path.backup_path()

        files_after_real = list(tmp_path.glob("path_backup_*.json"))
        assert len(files_after_real) == 1
        real_mtime = files_after_real[0].stat().st_mtime_ns

        # Now call backup_path again with dry_run=True
        with patch("subprocess.run") as mock_run:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = "C:\\NewPath\n"
            mock_process.stderr = ""
            mock_run.return_value = mock_process

            cmd_path.backup_path(dry_run=True)

        # The backup file should NOT have been overwritten or added
        files_after_dry = list(tmp_path.glob("path_backup_*.json"))
        assert len(files_after_dry) == 1, "dry-run should not create new backup files"
        assert files_after_dry[0].stat().st_mtime_ns == real_mtime, (
            "dry_run backup should not modify the backup file"
        )

    @patch("subprocess.run")
    def test_restore_path_dry_run_does_not_modify(
        self, mock_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "C:\\Original\n"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        # Create a real backup first
        cmd_path.backup_path()

        # Reset call count
        mock_run.reset_mock()

        # Now restore with dry_run=True
        cmd_path.restore_path(dry_run=True)

        # No extra subprocess calls for the restore itself
        # (get_path might be called for the warning message in clear_path,
        #  but restore_path doesn't call clear_path)
        assert mock_run.call_count == 0, (
            f"Expected 0 subprocess calls in dry-run restore, got {mock_run.call_count}"
        )


# ---------------------------------------------------------------------------
# Dry-run mode tests (Unix)
# ---------------------------------------------------------------------------


class TestDryRunUnix(UnixMixin):
    """dry_run parameter on Unix / macOS."""

    def test_set_path_dry_run_does_not_modify_os_environ(self) -> None:
        original = os.environ.get("PATH", "")
        cmd_path.set_path("/tmp/evil/bin", dry_run=True)
        assert os.environ.get("PATH", "") == original, (
            "dry_run set_path should not modify os.environ"
        )

    def test_clear_path_dry_run_does_not_modify_os_environ(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PATH", "/usr/bin:/bin")
        cmd_path.clear_path(confirm=True, dry_run=True)
        assert os.environ["PATH"] == "/usr/bin:/bin", (
            "dry_run clear_path should not modify os.environ"
        )

    def test_backup_path_dry_run_does_not_write_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PATH", "/usr/bin:/first/path")

        # Real backup
        cmd_path.backup_path()
        files_after_real = list(tmp_path.glob("path_backup_*.json"))
        assert len(files_after_real) == 1
        real_mtime = files_after_real[0].stat().st_mtime_ns

        # Dry-run backup
        monkeypatch.setenv("PATH", "/usr/bin:/second/path")
        cmd_path.backup_path(dry_run=True)

        # Should NOT have created a new file or modified the existing one
        files_after_dry = list(tmp_path.glob("path_backup_*.json"))
        assert len(files_after_dry) == 1, "dry-run should not create new backup files"
        assert files_after_dry[0].stat().st_mtime_ns == real_mtime

    def test_restore_path_dry_run_does_not_modify_os_environ(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PATH", "/usr/bin:/original")

        # Create backup
        cmd_path.backup_path()

        # Now os.environ has the backup value; modify to simulate drift
        monkeypatch.setenv("PATH", "/usr/bin:/modified/after/backup")

        # Restore with dry-run should NOT change os.environ
        cmd_path.restore_path(dry_run=True)
        assert os.environ["PATH"] == "/usr/bin:/modified/after/backup"


# ---------------------------------------------------------------------------
# End-to-end integration tests (Unix)
# ---------------------------------------------------------------------------


class TestIntegrationUnix(UnixMixin):
    """End-to-end flows on Unix / macOS."""

    def test_backup_modify_restore_cycle(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Full cycle: backup PATH -> modify -> restore -> original is back."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PATH", "/usr/bin:/original/path:/bin")

        # Modify PATH
        cmd_path.set_path("/tmp/modified")
        assert os.environ["PATH"] == "/tmp/modified"

        # Restore
        cmd_path.restore_path()
        assert os.environ["PATH"] == "/usr/bin:/original/path:/bin"

    def test_add_path_then_restore(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Add a path, then restore to revert the change."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PATH", "/usr/bin:/bin")

        # add_to_path calls set_path which auto-backups
        cmd_path.add_to_path("/opt/newapp")

        # Verify new path was added
        assert "/opt/newapp" in os.environ["PATH"]

        # Restore to revert
        cmd_path.restore_path()

        # Verify original is back and new path is removed
        assert os.environ["PATH"] == "/usr/bin:/bin"
        assert "/opt/newapp" not in os.environ["PATH"]
