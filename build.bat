@echo off
:: Set the current directory as the working directory
set CURRENT_DIR=%cd%

:: Run the pyinstaller command with the current directory
pyinstaller --noconfirm --onedir --windowed ^
--add-data "%CURRENT_DIR%\assets;assets/" ^
--add-data "%CURRENT_DIR%\cmd_path.py;." ^
--add-data "%CURRENT_DIR%\gui_command.py;." ^
"%CURRENT_DIR%\gui.py"

echo Build complete.
pause
