from pathlib import Path
import cmd_path
from tkinter import Tk, Canvas, Button, PhotoImage
import ctypes
from gui_command import *

OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"C:\Users\Yan\Documents\Path_editor\build\assets\frame0")

bypass = True
selected_path = ""

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
    
def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)


# Initialize the Tkinter window
window = Tk()
window.geometry("400x600")
window.configure(bg="#0948A8")
window.title("Environment Paths")

# Create the canvas with the specified configuration
canvas = Canvas(
    window,
    bg="#0948A8",
    height=600,
    width=400,
    bd=0,
    highlightthickness=0,
    relief="ridge"
)

# Create a rectangle and the text you already had
canvas.create_rectangle(
    0.0,
    0.0,
    400.0,
    148.0,
    fill="#002832",
    outline=""
)

canvas.create_text(
    7.0,
    13.0,
    anchor="nw",
    text="Windows 10\nEnvironment\nPath Editor",
    fill="#FFFFFF",
    font=("Inter Bold", 36 * -1)
)

canvas.create_rectangle(
    7.0,
    158.0,
    393.0,
    524.0,
    fill="#083A85",
    outline=""
)

# Place the canvas in the window
canvas.place(x=0, y=0)

# Create buttons
button_image_1 = PhotoImage(file=relative_to_assets("button_1.png"))
button_1 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: window.destroy(),
    relief="flat"
)
button_1.place(x=273.0, y=524.0, width=127.0, height=76.0)

button_image_2 = PhotoImage(file=relative_to_assets("button_2.png"))
button_2 = Button(
    image=button_image_2,
    borderwidth=0,
    highlightthickness=0,
    command=lambda:create_new_dir(),
    relief="flat"
)
button_2.place(x=136.0, y=524.0, width=127.0, height=76.0)

button_image_3 = PhotoImage(file=relative_to_assets("button_3.png"))
button_3 = Button(
    image=button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=open_path_editor,
    relief="flat"
)
button_3.place(x=0.0, y=524.0, width=127.0, height=76.0)

# Create the scrollable path list on the canvas (positioned within the defined dimensions)
create_scrollable_path_list(canvas)

# Start the Tkinter event loop
window.resizable(False, False)
window.mainloop()
