"""Template for user-authored Input Bridge controls.

Copy this file into the configured Input Bridge codebase and replace the
example handlers with commands for your own applications. Input Bridge runs
the file in a child Python process and provides the selected control through
``INPUT_BRIDGE_CONTROL``.
"""

from __future__ import annotations

import os
from collections.abc import Callable

ControlHandler = Callable[[], None]


def show_message() -> None:
    """Replace this example with a useful action."""

    print("Configure this handler in your user codebase.")


def run_command() -> None:
    """Replace this example with a command for the selected application."""

    print("Add your application command here.")


CONTROL_HANDLERS: dict[str, ControlHandler] = {
    # Replace these examples with the controls used by your profile.
    "R1C1": show_message,
    "R1C2": run_command,
}


def get_handler(control: str | None) -> ControlHandler:
    """Return the handler assigned to an Input Bridge control."""

    handler = CONTROL_HANDLERS.get(control)
    if handler is None:
        raise RuntimeError(
            f"No handler configured for Input Bridge control: {control}"
        )
    return handler


def main() -> None:
    """Dispatch the control event received from Input Bridge."""

    control = os.environ.get("INPUT_BRIDGE_CONTROL")
    get_handler(control)()


if __name__ == "__main__":
    main()
