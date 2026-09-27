"""Application-layer services for navigating and editing layer trees."""

from __future__ import annotations

from typing import Protocol

from ..domain.layers import Layer


class LayerBackend(Protocol):
    """Storage contract required by :class:`LayerService`."""

    def roots(self) -> list[Layer]:
        """Return the top-level layers."""

        ...

    def add_root(self, name: str) -> Layer:
        """Create and return a top-level layer."""

        ...

    def add_child(self, parent: Layer, name: str) -> Layer:
        """Create and return a child layer."""

        ...

    def replace_roots(self, roots: list[Layer]) -> None:
        """Replace the top-level layers."""

        ...


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

    def set_global_active(self) -> None:
        """Select the Global fallback layer."""

        self.active_layer = None

    def cycle_active(self, step: int) -> Layer | None:
        """Move the active layer through non-Global layers.

        Parameters
        ----------
        step : int
            Direction and distance to move. Positive values move forward;
            negative values move backward.

        Returns
        -------
        Layer or None
            The newly active layer, or ``None`` when no selectable layers
            exist.
        """

        if step == 0:
            return self.active_layer

        layers: list[Layer] = []

        def collect(items: list[Layer]) -> None:
            for layer in items:
                if not layer.locked:
                    layers.append(layer)
                    collect(layer.children)

        collect(self.backend.roots())
        if not layers:
            self.set_global_active()
            return None

        if self.active_layer not in layers:
            index = 0 if step > 0 else len(layers) - 1
        else:
            index = (layers.index(self.active_layer) + step) % len(layers)
        self.active_layer = layers[index]
        return self.active_layer

    def active_path(self) -> list[str]:
        """Return the active layer path used for action resolution.

        The locked Global layer represents the empty fallback path, so it is
        returned as an empty list. If no active layer has been selected, the
        same empty fallback path is returned.
        """

        if self.active_layer is None:
            return []

        def find_path(layer: Layer, parents: list[str]) -> list[str] | None:
            path = [*parents, layer.name]
            if layer is self.active_layer:
                return path
            for child in layer.children:
                result = find_path(child, path)
                if result is not None:
                    return result
            return None

        for root in self.backend.roots():
            result = find_path(root, [])
            if result is not None:
                return [] if result == ["Global"] else result
        return []

    def replace_roots(self, roots: list[Layer]) -> None:
        """Replace the layer tree and reset navigation state."""

        self.backend.replace_roots(roots)
        self.navigation_stack = []
        self.active_layer = None
