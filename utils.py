import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_PATH = PROJECT_ROOT / "assets" / "frame0"

_APP_NAME = "Windows10-Env-Manager"


def get_appdata_dir() -> Path:
    """Return the application data directory, creating it if needed.

    Cross-platform path:

    - Windows: ``%%APPDATA%%\\Windows10-Env-Manager``
    - macOS:   ``~/Library/Application Support/Windows10-Env-Manager``
    - Linux:   ``~/.local/share/Windows10-Env-Manager``

    The directory is created (including parents) on first access.
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"

    app_dir = base / _APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir
