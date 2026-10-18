"""Small host actions for logical macropad events."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from ..domain.profiles import BindingDefinition, ProfileDocument

WINDOW_ACTION_LABELS = {
    "open_file_explorer": "Open File Explorer",
    "open_settings": "Open Windows Settings",
    "open_task_manager": "Open Task Manager",
    "open_notepad": "Open Notepad",
    "open_terminal": "Open Windows Terminal",
}

WINDOW_EXECUTABLES = {
    "open_file_explorer": ("explorer.exe",),
    "open_task_manager": ("taskmgr.exe",),
    "open_notepad": ("notepad.exe",),
    "open_terminal": ("wt.exe",),
}


def default_codebase_directory() -> Path:
    """Return the default user-owned directory for external scripts."""

    local_app_data = os.environ.get("LOCALAPPDATA")
    base_directory = (
        Path(local_app_data)
        if local_app_data
        else Path.home() / "AppData" / "Local"
    )
    return base_directory / "InputBridge" / "code"


def resolve_script_source(
    script: object,
    codebase_root: Path | None = None,
) -> str:
    """Return embedded or validated external source for a script definition."""

    path = getattr(script, "path", None)
    if not path:
        source = getattr(script, "source", "")
        if not source:
            raise LookupError("script has no embedded source or external path")
        return source

    relative_path = Path(path)
    if relative_path.is_absolute():
        raise ValueError("external script paths must be relative to the codebase")
    root = (codebase_root or default_codebase_directory()).expanduser().resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("external script path escapes the configured codebase") from error
    if candidate.suffix.lower() != ".py":
        raise ValueError("external script paths must point to a .py file")
    return candidate.read_text(encoding="utf-8")


def find_profile_binding(
    logical_event: str,
    profile: ProfileDocument,
    trigger: str = "press",
    active_layer_path: Sequence[str] = (),
) -> BindingDefinition | None:
    """Find the profile binding for a control and trigger.

    Parameters
    ----------
    logical_event : str
        Stable logical control identifier.
    profile : ProfileDocument
        Profile containing the bindings to search.
    trigger : str, default="press"
        Trigger type to match.
    active_layer_path : Sequence[str], optional
        Current layer path. A binding applies when its path is a prefix of
        this path; the most specific matching binding wins.

    Returns
    -------
    BindingDefinition or None
        The matching binding, if one exists.
    """

    active_path = tuple(active_layer_path)
    candidates = [
        item
        for item in profile.bindings
        if (
            item.control == logical_event
            and item.trigger == trigger
            and tuple(item.layer_path) == active_path[: len(item.layer_path)]
        )
    ]
    return max(candidates, key=lambda item: len(item.layer_path), default=None)


def describe_profile_action(
    logical_event: str,
    profile: ProfileDocument,
    trigger: str = "press",
    active_layer_path: Sequence[str] = (),
) -> str:
    """Describe a profile action without executing it.

    Parameters
    ----------
    logical_event : str
        Stable logical control identifier.
    profile : ProfileDocument
        Profile containing the action definitions.
    trigger : str, default="press"
        Trigger type to match.
    active_layer_path : Sequence[str], optional
        Current layer path used to select the most specific binding.

    Returns
    -------
    str
        Human-readable action description suitable for a dry-run UI.
    """

    binding = find_profile_binding(
        logical_event,
        profile,
        trigger,
        active_layer_path,
    )
    if binding is None:
        return "Unassigned"
    if binding.action_id in WINDOW_ACTION_LABELS:
        return WINDOW_ACTION_LABELS[binding.action_id]
    if binding.action_id == "run_script":
        if binding.script_id is None:
            return "Script: missing script id"
        script = next(
            (item for item in profile.scripts if item.script_id == binding.script_id),
            None,
        )
        if script is None:
            return f"Script: missing {binding.script_id}"
        return f"Script: {script.name}"
    return f"Action: {binding.action_id}"


def execute_profile_action(
    logical_event: str,
    profile: ProfileDocument,
    trigger: str = "press",
    active_layer_path: Sequence[str] = (),
    codebase_root: Path | None = None,
) -> None:
    """Execute the script bound to one logical event in a profile.

    This function is intentionally only called by an explicit execution path.
    The script is run in a child Python process without shell interpolation.

    Parameters
    ----------
    logical_event : str
        Stable logical control identifier emitted by the event normalizer.
    profile : ProfileDocument
        Profile containing the binding and script definition.
    trigger : str, default="press"
        Trigger type to match.
    active_layer_path : Sequence[str], optional
        Active layer path used to select the most specific binding.
    codebase_root : pathlib.Path, optional
        User-selected root for external script files.

    Raises
    ------
    LookupError
        If the event has no binding or its script is missing.
    subprocess.CalledProcessError
        If the script process exits unsuccessfully.
    """

    binding = find_profile_binding(
        logical_event,
        profile,
        trigger,
        active_layer_path,
    )
    if binding is None:
        raise LookupError(f"no profile binding for {logical_event!r}")
    if binding.action_id in WINDOW_ACTION_LABELS:
        if os.name != "nt":
            raise RuntimeError("Windows actions require Windows")
        if binding.action_id == "open_settings":
            os.startfile("ms-settings:")
            return
        command = WINDOW_EXECUTABLES.get(binding.action_id)
        if command is None:
            raise LookupError(f"unknown Windows action {binding.action_id!r}")
        subprocess.run(command, check=True, shell=False)
        return
    if binding.action_id != "run_script" or binding.script_id is None:
        raise LookupError(f"binding for {logical_event!r} is not a script action")

    script = next(
        (item for item in profile.scripts if item.script_id == binding.script_id),
        None,
    )
    if script is None:
        raise LookupError(f"script {binding.script_id!r} was not found")

    source = resolve_script_source(script, codebase_root)
    environment = os.environ.copy()
    environment["INPUT_BRIDGE_ACTION_ID"] = binding.action_id
    environment["INPUT_BRIDGE_CONTROL"] = logical_event
    completed = subprocess.run(
        [sys.executable, "-c", source],
        shell=False,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"script exited with code {completed.returncode}")
