from tkinter import Tk, Canvas, Button, PhotoImage, Frame, Listbox, SINGLE, messagebox, Entry, StringVar, Label, Toplevel
import os
from pathlib import Path
import cmd_path
from tkinter.filedialog import askdirectory

OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"C:\Users\Yan\Documents\Path_editor\build\assets\frame0")

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

def create_new_dir():
    """Open a file dialog to select a directory and add it to the PATH."""
    # Open a directory dialog to let the user select a folder
    selected_directory = askdirectory(title="Select a Folder")

    if not selected_directory:
        messagebox.showinfo("No Folder Selected", "Please select a folder to add to the PATH.")
        return

    try:
        # Add the selected directory to the PATH
        cmd_path.add_to_path(selected_directory)

        # Optionally, you can update the listbox with the new directory path
        messagebox.showinfo("Directory Added", f"Directory '{selected_directory}' has been added to the PATH.")
        print(f"Added to PATH: {selected_directory}")

    except Exception as e:
        # Handle any errors that occur during the process
        messagebox.showerror("Error", str(e))
        print(f"Error: {e}")


def open_path_editor():
    global selected_path
    if not selected_path:
        messagebox.showinfo("No Path Selected", "Please select a folder first!")
        return

    # Create a popup window
    popup = Toplevel()
    popup.title("Edit Path")
    popup.geometry("400x200")
    popup.configure(bg="#0949A8")  # Set background color

    # Add a label
    Label(
        popup,
        text="Edit Selected Path:",
        bg="#0949A8",
        fg="white",
        font=("Arial", 12)
    ).pack(pady=10)

    # Add an entry pre-filled with the selected path
    path_var = StringVar(value=selected_path)
    path_entry = Entry(
        popup,
        textvariable=path_var,
        width=50,
        bg="#093B85",  # Entry background color
        fg="white",
        relief="flat",
        font=("Arial", 10)
    )
    path_entry.pack(pady=5, padx=10)

    # Load button images using relative_to_assets
    submit_image = PhotoImage(file=relative_to_assets("button_4.png"))
    cancel_image = PhotoImage(file=relative_to_assets("button_5.png"))

    # Function for the Submit button
    def submit_path():
        global selected_path

        # Get the new path entered by the user
        new_path = path_var.get()  # Value from the entry field
        path_file = "path_list.txt"

        try:
            # Check if the path file exists
            if not os.path.exists(path_file):
                raise FileNotFoundError(f"{path_file} does not exist.")
            
            # Read the current paths as a single semicolon-separated string
            with open(path_file, "r") as file:
                path_content = file.read().strip()
            
            # Split the content into a list of individual paths
            paths = path_content.split(";")
            
            # Remove empty strings that may occur due to trailing semicolons
            paths = [p for p in paths if p]

            # Check if the selected path exists and remove it
            if selected_path in paths:
                paths.remove(selected_path)
            else:
                raise ValueError(f"Selected path '{selected_path}' not found in the file.")
            
            # Add the new path from the entry field if not already in the list
            if new_path not in paths:
                paths.append(new_path)

            # Join the updated paths back into a semicolon-separated string
            updated_path_content = ";".join(paths) + ";"
            cmd_path.clear_path()
            cmd_path.add_to_path(updated_path_content)

            # Write back the updated paths to the file
            with open(path_file, "w") as file:
                file.write(updated_path_content)

            # Show confirmation
            messagebox.showinfo("Path Updated", f"Replaced '{selected_path}' with '{new_path}' in the PATH.")
            print(f"Updated PATH:\n{updated_path_content}")

            # Close the popup window
            popup.destroy()

        except Exception as e:
            # Handle errors
            messagebox.showerror("Error", str(e))
            print(f"Error: {e}")

    def cancel_popup():
        popup.destroy()

    # Add Submit and Cancel buttons using images and using pack for placement
    submit_button = Button(
        popup,
        image=submit_image,
        borderwidth=0,
        highlightthickness=0,
        command=submit_path,
        relief="flat",
        bg="#0949A8",  # Match the background for seamless appearance
        activebackground="#0949A8"
    )
    submit_button.pack(side="left", padx=20, pady=20)

    cancel_button = Button(
        popup,
        image=cancel_image,
        borderwidth=0,
        highlightthickness=0,
        command=cancel_popup,
        relief="flat",
        bg="#0949A8",  # Match the background for seamless appearance
        activebackground="#0949A8"
    )
    cancel_button.pack(side="right", padx=20, pady=20)

    # Keep a reference to the images to prevent garbage collection
    popup.submit_image = submit_image
    popup.cancel_image = cancel_image

def create_scrollable_path_list(canvas):
    """Create a scrollable list of paths retrieved from cmd_path."""
    # Retrieve the current PATH using cmd_path's get_path() method
    full_path_string = cmd_path.get_path()

    # Save the PATH to a file
    cmd_path.save_path_to_file(full_path_string)

    # Read the paths from the saved file
    with open("path_list.txt", "r", encoding="utf-8") as file:
        paths = file.read().split(";")  # Assuming paths are separated by semicolons

    # Create a frame inside the canvas to hold the listbox
    frame = Frame(canvas, bg="#0948A8", width=386)  # Fixed width to fit within the canvas
    canvas.create_window((7, 158), window=frame, anchor="nw")  # Place it at the rectangle position

    # Create the listbox widget to display paths
    listbox = Listbox(
        frame,
        bg="#083A85",
        fg="white",
        selectmode=SINGLE,  # Allow only one item to be selected at a time
        font=("Helvetica", 9),
        width=52,  # Set width of the listbox (adjust as needed)
        height=22  # Set height of the listbox (adjust based on number of items)
    )

    # Insert paths into the listbox
    for path in paths:
        listbox.insert("end", path)

    # Bind a function to be triggered when an item is selected
    def on_select(event):
        global selected_path
        selected_index = listbox.curselection()
        if selected_index:
            selected_path = listbox.get(selected_index)
            print(f"Selected Path: {selected_path}")  # Replace this with desired behavior

    listbox.bind("<<ListboxSelect>>", on_select)

    # Place the listbox inside the frame
    listbox.pack(padx=10, pady=10)

    # Update the scrollable region to accommodate all items
    frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))
