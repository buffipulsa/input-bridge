"""Application-layer services for navigating and editing layer trees."""

from __future__ import annotations

from typing import Protocol

from ..domain.layers import Layer


class LayerBackend(Protocol):
    """Storage contract required by :class:`LayerService`."""

    def roots(self) -> list[Layer]:
        """Return the top-level layers."""

    def add_root(self, name: str) -> Layer:
        """Create and return a top-level layer."""

    def add_child(self, parent: Layer, name: str) -> Layer:
        """Create and return a child layer."""


class LayerService:
    """Coordinate layer navigation without depending on a UI toolkit."""

    def __init__(self, backend: LayerBackend) -> None:
        self.backend = backend
        self.navigation_stack: list[Layer] = []
        self.active_layer: Layer | None = None

    def visible_layers(self) -> list[Layer]:
        """Return the layers visible at the current navigation level."""

        if not self.navigation_stack:
            return self.backend.roots()
        return self.navigation_stack[-1].children

    def path(self) -> list[str]:
        """Return the current path as display names."""

        return ["Layers", *(layer.name for layer in self.navigation_stack)]

    def current_layer(self) -> Layer | None:
        """Return the layer currently being viewed, if any."""

        return self.navigation_stack[-1] if self.navigation_stack else None

    def enter(self, layer: Layer) -> None:
        """Enter a layer in the navigation view."""

        self.navigation_stack.append(layer)

    def go_back(self) -> None:
        """Move to the parent navigation level."""

        if self.navigation_stack:
            self.navigation_stack.pop()

    def navigate_to(self, depth: int) -> None:
        """Navigate to a breadcrumb depth."""

        self.navigation_stack = self.navigation_stack[:depth]

    def create_current_layer(self, name: str) -> Layer:
        """Create a layer at the current navigation level."""

        current = self.current_layer()
        if current is None:
            return self.backend.add_root(name)
        return self.backend.add_child(current, name)

    def set_active(self, layer: Layer) -> None:
        """Set the active layer without knowing how the UI represents it."""

        self.active_layer = layer
