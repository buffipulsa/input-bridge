"""Portable profile data for layers, bindings, and user-authored scripts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PROFILE_SCHEMA_VERSION = 1


@dataclass
class ScriptDefinition:
    """Store a user-authored script without executing it."""

    script_id: str
    name: str
    source: str
    language: str = "python"


@dataclass
class BindingDefinition:
    """Map one logical control to an action definition."""

    control: str
    action_id: str
    executor: str = "host"
    layer_path: list[str] = field(default_factory=list)
    trigger: str = "press"
    script_id: str | None = None


@dataclass
class ConnectorDefinition:
    """Describe an optional application-specific bridge."""

    connector_id: str
    name: str
    entry_point: str
    version: str | None = None


@dataclass
class ProfileDocument:
    """Represent the portable contents of an Input Bridge profile.

    Parameters
    ----------
    name : str
        Human-readable profile name.
    layers : list[dict[str, Any]], optional
        Serialized layer hierarchy.
    bindings : list[BindingDefinition], optional
        Control-to-action assignments.
    scripts : list[ScriptDefinition], optional
        User-authored scripts included in the profile.
    connectors : list[ConnectorDefinition], optional
        Optional application-specific bridge metadata.
    """

    name: str
    layers: list[dict[str, Any]] = field(default_factory=list)
    bindings: list[BindingDefinition] = field(default_factory=list)
    scripts: list[ScriptDefinition] = field(default_factory=list)
    connectors: list[ConnectorDefinition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the profile in its versioned JSON representation."""

        return {
            "schema_version": PROFILE_SCHEMA_VERSION,
            "name": self.name,
            "layers": self.layers,
            "bindings": [asdict(binding) for binding in self.bindings],
            "scripts": [asdict(script) for script in self.scripts],
            "connectors": [asdict(connector) for connector in self.connectors],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfileDocument:
        """Create a profile from validated JSON-compatible data.

        Raises
        ------
        ValueError
            If the data is not a supported profile document.
        """

        if data.get("schema_version") != PROFILE_SCHEMA_VERSION:
            raise ValueError("unsupported or missing profile schema version")
        if not isinstance(data.get("name"), str) or not data["name"].strip():
            raise ValueError("profile name must be a non-empty string")

        return cls(
            name=data["name"],
            layers=_list_of_dicts(data.get("layers", []), "layers"),
            bindings=_build_items(data.get("bindings", []), BindingDefinition, "bindings"),
            scripts=_build_items(data.get("scripts", []), ScriptDefinition, "scripts"),
            connectors=_build_items(
                data.get("connectors", []), ConnectorDefinition, "connectors"
            ),
        )


def save_profile(profile: ProfileDocument, path: Path) -> None:
    """Write a profile document as UTF-8 JSON."""

    path.write_text(
        json.dumps(profile.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_profile(path: Path) -> ProfileDocument:
    """Read and validate a profile document from UTF-8 JSON."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("profile document must contain a JSON object")
    return ProfileDocument.from_dict(data)


def _list_of_dicts(value: object, field_name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{field_name} must be a list of objects")
    return value


def _build_items[T](
    value: object,
    item_type: type[T],
    field_name: str,
) -> list[T]:
    items = _list_of_dicts(value, field_name)
    try:
        return [item_type(**item) for item in items]
    except TypeError as error:
        raise ValueError(f"invalid {field_name} entry: {error}") from error
