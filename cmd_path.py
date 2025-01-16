import os
import subprocess
import ctypes
import sys

def check_admin():
    """Check if the script is run as an administrator."""
    if not ctypes.windll.shell32.IsUserAnAdmin():
        return False
    return True

def get_path():
    """Retrieve the current PATH variable using PowerShell."""
    command = [
        "powershell", "-Command",
        "[System.Environment]::GetEnvironmentVariable('Path', 'Machine')"
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        raise ValueError(f"Failed to retrieve PATH variable. Error: {result.stderr.strip()}")

def save_path_to_file(path_string, file_name="path_list.txt"):
    """Save the full PATH string to a .txt file."""
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(path_string)
    print(f"PATH variable saved to '{file_name}'.")

def clear_path():
    command = [
        "powershell", "-Command",
        f"[System.Environment]::SetEnvironmentVariable('Path', '', 'Machine')"
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    pass

def add_to_path(new_path, system_wide=True):
    """Add a new path to the PATH environment variable using PowerShell."""
    current_path = get_path()

    # Check if the new path is already in the PATH variable
    if new_path in current_path:
        print(f"The path '{new_path}' is already in the PATH variable.")
        return

    # Determine the scope: 'Machine' for system-wide, 'User' for user-specific
    scope = "Machine" if system_wide else "User"

    # Construct the new PATH value
    updated_path = f"{current_path};{new_path}"

    # Set the updated PATH variable using PowerShell
    command = [
        "powershell", "-Command",
        f"[System.Environment]::SetEnvironmentVariable('Path', \"{updated_path}\", '{scope}')"
    ]
    result = subprocess.run(command, capture_output=True, text=True)

    # Check for success
    if result.returncode == 0:
        print(f"The path '{new_path}' has been added to the {'system' if system_wide else 'user'} PATH variable.")
    else:
        print(f"Failed to add the path. Error: {result.stderr.strip()}")

if __name__ == "__main__":
    # Check if the script is run as an administrator
    if not check_admin():
        print("Error: This script must be run as an administrator.")
        sys.exit(1)

    # Retrieve the current PATH
    full_path_string = get_path()

    # Save the PATH to a file
    save_path_to_file(full_path_string)

    # Check if a custom path is passed as an argument
    if len(sys.argv) > 1:
        custom_path = sys.argv[1]
        add_to_path(custom_path, system_wide=True)  # Set `system_wide=False` for user-specific PATH updates
