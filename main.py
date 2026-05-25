from pathlib import Path
from tkinter import Tk, Canvas, Button, PhotoImage
import ctypes
from gui_command import (
    create_new_dir,
    open_path_editor,
    create_scrollable_path_list,
)
from utils import ASSETS_PATH


def is_admin() -> bool:
    """Check if the script is run with administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except AttributeError:
        return False


def relative_to_assets(path: str) -> Path:
    """Resolve a path relative to the assets directory."""
    return ASSETS_PATH / Path(path)


# Initialize the Tkinter window
window: Tk = Tk()
window.geometry("400x600")
window.configure(bg="#0948A8")
window.title("Environment Paths")

# Create the canvas
canvas: Canvas = Canvas(
    window,
    bg="#0948A8",
    height=600,
    width=400,
    bd=0,
    highlightthickness=0,
    relief="ridge",
)

# Header rectangle
canvas.create_rectangle(
    0.0,
    0.0,
    400.0,
    148.0,
    fill="#002832",
    outline="",
)

canvas.create_text(
    7.0,
    13.0,
    anchor="nw",
    text="Windows 10\nEnvironment\nPath Editor",
    fill="#FFFFFF",
    font=("Inter Bold", 36 * -1),
)

canvas.create_rectangle(
    7.0,
    158.0,
    393.0,
    524.0,
    fill="#083A85",
    outline="",
)

canvas.place(x=0, y=0)


def _load_button_image(name: str) -> PhotoImage:
    """Load a button image, trying .png first (Windows Tk 8.6+), then .gif (macOS/Linux Tk 8.5)."""
    for ext in (".png", ".gif"):
        path = relative_to_assets(f"{name}{ext}")
        if path.exists():
            try:
                return PhotoImage(file=str(path))
            except Exception:
                continue
    # Fallback: create a tiny blank image
    return PhotoImage(width=1, height=1)


# Create buttons
button_image_1: PhotoImage = _load_button_image("button_1")
button_1: Button = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: window.destroy(),
    relief="flat",
)
button_1.place(x=273.0, y=524.0, width=127.0, height=76.0)

button_image_2: PhotoImage = _load_button_image("button_2")
button_2: Button = Button(
    image=button_image_2,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: create_new_dir(),
    relief="flat",
)
button_2.place(x=136.0, y=524.0, width=127.0, height=76.0)

button_image_3: PhotoImage = _load_button_image("button_3")
button_3: Button = Button(
    image=button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=open_path_editor,
    relief="flat",
)
button_3.place(x=0.0, y=524.0, width=127.0, height=76.0)

# Create the scrollable path list
create_scrollable_path_list(canvas)

# Start the Tkinter event loop
window.resizable(False, False)
window.mainloop()
