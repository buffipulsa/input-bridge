"""Tests for portable profile documents."""

import unittest

from input_bridge.application.actions import (
    describe_profile_action,
    find_profile_binding,
)
from input_bridge.domain.profiles import (
    BindingDefinition,
    ConnectorDefinition,
    ProfileDocument,
    ScriptDefinition,
)


class ProfileDocumentTests(unittest.TestCase):
    """Verify profile serialization and validation contracts."""

    def test_profile_round_trips_through_dict(self) -> None:
        profile = ProfileDocument(
            name="Maya",
            layers=[{"name": "Global", "children": []}],
            bindings=[
                BindingDefinition(
                    control="R1C1",
                    action_id="run_script",
                    layer_path=["Global", "Modeling"],
                    script_id="open_spotify",
                )
            ],
            scripts=[
                ScriptDefinition(
                    script_id="open_spotify",
                    name="Open Spotify",
                    source="import os\\nos.startfile('spotify:')",
                )
            ],
            connectors=[
                ConnectorDefinition(
                    connector_id="maya",
                    name="Maya Bridge",
                    entry_point="input_bridge_maya",
                )
            ],
        )

        loaded = ProfileDocument.from_dict(profile.to_dict())
        self.assertEqual(loaded, profile)

    def test_missing_or_unknown_schema_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "schema version"):
            ProfileDocument.from_dict({"name": "Broken"})

        with self.assertRaisesRegex(ValueError, "schema version"):
            ProfileDocument.from_dict(
                {"schema_version": 999, "name": "Unsupported"}
            )

    def test_profile_name_must_be_non_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty"):
            ProfileDocument.from_dict(
                {"schema_version": 1, "name": "  "}
            )

    def test_describe_profile_action_reports_script_name(self) -> None:
        profile = ProfileDocument(
            name="Test",
            bindings=[
                BindingDefinition(
                    control="R1C1",
                    action_id="run_script",
                    script_id="open_spotify",
                )
            ],
            scripts=[
                ScriptDefinition(
                    script_id="open_spotify",
                    name="Open Spotify",
                    source="pass",
                )
            ],
        )

        self.assertEqual(
            describe_profile_action("R1C1", profile),
            "Script: Open Spotify",
        )

    def test_describe_profile_action_reports_unassigned_control(self) -> None:
        self.assertEqual(
            describe_profile_action("R1C1", ProfileDocument(name="Test")),
            "Unassigned",
        )

    def test_describe_profile_action_reports_missing_script(self) -> None:
        profile = ProfileDocument(
            name="Test",
            bindings=[
                BindingDefinition(
                    control="R1C1",
                    action_id="run_script",
                    script_id="missing",
                )
            ],
        )

        self.assertEqual(
            describe_profile_action("R1C1", profile),
            "Script: missing missing",
        )

    def test_layer_specific_binding_wins_over_parent_and_global(self) -> None:
        profile = ProfileDocument(
            name="Test",
            bindings=[
                BindingDefinition(
                    control="R1C1",
                    action_id="global_action",
                ),
                BindingDefinition(
                    control="R1C1",
                    action_id="maya_action",
                    layer_path=["Maya"],
                ),
                BindingDefinition(
                    control="R1C1",
                    action_id="modeling_action",
                    layer_path=["Maya", "Modeling"],
                ),
            ],
        )

        binding = find_profile_binding(
            "R1C1",
            profile,
            active_layer_path=["Maya", "Modeling"],
        )

        self.assertIsNotNone(binding)
        self.assertEqual(binding.action_id, "modeling_action")

    def test_global_binding_is_fallback_for_child_layer(self) -> None:
        profile = ProfileDocument(
            name="Test",
            bindings=[
                BindingDefinition(
                    control="R1C1",
                    action_id="global_action",
                )
            ],
        )

        self.assertEqual(
            describe_profile_action(
                "R1C1",
                profile,
                active_layer_path=["Maya", "Modeling"],
            ),
            "Action: global_action",
        )


if __name__ == "__main__":
    unittest.main()
