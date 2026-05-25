import subprocess
import ctypes
import sys
from pathlib import Path


def check_admin() -> bool:
    """Check if the script is run as an administrator."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except AttributeError:
        return False


def get_path(scope: str = "Machine") -> str:
    """
    Retrieve the current PATH environment variable using PowerShell.

    Args:
        scope: "Machine" for system-wide or "User" for user-specific PATH.

    Returns:
        The PATH string.

    Raises:
        ValueError: If the PowerShell command fails.
    """
    command: list[str] = [
        "powershell", "-Command",
        f"[System.Environment]::GetEnvironmentVariable('Path', '{scope}')"
    ]
    result: subprocess.CompletedProcess = subprocess.run(
        command, capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        raise ValueError(
            f"Failed to retrieve PATH variable. Error: {result.stderr.strip()}"
        )


def set_path(new_path: str, scope: str = "Machine") -> None:
    """
    Set the PATH environment variable to the given value using PowerShell.

    Args:
        new_path: The full PATH string to set.
        scope: "Machine" for system-wide or "User" for user-specific PATH.

    Raises:
        ValueError: If the PowerShell command fails.
    """
    # Escape double quotes in the path for PowerShell
    escaped_path: str = new_path.replace('"', '\\"')
    command: list[str] = [
        "powershell", "-Command",
        f"[System.Environment]::SetEnvironmentVariable('Path', \"{escaped_path}\", '{scope}')"
    ]
    result: subprocess.CompletedProcess = subprocess.run(
        command, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise ValueError(
            f"Failed to set PATH variable. Error: {result.stderr.strip()}"
        )


def save_path_to_file(
    path_string: str, file_name: str = "path_list.txt"
) -> None:
    """Save the full PATH string to a .txt file."""
    path: Path = Path(file_name)
    path.write_text(path_string, encoding="utf-8")
    print(f"PATH variable saved to '{file_name}'.")


def clear_path(scope: str = "Machine") -> None:
    """
    Clear the PATH environment variable (DANGEROUS: sets PATH to empty).

    Warning: This will remove ALL paths from the environment variable.
    Use with extreme caution.

    Args:
        scope: "Machine" for system-wide or "User" for user-specific PATH.

    Raises:
        ValueError: If the PowerShell command fails.
    """
    command: list[str] = [
        "powershell", "-Command",
        f"[System.Environment]::SetEnvironmentVariable('Path', '', '{scope}')"
    ]
    result: subprocess.CompletedProcess = subprocess.run(
        command, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise ValueError(
            f"Failed to clear PATH variable. Error: {result.stderr.strip()}"
        )


def add_to_path(new_path: str, system_wide: bool = True) -> None:
    """
    Add a new path to the PATH environment variable using PowerShell.

    Args:
        new_path: The directory path to add to PATH. Can be a single path
                  or a semicolon-separated string of paths.
        system_wide: If True, modifies the Machine-level PATH.
                     If False, modifies the User-level PATH.

    Raises:
        ValueError: If the PowerShell command fails or the path is invalid.
    """
    if not new_path or not new_path.strip():
        raise ValueError("Cannot add an empty path to PATH.")

    scope: str = "Machine" if system_wide else "User"
    current_path: str = get_path(scope)

    # Split existing paths into individual entries for duplicate checking
    existing_entries: list[str] = [
        p.strip() for p in current_path.split(";") if p.strip()
    ]

    # Split the new path(s) into individual entries
    new_entries: list[str] = [
        p.strip() for p in new_path.split(";") if p.strip()
    ]

    if not new_entries:
        raise ValueError("No valid paths to add.")

    # Check which entries are already present
    already_present: list[str] = [
        e for e in new_entries if e in existing_entries
    ]
    entries_to_add: list[str] = [
        e for e in new_entries if e not in existing_entries
    ]

    if not entries_to_add:
        print(
            f"All path(s) are already in the PATH variable: {', '.join(already_present)}"
        )
        return

    # Construct the new PATH value
    all_entries: list[str] = existing_entries + entries_to_add
    updated_path: str = ";".join(all_entries) + ";"

    # Set the updated PATH variable using the set_path helper
    set_path(updated_path, scope)

    print(
        f"The path(s) '{'; '.join(entries_to_add)}' have been added to the "
        f"{'system' if system_wide else 'user'} PATH variable."
    )
    if already_present:
        print(
            f"The following path(s) were already present: {', '.join(already_present)}"
        )


if __name__ == "__main__":
    # Check if the script is run as an administrator
    if not check_admin():
        print("Error: This script must be run as an administrator.")
        sys.exit(1)

    # Retrieve the current PATH
    full_path_string: str = get_path()

    # Save the PATH to a file
    save_path_to_file(full_path_string)

    # Check if a custom path is passed as an argument
    if len(sys.argv) > 1:
        custom_path: str = sys.argv[1]
        add_to_path(custom_path, system_wide=True)
