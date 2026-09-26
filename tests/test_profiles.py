"""Tests for portable profile documents."""

import unittest

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


if __name__ == "__main__":
    unittest.main()
