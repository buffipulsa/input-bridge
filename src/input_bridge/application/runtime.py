"""Runtime boundary between input sources, profiles, and action dispatch."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from ..domain.profiles import ProfileDocument


@dataclass(frozen=True)
class LogicalInputEvent:
    """Represent one normalized macropad control event.

    Parameters
    ----------
    control : str
        Stable logical control identifier, such as ``R1C1`` or ``K1-CW``.
    trigger : str, default="press"
        Trigger type emitted by the control.
    """

    control: str
    trigger: str = "press"


class RuntimeMode(Enum):
    """Control whether a runtime dispatch is observational or executable."""

    DRY_RUN = "dry_run"
    EXECUTE = "execute"


class InputEventSource(Protocol):
    """Source of normalized input events."""

    def start(self, on_event: Callable[[LogicalInputEvent], None]) -> None:
        """Start sending events to ``on_event``."""

    def stop(self) -> None:
        """Stop sending events."""


class ActionDispatcher(Protocol):
    """Destination for events resolved against a profile."""

    def dispatch(
        self,
        event: LogicalInputEvent,
        profile: ProfileDocument,
    ) -> None:
        """Resolve and dispatch one event."""


class ProfileRuntime:
    """Coordinate an input source and an injected action dispatcher.

    The runtime deliberately knows neither about Windows Raw Input nor about
    a UI toolkit. Those concerns can be supplied through the two protocols.
    """

    def __init__(
        self,
        profile: ProfileDocument,
        input_source: InputEventSource,
        dispatcher: ActionDispatcher,
    ) -> None:
        self.profile = profile
        self.input_source = input_source
        self.dispatcher = dispatcher
        self.is_running = False
        self.is_emergency_stopped = False
        self.mode = RuntimeMode.DRY_RUN

    def set_mode(self, mode: RuntimeMode) -> None:
        """Set the dispatch mode for future events."""

        self.mode = mode

    def start(self) -> None:
        """Start the input source for this profile."""

        if self.is_emergency_stopped:
            raise RuntimeError("runtime is emergency-stopped; reset it before starting")
        if self.is_running:
            return
        self.input_source.start(self._handle_event)
        self.is_running = True

    def stop(self) -> None:
        """Stop the input source for this profile."""

        if not self.is_running:
            return
        self.input_source.stop()
        self.is_running = False

    def emergency_stop(self) -> None:
        """Stop input and require an explicit reset before restarting."""

        if self.is_running:
            self.input_source.stop()
        self.is_running = False
        self.is_emergency_stopped = True

    def reset_emergency_stop(self) -> None:
        """Clear the emergency-stop state without starting input."""

        self.is_emergency_stopped = False

    def dispatch(self, event: LogicalInputEvent) -> None:
        """Dispatch an explicit event while the runtime is running.

        This is used by the UI's dry-run simulation control. Hardware input
        should normally arrive through the configured input source.
        """

        self._handle_event(event)

    def _handle_event(self, event: LogicalInputEvent) -> None:
        if self.is_running and not self.is_emergency_stopped:
            self.dispatcher.dispatch(event, self.profile)


class FakeInputSource:
    """Manually controlled input source for UI and application tests."""

    def __init__(self) -> None:
        self._on_event: Callable[[LogicalInputEvent], None] | None = None
        self.is_running = False

    def start(self, on_event: Callable[[LogicalInputEvent], None]) -> None:
        """Start accepting events from :meth:`emit`."""

        self._on_event = on_event
        self.is_running = True

    def stop(self) -> None:
        """Stop accepting events from :meth:`emit`."""

        self._on_event = None
        self.is_running = False

    def emit(self, event: LogicalInputEvent) -> None:
        """Emit one event to the runtime when the source is running.

        Raises
        ------
        RuntimeError
            If the fake source has not been started.
        """

        if self._on_event is None:
            raise RuntimeError("fake input source is not running")
        self._on_event(event)
