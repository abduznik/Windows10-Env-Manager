"""Cross-platform PATH environment variable management.

Windows
    Uses PowerShell to read/write ``Machine`` or ``User`` level PATH.
    Administrator privileges are required for ``Machine`` scope.

Unix / macOS
    Reads from ``os.environ`` and persists changes to the user's shell
    configuration file (``~/.zshrc``, ``~/.bashrc``, or ``~/.profile``).
    Changes take effect in new terminal sessions; the current session
    is updated via ``os.environ`` immediately.
"""

import os
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------

_IS_WINDOWS = sys.platform == "win32"


def _get_sep() -> str:
    """Return the PATH entry separator for the current platform.

    ``;`` on Windows, ``:`` on Unix / macOS.
    """
    return ";" if _IS_WINDOWS else ":"


def _get_shell_rc_path() -> Path:
    """Return the path to the user's shell configuration file."""
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    if "zsh" in shell:
        return home / ".zshrc"
    if "bash" in shell:
        return home / ".bashrc"
    return home / ".profile"


def _update_shell_config(new_path: str) -> None:
    """Persist *new_path* to the user's shell rc file.

    Replaces any existing ``export PATH=…`` line so the file doesn't
    accumulate stale entries.
    """
    rc = _get_shell_rc_path()
    export_line = f"export PATH=\"{new_path}\"\n"

    if rc.exists():
        lines = rc.read_text(encoding="utf-8").splitlines(keepends=True)
        filtered = [line for line in lines if not line.startswith("export PATH=")]
        if filtered and not filtered[-1].endswith("\n"):
            filtered[-1] += "\n"
        filtered.append(export_line)
        rc.write_text("".join(filtered), encoding="utf-8")
    else:
        rc.write_text(export_line, encoding="utf-8")


# ---------------------------------------------------------------------------
# check_admin
# ---------------------------------------------------------------------------


def check_admin() -> bool:
    """Check whether the current process has administrator / root privileges.

    Returns:
        ``True`` if running as admin (Windows) or root (Unix).
    """
    try:
        if _IS_WINDOWS:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except (AttributeError, OSError):
        return False


# ---------------------------------------------------------------------------
# get_path
# ---------------------------------------------------------------------------


def get_path(scope: str = "Machine") -> str:
    """Return the current ``PATH`` as a string.

    Args:
        scope: ``"Machine"`` or ``"User"`` (Windows only; ignored on Unix).

    Raises:
        ValueError: If the underlying command fails.
    """
    if _IS_WINDOWS:
        command: list[str] = [
            "powershell", "-Command",
            f"[System.Environment]::GetEnvironmentVariable('Path', '{scope}')",
        ]
        result: subprocess.CompletedProcess = subprocess.run(
            command, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise ValueError(
                f"Failed to retrieve PATH variable. Error: {result.stderr.strip()}"
            )
        return result.stdout.strip()
    return os.environ.get("PATH", "")


# ---------------------------------------------------------------------------
# set_path
# ---------------------------------------------------------------------------


def set_path(new_path: str, scope: str = "Machine") -> None:
    """Set ``PATH`` to *new_path*.

    On Windows the change is written to the system registry via PowerShell.
    On Unix / macOS the current process's ``os.environ`` is updated and the
    value is persisted to the user's shell rc file.

    Args:
        new_path: The full ``PATH`` string to set.
        scope: ``"Machine"`` or ``"User"`` (Windows only; ignored on Unix).

    Raises:
        ValueError: If the underlying command fails.
    """
    if _IS_WINDOWS:
        escaped = new_path.replace('"', '\\"')
        command: list[str] = [
            "powershell", "-Command",
            f"[System.Environment]::SetEnvironmentVariable('Path', \"{escaped}\", '{scope}')",
        ]
        result: subprocess.CompletedProcess = subprocess.run(
            command, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise ValueError(
                f"Failed to set PATH variable. Error: {result.stderr.strip()}"
            )
    else:
        os.environ["PATH"] = new_path
        _update_shell_config(new_path)


# ---------------------------------------------------------------------------
# save_path_to_file
# ---------------------------------------------------------------------------


def save_path_to_file(
    path_string: str, file_name: str = "path_list.txt"
) -> None:
    """Save *path_string* to a text file (used by the GUI)."""
    Path(file_name).write_text(path_string, encoding="utf-8")
    print(f"PATH variable saved to '{file_name}'.")


# ---------------------------------------------------------------------------
# clear_path
# ---------------------------------------------------------------------------


def clear_path(scope: str = "Machine") -> None:
    """Set ``PATH`` to an empty string.

    .. warning::
        This removes **all** paths from the environment variable.

    Args:
        scope: ``"Machine"`` or ``"User"`` (Windows only; ignored on Unix).

    Raises:
        ValueError: If the underlying command fails.
    """
    if _IS_WINDOWS:
        command: list[str] = [
            "powershell", "-Command",
            f"[System.Environment]::SetEnvironmentVariable('Path', '', '{scope}')",
        ]
        result: subprocess.CompletedProcess = subprocess.run(
            command, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise ValueError(
                f"Failed to clear PATH variable. Error: {result.stderr.strip()}"
            )
    else:
        os.environ["PATH"] = ""
        _update_shell_config("")


# ---------------------------------------------------------------------------
# add_to_path
# ---------------------------------------------------------------------------


def add_to_path(new_path: str, system_wide: bool = True) -> None:
    """Add one or more directories to ``PATH``.

    Duplicates are detected and skipped silently.

    Args:
        new_path: A directory path, or a ``os.pathsep``-separated string of
                  paths (``;`` on Windows, ``:`` on Unix).
        system_wide:
            ``True`` → ``"Machine"`` scope (Windows) or global config (Unix).
            ``False`` → ``"User"`` scope.

    Raises:
        ValueError: If the input is empty or no valid paths remain after
                    filtering.
    """
    if not new_path or not new_path.strip():
        raise ValueError("Cannot add an empty path to PATH.")

    sep = _get_sep()
    scope: str = "Machine" if system_wide else "User"
    current_path: str = get_path(scope)

    existing_entries: list[str] = [
        p.strip() for p in current_path.split(sep) if p.strip()
    ]
    new_entries: list[str] = [
        p.strip() for p in new_path.split(sep) if p.strip()
    ]

    if not new_entries:
        raise ValueError("No valid paths to add.")

    already_present: list[str] = [
        e for e in new_entries if e in existing_entries
    ]
    entries_to_add: list[str] = [
        e for e in new_entries if e not in existing_entries
    ]

    if not entries_to_add:
        print(
            f"All path(s) are already in the PATH variable: "
            f"{', '.join(already_present)}"
        )
        return

    updated_path: str = sep.join(existing_entries + entries_to_add) + sep
    set_path(updated_path, scope)

    print(
        f"The path(s) '{'; '.join(entries_to_add)}' have been added to the "
        f"{'system' if system_wide else 'user'} PATH variable."
    )
    if already_present:
        print(
            f"The following path(s) were already present: "
            f"{', '.join(already_present)}"
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    if not check_admin():
        msg = (
            "This script must be run as an administrator."
            if _IS_WINDOWS
            else "This script must be run as root."
        )
        print(f"Error: {msg}")
        sys.exit(1)

    full_path_string: str = get_path()
    save_path_to_file(full_path_string)

    if len(sys.argv) > 1:
        custom_path: str = sys.argv[1]
        add_to_path(custom_path, system_wide=True)
