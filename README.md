
# Windows 10 Environment Path Editor

  

## Overview

This application is a user-friendly tool for managing the Windows 10 environment `PATH` variable. It allows users to:

- Select an existing `PATH` variable.

- Edit its values or create new ones.

- Add, remove, or clear values as needed.

  ![enter image description here](/preview.png)

The app is designed to make managing `PATH` variables simple and accessible, eliminating the need to manually navigate system settings or use complex commands.

  

---

  

## Features

-  **Select and Edit Existing Paths**: Browse and update the variables in your environment `PATH`.

-  **Create New Paths**: Easily add new `PATH` variables without errors.

-  **Manage Values**:

- Show all values in the selected `PATH`.

- Add new values.

- Remove specific values.

- Clear all values if required.

  

---

  

## Library: `cmd_path.py`

The app includes a custom library, `cmd_path.py`, which provides:

- Commands to display all current `PATH` values.

- Methods to add, remove, or clear specific values in the `PATH`.

  

This library is at the core of the app, handling all operations with efficiency and reliability.

  

---

  

## Build the App

If you'd like to modify the app and build it yourself, a `build.bat` script is included.

  

### Requirements:

-  **Python**

-  **PyInstaller** library

  

### Steps to Build:

1. Install PyInstaller:

```bash

pip install pyinstaller

  

2. Run the `build.bat` script:

```cmd

build.bat

3. The executable will be created in the dist folder.
```
## How to Use

1.  Run the app executable or Python script **RUN AS ADMIN**
2.  Select an existing `PATH` variable to edit or create a new one.
3.  Use the intuitive interface to:
    -   View all values.
    -   Add, remove, or clear specific values.