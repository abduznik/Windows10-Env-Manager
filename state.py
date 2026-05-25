"""Shared application state for the Windows10-Env-Manager.

Using a dedicated state module avoids cross-module ``global`` variable
issues that arise when ``selected_path`` is defined in one module and
referenced via ``global`` in another.
"""


class State:
    """Mutable application state.

    All state attributes are class-level so they act as module-level
    singletons without requiring module-level ``global`` declarations.
    """

    selected_path: str = ""


# Convenience reference so callers can write ``state.selected_path``.
state = State()
