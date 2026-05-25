from tkinter import (
    Canvas, Button, PhotoImage, Frame, Listbox,
    SINGLE, messagebox, Entry, StringVar, Label, Toplevel,
)
from pathlib import Path
import cmd_path
from tkinter.filedialog import askdirectory
from utils import ASSETS_PATH, get_appdata_dir
from state import state


_PATH_LIST_FILE = get_appdata_dir() / "path_list.txt"


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

    # Auto-backup before modifying (non-fatal)
    try:
        cmd_path.backup_path()
    except Exception as backup_err:
        print(f"Warning: failed to backup PATH: {backup_err}")

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

        try:
            if not _PATH_LIST_FILE.exists():
                raise FileNotFoundError(f"{_PATH_LIST_FILE} does not exist.")

            # Read the current paths
            path_content: str = _PATH_LIST_FILE.read_text(encoding="utf-8").strip()

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
            _PATH_LIST_FILE.write_text(updated_path_content + _SEP, encoding="utf-8")

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


def _maybe_offer_restore() -> None:
    """Check if multiple backups exist and offer to restore if so."""
    try:
        suggestion = cmd_path.suggest_restore()
        if suggestion is not None:
            count: int = suggestion["count"]
            oldest: str = suggestion["oldest"]
            newest: str = suggestion["newest"]
            if messagebox.askyesno(
                "PATH Backups Available",
                f"You have {count} saved PATH backups.\n\n"
                f"Newest: {newest}\n"
                f"Oldest: {oldest}\n\n"
                "Would you like to restore a previous version?",
            ):
                _show_restore_dialog()
    except Exception as e:
        # Non-fatal — just log
        print(f"Warning: could not check backups: {e}")


def _show_restore_dialog() -> None:
    """Show a dialog listing all available backups for the user to pick from."""
    try:
        backups = cmd_path.list_backups()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to list backups: {e}")
        return

    if not backups:
        messagebox.showinfo("No Backups", "No backups found.")
        return

    popup: Toplevel = Toplevel()
    popup.title("Restore PATH from Backup")
    popup.geometry("500x400")
    popup.configure(bg="#0949A8")

    Label(
        popup,
        text="Select a backup to restore:",
        bg="#0949A8",
        fg="white",
        font=("Arial", 11),
    ).pack(pady=(15, 5))

    backup_listbox: Listbox = Listbox(
        popup,
        bg="#083A85",
        fg="white",
        selectmode=SINGLE,
        font=("Courier", 9),
        width=65,
        height=12,
    )

    for b in backups:
        ts: str = b["timestamp"]
        path_preview: str = b["path"]
        scope: str = b["scope"]
        backup_listbox.insert("end", f"{ts}  [{scope}]  {path_preview}")

    backup_listbox.pack(padx=15, pady=10)

    def do_restore() -> None:
        selected = backup_listbox.curselection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select a backup first.")
            return
        idx: int = selected[0]
        try:
            cmd_path.restore_at_index(idx)
            messagebox.showinfo("Restored", "PATH restored successfully!")
            popup.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    Button(
        popup,
        text="Restore Selected Backup",
        bg="#0A5BC8",
        fg="white",
        font=("Arial", 10),
        command=do_restore,
        relief="flat",
    ).pack(pady=(5, 15))


def create_scrollable_path_list(canvas: Canvas) -> None:
    """Create a scrollable list of paths retrieved from cmd_path."""

    try:
        full_path_string: str = cmd_path.get_path()
        _PATH_LIST_FILE.write_text(full_path_string, encoding="utf-8")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to retrieve PATH: {e}")
        print(f"Error retrieving PATH: {e}")
        return

    if not _PATH_LIST_FILE.exists():
        messagebox.showerror("Error", "Could not create path list file.")
        return

    try:
        paths: list[str] = [
            p for p in _PATH_LIST_FILE.read_text(encoding="utf-8").split(_SEP) if p
        ]
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read path list: {e}")
        print(f"Error reading path list: {e}")
        return

    # Check if there are multiple backups to suggest a restore
    _maybe_offer_restore()

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
