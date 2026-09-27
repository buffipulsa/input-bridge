"""Tests for the profile runtime boundary."""

import unittest

from input_bridge.application.runtime import (
    FakeInputSource,
    LogicalInputEvent,
    ProfileRuntime,
    RuntimeMode,
)
from input_bridge.domain.profiles import ProfileDocument


class RecordingDispatcher:
    """Test double that records events without executing actions."""

    def __init__(self) -> None:
        self.events: list[tuple[LogicalInputEvent, ProfileDocument]] = []

    def dispatch(
        self,
        event: LogicalInputEvent,
        profile: ProfileDocument,
    ) -> None:
        self.events.append((event, profile))


class ProfileRuntimeTests(unittest.TestCase):
    """Verify runtime lifecycle and event routing."""

    def test_events_route_only_while_runtime_is_running(self) -> None:
        source = FakeInputSource()
        dispatcher = RecordingDispatcher()
        profile = ProfileDocument(name="Test")
        runtime = ProfileRuntime(profile, source, dispatcher)

        runtime.start()
        event = LogicalInputEvent(control="R1C1")
        source.emit(event)
        runtime.stop()

        self.assertEqual(dispatcher.events, [(event, profile)])
        self.assertFalse(runtime.is_running)
        self.assertFalse(source.is_running)

    def test_fake_source_rejects_events_before_start(self) -> None:
        source = FakeInputSource()

        with self.assertRaisesRegex(RuntimeError, "not running"):
            source.emit(LogicalInputEvent(control="R1C1"))

    def test_start_and_stop_are_idempotent(self) -> None:
        source = FakeInputSource()
        dispatcher = RecordingDispatcher()
        runtime = ProfileRuntime(ProfileDocument(name="Test"), source, dispatcher)

        runtime.start()
        runtime.start()
        runtime.stop()
        runtime.stop()

        self.assertFalse(runtime.is_running)
        self.assertFalse(source.is_running)

    def test_emergency_stop_blocks_events_until_reset_and_restart(self) -> None:
        source = FakeInputSource()
        dispatcher = RecordingDispatcher()
        runtime = ProfileRuntime(ProfileDocument(name="Test"), source, dispatcher)

        runtime.start()
        runtime.emergency_stop()
        runtime.dispatch(LogicalInputEvent(control="R1C1"))

        self.assertTrue(runtime.is_emergency_stopped)
        self.assertEqual(dispatcher.events, [])
        with self.assertRaisesRegex(RuntimeError, "emergency-stopped"):
            runtime.start()

        runtime.reset_emergency_stop()
        runtime.start()
        runtime.dispatch(LogicalInputEvent(control="R1C1"))

        self.assertEqual(len(dispatcher.events), 1)

    def test_runtime_defaults_to_dry_run_and_can_change_mode(self) -> None:
        runtime = ProfileRuntime(
            ProfileDocument(name="Test"),
            FakeInputSource(),
            RecordingDispatcher(),
        )

        self.assertEqual(runtime.mode, RuntimeMode.DRY_RUN)
        runtime.set_mode(RuntimeMode.EXECUTE)
        self.assertEqual(runtime.mode, RuntimeMode.EXECUTE)


if __name__ == "__main__":
    unittest.main()
