from tkinter import (
    Canvas, Button, PhotoImage, Frame, Listbox,
    SINGLE, messagebox, Entry, StringVar, Label, Toplevel,
)
import os
from pathlib import Path
import cmd_path
from tkinter.filedialog import askdirectory
from utils import ASSETS_PATH
from state import state


_SEP = ";"  # internal path-list file delimiter (always ";" across all platforms)


def relative_to_assets(path: str) -> Path:
    """Resolve a path relative to the assets directory."""
    return ASSETS_PATH / Path(path)


def create_new_dir() -> None:
    """Open a file dialog to select a directory and add it to the PATH."""
    selected_directory: str = askdirectory(title="Select a Folder")

    if not selected_directory:
        messagebox.showinfo("No Folder Selected", "Please select a folder to add to the PATH.")
        return

    # Ask for confirmation before modifying the system PATH
    if not messagebox.askyesno(
        "Confirm PATH Modification",
        f"Are you sure you want to add the following directory to the "
        f"system PATH?\n\n{selected_directory}",
    ):
        return

    try:
        cmd_path.add_to_path(selected_directory)
        messagebox.showinfo(
            "Directory Added",
            f"Directory '{selected_directory}' has been added to the PATH.",
        )
        print(f"Added to PATH: {selected_directory}")
    except Exception as e:
        messagebox.showerror("Error", str(e))
        print(f"Error adding directory to PATH: {e}")

    # Backup before modification
    try:
        cmd_path.backup_path()
    except Exception as backup_err:
        print(f"Warning: failed to backup PATH: {backup_err}")


def open_path_editor() -> None:
    """Open a popup window to edit the currently selected path."""
    if not state.selected_path:
        messagebox.showinfo("No Path Selected", "Please select a folder first!")
        return

    # Create a popup window
    popup: Toplevel = Toplevel()
    popup.title("Edit Path")
    popup.geometry("400x200")
    popup.configure(bg="#0949A8")

    # Add a label
    Label(
        popup,
        text="Edit Selected Path:",
        bg="#0949A8",
        fg="white",
        font=("Arial", 12),
    ).pack(pady=10)

    # Add an entry pre-filled with the selected path
    path_var: StringVar = StringVar(value=state.selected_path)
    path_entry: Entry = Entry(
        popup,
        textvariable=path_var,
        width=50,
        bg="#093B85",
        fg="white",
        relief="flat",
        font=("Arial", 10),
    )
    path_entry.pack(pady=5, padx=10)

    # Load button images
    try:
        submit_image: PhotoImage = PhotoImage(file=relative_to_assets("button_4.png"))
        cancel_image: PhotoImage = PhotoImage(file=relative_to_assets("button_5.png"))
    except Exception as e:
        messagebox.showerror("Asset Error", f"Failed to load button images: {e}")
        popup.destroy()
        return

    def submit_path() -> None:
        """Replace the selected path with the user-entered value."""
        new_path: str = path_var.get().strip()

        if not new_path:
            messagebox.showerror("Error", "Path cannot be empty.")
            return

        path_file: str = "path_list.txt"

        try:
            if not os.path.exists(path_file):
                raise FileNotFoundError(f"{path_file} does not exist.")

            # Read the current paths
            path_content: str = Path(path_file).read_text(encoding="utf-8").strip()

            # Split into individual paths and remove empties
            paths: list[str] = [p for p in path_content.split(_SEP) if p]

            if state.selected_path not in paths:
                raise ValueError(f"Selected path '{state.selected_path}' not found in the file.")

            # Replace the old path with the new one
            paths = [new_path if p == state.selected_path else p for p in paths]

            # Join with platform path separator (no trailing separator)
            updated_path_content: str = _SEP.join(paths)

            # Confirm the modification with the user
            if not messagebox.askyesno(
                "Confirm PATH Modification",
                f"Are you sure you want to update the system PATH?\n\n"
                f"This will replace:\n{state.selected_path}\n\n"
                f"With:\n{new_path}",
            ):
                return

            # Update the system PATH via cmd_path
            cmd_path.set_path(updated_path_content)

            # Write back to the file (add trailing separator for consistency)
            Path(path_file).write_text(updated_path_content + _SEP, encoding="utf-8")

            messagebox.showinfo(
                "Path Updated",
                f"Replaced '{state.selected_path}' with '{new_path}' in the PATH.",
            )
            print(f"Updated PATH: {updated_path_content}")

            popup.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))
            print(f"Error updating path: {e}")

    def cancel_popup() -> None:
        """Close the popup without saving."""
        popup.destroy()

    submit_button: Button = Button(
        popup,
        image=submit_image,
        borderwidth=0,
        highlightthickness=0,
        command=submit_path,
        relief="flat",
        bg="#0949A8",
        activebackground="#0949A8",
    )
    submit_button.pack(side="left", padx=20, pady=20)

    cancel_button: Button = Button(
        popup,
        image=cancel_image,
        borderwidth=0,
        highlightthickness=0,
        command=cancel_popup,
        relief="flat",
        bg="#0949A8",
        activebackground="#0949A8",
    )
    cancel_button.pack(side="right", padx=20, pady=20)

    # Keep references to prevent garbage collection
    popup.submit_image = submit_image
    popup.cancel_image = cancel_image


def create_scrollable_path_list(canvas: Canvas) -> None:
    """Create a scrollable list of paths retrieved from cmd_path."""

    try:
        full_path_string: str = cmd_path.get_path()
        cmd_path.save_path_to_file(full_path_string)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to retrieve PATH: {e}")
        print(f"Error retrieving PATH: {e}")
        return

    path_file: Path = Path("path_list.txt")
    if not path_file.exists():
        messagebox.showerror("Error", "Could not create path list file.")
        return

    try:
        paths: list[str] = [
            p for p in path_file.read_text(encoding="utf-8").split(_SEP) if p
        ]
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read path list: {e}")
        print(f"Error reading path list: {e}")
        return

    # Create a frame inside the canvas to hold the listbox
    frame: Frame = Frame(canvas, bg="#0948A8", width=386)
    canvas.create_window((7, 158), window=frame, anchor="nw")

    # Create the listbox widget
    listbox: Listbox = Listbox(
        frame,
        bg="#083A85",
        fg="white",
        selectmode=SINGLE,
        font=("Helvetica", 9),
        width=52,
        height=22,
    )

    for path in paths:
        listbox.insert("end", path)

    def on_select(event: object) -> None:
        """Update selected_path when the user clicks an item."""
        selected_indices = listbox.curselection()
        if selected_indices:
            state.selected_path = listbox.get(selected_indices[0])
            print(f"Selected Path: {state.selected_path}")

    listbox.bind("<<ListboxSelect>>", on_select)
    listbox.pack(padx=10, pady=10)

    frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))
