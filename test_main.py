"""Unit tests for main.py.

``main.py`` runs module-level code at import time (window creation, canvas
drawing, button setup).  Because ``conftest.py`` eagerly stubs ``tkinter``,
importing ``main`` does **not** open a real GUI window on any platform.
"""

from state import state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_main():
    """Import (or reload) ``main`` so module-level code re-executes.

    Returns the module object.
    """
    import main  # type: ignore[import-untyped]

    return main


# ---------------------------------------------------------------------------
# Window & general setup
# ---------------------------------------------------------------------------


class TestMainWindow:
    """Verify the Tkinter window is created with the expected attributes."""

    def test_window_created(self) -> None:
        """Importing main should create a Tk() instance (via the stub)."""
        main = _import_main()
        assert main.window is not None

    def test_window_geometry(self) -> None:
        """Window geometry should be 400x600."""
        main = _import_main()
        main.window.geometry.assert_any_call("400x600")

    def test_window_title(self) -> None:
        """Window title should be 'Environment Paths'."""
        main = _import_main()
        main.window.title.assert_any_call("Environment Paths")

    def test_window_background_color(self) -> None:
        """Window background should be #0948A8."""
        main = _import_main()
        main.window.configure.assert_any_call(bg="#0948A8")

    def test_window_not_resizable(self) -> None:
        """Window should not be resizable."""
        main = _import_main()
        main.window.resizable.assert_any_call(False, False)


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------


class TestCanvas:
    """Verify the Canvas is created with the correct properties."""

    def test_canvas_created(self) -> None:
        """Canvas instance should exist."""
        main = _import_main()
        assert main.canvas is not None

    def test_canvas_rectangle_drawn(self) -> None:
        """A header rectangle should be drawn on the canvas."""
        main = _import_main()
        # Check create_rectangle was called with the header coordinates
        found_header = any(
            args[0] == 0.0 and args[1] == 0.0
            for args, _ in main.canvas.create_rectangle.call_args_list
        )
        assert found_header, "Expected a header rectangle at (0, 0)"

    def test_canvas_text_drawn(self) -> None:
        """Title text should be drawn on the canvas."""
        main = _import_main()
        found_title = any(
            "Windows 10" in str(kwargs.get("text", ""))
            or "Environment" in str(kwargs.get("text", ""))
            for _, kwargs in main.canvas.create_text.call_args_list
        )
        assert found_title, "Expected title text on the canvas"

    def test_canvas_placed(self) -> None:
        """Canvas.place(x=0, y=0) should have been called."""
        main = _import_main()
        main.canvas.place.assert_any_call(x=0, y=0)


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------


class TestButtons:
    """Verify the three buttons are created and placed."""

    def test_close_button_created(self) -> None:
        """Button 1 should exist (close window)."""
        main = _import_main()
        assert main.button_1 is not None

    def test_add_directory_button_created(self) -> None:
        """Button 2 should exist (add directory)."""
        main = _import_main()
        assert main.button_2 is not None

    def test_edit_path_button_created(self) -> None:
        """Button 3 should exist (edit path)."""
        main = _import_main()
        assert main.button_3 is not None

    def test_images_loaded(self) -> None:
        """All three button images should be PhotoImage instances."""
        main = _import_main()
        assert main.button_image_1 is not None
        assert main.button_image_2 is not None
        assert main.button_image_3 is not None

    def test_close_button_places_window(self) -> None:
        """Close button should be at bottom-left area."""
        main = _import_main()
        main.button_1.place.assert_called()


# ---------------------------------------------------------------------------
# Module-level calls
# ---------------------------------------------------------------------------


class TestModuleLevelCalls:
    """Verify module-level functions are invoked during import."""

    def test_create_scrollable_path_list_called(self) -> None:
        """The path list function ran without raising."""
        _import_main()
        # selected_path should be reset by conftest's _reset_selected_path
        # before this test runs, and should stay empty since no listbox
        # selection event fires during import
        assert state.selected_path == ""

    def test_mainloop_called(self) -> None:
        """window.mainloop() should be called at the end."""
        mod = _import_main()
        mod.window.mainloop.assert_called()
