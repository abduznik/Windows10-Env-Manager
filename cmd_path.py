"""Cross-platform PATH environment variable management.

Windows
    Uses PowerShell to read/write ``Machine`` or ``User`` level PATH.
    Administrator privileges are required for ``Machine`` scope.

Unix / macOS
    Reads from ``os.environ`` and persists changes to the user's shell
    configuration file (``~/.zshrc``, ``~/.bashrc``, or ``~/.profile``).
    Changes take effect in new terminal sessions; the current session
    is updated via ``os.environ`` immediately.

Backup / Restore
    Every modification (``set_path``, ``clear_path``) automatically backs
    up the current PATH first.  Use ``restore_path()`` to roll back.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


_BACKUP_PREFIX = "path_backup"
_BACKUP_SUFFIX = ".json"


def _appdata_dir() -> Path:
    """Lazy-import of utils.get_appdata_dir to avoid circular imports."""
    from utils import get_appdata_dir as _get_appdata_dir

    return _get_appdata_dir()


# ---------------------------------------------------------------------------
# Backup helpers (versioned timestamped files)
# ---------------------------------------------------------------------------


def _backup_dir() -> Path:
    """Return the directory where versioned backup files are stored."""
    return _appdata_dir()


def _backup_glob() -> str:
    """Glob pattern for finding all backup files in the backup directory."""
    return f"{_BACKUP_PREFIX}_*{_BACKUP_SUFFIX}"


_timestamp_counter: int = 0


def _backup_timestamp() -> str:
    """Return a filesystem-safe timestamp string with microsecond precision.

    Microseconds ensure unique filenames even when multiple backups happen
    in rapid succession (e.g. during testing or batch operations).
    A monotonic counter disambiguates calls within the same microsecond.
    """
    global _timestamp_counter
    _timestamp_counter += 1
    ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    return f"{ts}_{_timestamp_counter:04d}"


def _parse_backup_timestamp(filename: str) -> str:
    """Extract the timestamp string from a backup filename.

    ``path_backup_20260525T120000_0001.json`` → ``2026-05-25T12:00:00``
    ``path_backup_20260525T120000123456_0001.json`` → ``2026-05-25T12:00:00.123456``
    (ISO-ish format for human display).

    The four-digit counter suffix is stripped before formatting.
    """
    ts_raw = filename.replace(f"{_BACKUP_PREFIX}_", "").replace(_BACKUP_SUFFIX, "")
    # Strip trailing monotonic counter (e.g. "_0001")
    ts_raw = ts_raw.rsplit("_", 1)[0]
    # Convert YYYYMMDDTHHMMSS[ffffff] -> YYYY-MM-DDTHH:MM:SS[.ffffff]
    if len(ts_raw) in (15, 21) and "T" in ts_raw:
        date_part, time_part = ts_raw.split("T")
        if len(date_part) == 8:
            date_part = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        if len(time_part) >= 6:
            time_part = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
            if len(time_part) > 8:  # includes microseconds
                time_part = f"{time_part[:8]}.{time_part[8:]}"
        return f"{date_part}T{time_part}"
    return ts_raw


def _backup_files() -> list[Path]:
    """Return sorted list of versioned backup file paths (newest first)."""
    bdir = _backup_dir()
    files = sorted(bdir.glob(_backup_glob()), reverse=True)
    return files


def list_backups() -> list[dict[str, str]]:
    """Return a list of all available backups, newest first.

    Each entry contains:

    - ``index``: ordinal for use with ``restore_at_index()``
    - ``timestamp``: human-readable ISO timestamp
    - ``path``: the PATH value that was backed up (first 80 chars)
    - ``scope``: ``"Machine"`` or ``"User"``

    Returns:
        List of backup metadata dicts. Empty list if no backups exist.
    """
    result: list[dict[str, str]] = []
    for idx, fp in enumerate(_backup_files()):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            ts_raw = _parse_backup_timestamp(fp.name)
            result.append(
                {
                    "index": str(idx),
                    "timestamp": ts_raw,
                    "path": data.get("path", "")[:80],
                    "scope": data.get("scope", "Machine"),
                    "filename": fp.name,
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return result


def restore_at_index(index: int, *, dry_run: bool = False) -> None:
    """Restore ``PATH`` from the backup at *index* (0 = newest).

    Args:
        index: 0-based index into the sorted backup list (0 = most recent).
        dry_run: If ``True``, print what would be restored without writing.

    Raises:
        IndexError: If *index* is out of range.
        ValueError: If the backup data is malformed.
    """
    files = _backup_files()
    if not files:
        raise FileNotFoundError("No PATH backups found.")
    if index < 0 or index >= len(files):
        raise IndexError(
            f"Backup index {index} out of range. "
            f"There are {len(files)} backups (0-{len(files) - 1})."
        )

    fp = files[index]
    try:
        backup: dict[str, str] = json.loads(fp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Backup file '{fp.name}' is corrupted: {exc}") from exc

    if "path" not in backup:
        raise ValueError(f"Backup file '{fp.name}' is missing the 'path' field.")

    saved_path: str = backup["path"]
    saved_scope: str = backup.get("scope", "Machine")
    saved_ts: str = backup.get("timestamp", "unknown")

    ts_display = _parse_backup_timestamp(fp.name) if saved_ts == "unknown" else saved_ts
    print(f"Restoring PATH from backup #{index} (saved at {ts_display})...")

    if dry_run:
        print(f"[DRY RUN] Would set PATH ({saved_scope}):")
        print(f"[DRY RUN]   {saved_path[:120]}{'...' if len(saved_path) > 120 else ''}")
        print("[DRY RUN] No changes were made.")
        return

    set_path(saved_path, saved_scope)
    print("PATH restored successfully.")


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
    export_line = f'export PATH="{new_path}"\n'

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
# Backup / Restore
# ---------------------------------------------------------------------------


def backup_path(scope: str = "Machine", *, dry_run: bool = False) -> str:
    """Save the current ``PATH`` to a backup file and return its value.

    The backup is stored as JSON with the scope, path value, and a
    timestamp so ``restore_path()`` can restore it later.

    Args:
        scope: ``"Machine"`` or ``"User"`` (Windows only; ignored on Unix).
        dry_run: If ``True``, print what would be saved without writing.

    Returns:
        The current PATH string that was backed up (or would be backed up
        in dry-run mode).
    """
    current: str = get_path(scope)

    ts = _backup_timestamp()
    backup_file = _backup_dir() / f"{_BACKUP_PREFIX}_{ts}{_BACKUP_SUFFIX}"

    if dry_run:
        print(f"[DRY RUN] Would backup current PATH ({scope}):")
        print(f"[DRY RUN]   {current[:120]}{'...' if len(current) > 120 else ''}")
        print(f"[DRY RUN]   → {backup_file}")
        return current

    backup: dict[str, str] = {
        "scope": scope,
        "path": current,
        "timestamp": datetime.now().isoformat(),
    }
    backup_file.write_text(json.dumps(backup, indent=2), encoding="utf-8")
    return current


def restore_path(scope: str = "Machine", *, dry_run: bool = False) -> None:
    """Restore ``PATH`` from the most recent versioned backup.

    This is a convenience wrapper around ``restore_at_index(0)`` (the
    newest backup).

    Args:
        scope: Ignored; the scope from the backup file is used instead.
        dry_run: If ``True``, print what would be restored without writing.

    Raises:
        FileNotFoundError: If no backup files exist.
        ValueError: If the backup data is malformed.
    """
    restore_at_index(0, dry_run=dry_run)


def suggest_restore() -> dict | None:
    """Check whether the user might want to restore a previous PATH.

    Looks at the number of available backups.  If 3 or more exist, it
    returns info about the oldest and newest so the GUI can offer to
    restore.

    Returns:
        A dict with ``count``, ``newest``, ``oldest`` keys, or ``None``
        if fewer than 3 backups exist.
    """
    backups = list_backups()
    if len(backups) < 3:
        return None
    return {
        "count": len(backups),
        "newest": backups[0]["timestamp"],
        "oldest": backups[-1]["timestamp"],
    }


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
            "powershell",
            "-Command",
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


def _validate_path_not_empty(new_path: str, sep: str) -> None:
    """Raise ``ValueError`` if *new_path* would effectively delete PATH.

    Guards against accidentally wiping the environment variable by
    passing an empty string, whitespace, or a string that contains only
    PATH separators (``;`` / ``:``).
    """
    stripped = new_path.strip()
    if not stripped:
        raise ValueError(
            "Refusing to set PATH to an empty value. "
            "Use clear_path(confirm=True) if you intend to clear it."
        )
    # Check if the string is nothing but separators (e.g. ";;;" or "::")
    only_seps = all(ch in (sep + " \t\n\r") for ch in stripped)
    if only_seps:
        raise ValueError(
            "Refusing to set PATH to a value that contains only PATH "
            f"separators ('{sep}'). "
            "Use clear_path(confirm=True) if you intend to clear it."
        )


def set_path(new_path: str, scope: str = "Machine", *, dry_run: bool = False) -> None:
    """Set ``PATH`` to *new_path*.

    On Windows the change is written to the system registry via PowerShell.
    On Unix / macOS the current process's ``os.environ`` is updated and the
    value is persisted to the user's shell rc file.

    Args:
        new_path: The full ``PATH`` string to set.
        scope: ``"Machine"`` or ``"User"`` (Windows only; ignored on Unix).
        dry_run: If ``True``, print what would be done without any changes.

    Raises:
        ValueError:
            If *new_path* is empty, whitespace-only, or contains only PATH
            separators (would effectively delete the environment variable).
        ValueError: If the underlying command fails.
    """
    sep = _get_sep()
    _validate_path_not_empty(new_path, sep)

    if dry_run:
        print(f"[DRY RUN] Would set PATH ({scope}):")
        print(f"[DRY RUN]   {new_path[:120]}{'...' if len(new_path) > 120 else ''}")
        print("[DRY RUN] Would auto-backup current PATH first")
        print("[DRY RUN] No changes were made.")
        return

    # Auto-backup before modifying (non-fatal)
    try:
        backup_path(scope)
    except Exception as backup_err:
        print(f"Warning: failed to backup PATH: {backup_err}")

    if _IS_WINDOWS:
        escaped = new_path.replace('"', '\\"')
        command: list[str] = [
            "powershell",
            "-Command",
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


def save_path_to_file(path_string: str, file_name: str = "path_list.txt") -> None:
    """Save *path_string* to a text file (used by the GUI)."""
    Path(file_name).write_text(path_string, encoding="utf-8")
    print(f"PATH variable saved to '{file_name}'.")


# ---------------------------------------------------------------------------
# clear_path
# ---------------------------------------------------------------------------


def clear_path(
    scope: str = "Machine", *, confirm: bool = False, dry_run: bool = False
) -> None:
    """Set ``PATH`` to an empty string.

    .. warning::
        This removes **all** paths from the environment variable and can
        break system functionality.  You **must** pass ``confirm=True`` to
        execute this operation.

    Args:
        scope: ``"Machine"`` or ``"User"`` (Windows only; ignored on Unix).
        confirm: Pass ``True`` to acknowledge the destructive nature of
                 this operation.  Raises ``ValueError`` if ``False``.
        dry_run: If ``True``, print what would be cleared without changes.

    Raises:
        ValueError: If *confirm* is not ``True``.
        ValueError: If the underlying command fails.
    """
    if not confirm:
        raise ValueError(
            "Refusing to clear PATH without explicit confirmation. "
            "Pass confirm=True to acknowledge this destructive operation."
        )

    if dry_run:
        current: str = get_path(scope)
        print(f"[DRY RUN] Would clear PATH ({scope}):")
        print(
            f"[DRY RUN]   Current: {current[:120]}{'...' if len(current) > 120 else ''}"
        )
        print("[DRY RUN] Would auto-backup current PATH first")
        print("[DRY RUN] No changes were made.")
        return

    # Auto-backup before clearing (non-fatal)
    try:
        backup_path(scope)
    except Exception as backup_err:
        print(f"Warning: failed to backup PATH: {backup_err}")

    if _IS_WINDOWS:
        command: list[str] = [
            "powershell",
            "-Command",
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


def add_to_path(
    new_path: str, system_wide: bool = True, *, dry_run: bool = False
) -> None:
    """Add one or more directories to ``PATH``.

    Duplicates are detected and skipped silently.

    Args:
        new_path: A directory path, or a ``os.pathsep``-separated string of
                  paths (``;`` on Windows, ``:`` on Unix).
        system_wide:
            ``True`` → ``"Machine"`` scope (Windows) or global config (Unix).
            ``False`` → ``"User"`` scope.
        dry_run: If ``True``, print what would be done without making changes.

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
    new_entries: list[str] = [p.strip() for p in new_path.split(sep) if p.strip()]

    if not new_entries:
        raise ValueError("No valid paths to add.")

    already_present: list[str] = [e for e in new_entries if e in existing_entries]
    entries_to_add: list[str] = [e for e in new_entries if e not in existing_entries]

    if not entries_to_add:
        print(
            f"All path(s) are already in the PATH variable: "
            f"{', '.join(already_present)}"
        )
        return

    updated_path: str = sep.join(existing_entries + entries_to_add) + sep

    if dry_run:
        print(f"[DRY RUN] Would add to PATH ({scope}):")
        for entry in entries_to_add:
            print(f"[DRY RUN]   + {entry}")
        print("[DRY RUN] Resulting PATH:")
        print(
            f"[DRY RUN]   {updated_path[:200]}{'...' if len(updated_path) > 200 else ''}"
        )
        print("[DRY RUN] No changes were made.")
        return

    set_path(updated_path, scope)

    print(
        f"The path(s) '{'; '.join(entries_to_add)}' have been added to the "
        f"{'system' if system_wide else 'user'} PATH variable."
    )
    if already_present:
        print(
            f"The following path(s) were already present: {', '.join(already_present)}"
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    dry_run: bool = "--dry-run" in sys.argv

    if not dry_run and not check_admin():
        msg = (
            "This script must be run as an administrator."
            if _IS_WINDOWS
            else "This script must be run as root."
        )
        print(f"Error: {msg}")
        sys.exit(1)

    full_path_string: str = get_path()

    if dry_run:
        print("[DRY RUN] == CLI dry-run mode — no changes will be made ==")
        print()
        print(f"[DRY RUN] Current PATH ({'Machine' if _IS_WINDOWS else 'session'}):")
        print(
            f"[DRY RUN]   {full_path_string[:200]}{'...' if len(full_path_string) > 200 else ''}"
        )
        print()
    else:
        # Write current PATH to file (only in real mode)
        save_path_to_file(full_path_string)

    # Collect non-flag arguments
    path_args: list[str] = [a for a in sys.argv[1:] if a != "--dry-run"]
    if path_args:
        custom_path: str = path_args[0]
        add_to_path(custom_path, system_wide=True, dry_run=dry_run)
