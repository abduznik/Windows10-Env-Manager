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
        mock_run.return_value = mock_process

        cmd_path.set_path("C:\\MyApp")
        mock_run.assert_called_once()

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
        mock_run.return_value = mock_process

        path_with_quotes = 'C:\\My"App'
        cmd_path.set_path(path_with_quotes)

        # Verify the escaped version is in the command
        command_str = " ".join(mock_run.call_args[0][0])
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
        mock_run.return_value = mock_process

        cmd_path.clear_path(confirm=True)
        mock_run.assert_called_once()

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
        mock_set_path.assert_called_once_with(
            "C:\\Windows;C:\\MyApp;", "User"
        )

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
        mock_run.return_value = mock_process

        # Should not raise
        cmd_path.set_path("C:\\Windows")
        mock_run.assert_called_once()


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
        mock_run.return_value = mock_process

        cmd_path.clear_path(confirm=True)
        mock_run.assert_called_once()


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
    def test_cannot_wipe_existing_by_adding_nothing(self, mock_get_path: MagicMock) -> None:
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
    def test_writes_to_default_filename(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify default file name is path_list.txt."""
        defaults = tmp_path / "path_list.txt"
        monkeypatch.chdir(tmp_path)
        assert not defaults.exists()

        cmd_path.save_path_to_file("C:\\Test")
        assert defaults.exists()
        assert defaults.read_text(encoding="utf-8") == "C:\\Test"


# ---------------------------------------------------------------------------
# Unix / macOS code paths (``_IS_WINDOWS = False``)
# ---------------------------------------------------------------------------


class UnixMixin:
    """Mixin that patches ``_IS_WINDOWS`` to ``False`` for Unix code paths."""

    @pytest.fixture(autouse=True)
    def _patch_unix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(cmd_path, "_IS_WINDOWS", False)


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

    def test_returns_empty_string_when_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PATH", raising=False)
        result = cmd_path.get_path()
        assert result == ""


class TestSetPathUnix(UnixMixin):
    """set_path when running on Unix / macOS."""

    def test_updates_os_environ(self) -> None:
        cmd_path.set_path("/usr/local/bin:/usr/bin")
        assert os.environ["PATH"] == "/usr/local/bin:/usr/bin"

    def test_updates_shell_config(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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

    def test_replaces_existing_path_in_shell_config(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
    def test_cannot_wipe_existing_by_adding_nothing_unix(self, mock_get_path: MagicMock) -> None:
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