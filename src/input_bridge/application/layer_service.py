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
        self.selected_layer: Layer | None = None
        self.selected_back = False

    def visible_layers(self) -> list[Layer]:
        """Return the layers visible at the current navigation level."""

        if not self.navigation_stack:
            # Global is the reserved empty-path fallback scope.  It is edited
            # from the root view, but it is not itself a navigable application
            # layer.  Keeping it out of this list prevents a root application
            # layer from being mistaken for a global assignment in the UI.
            return [
                layer
                for layer in self.backend.roots()
                if layer.name.casefold() != "global"
            ]
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
        self.selected_layer = layer
        self.selected_back = False

    def set_global_active(self) -> None:
        """Select the Global fallback layer."""

        self.active_layer = None
        self.selected_layer = self._global_layer()
        self.selected_back = False

    def select_back(self) -> None:
        """Select the parent navigation target for K1."""

        if self.navigation_stack:
            self.selected_back = True
            self.selected_layer = None

    def cycle_selected(self, step: int) -> Layer | None:
        """Move the pending layer selection without activating it.

        Parameters
        ----------
        step : int
            Direction and distance to move. Positive values move forward;
            negative values move backward.

        Returns
        -------
        Layer or None
            The newly selected layer, or ``None`` when no selectable layers
            exist.
        """

        if step == 0:
            return self.selected_layer

        layers = self._cycle_layers()
        if self.navigation_stack:
            target_count = len(layers) + 1  # ``..`` plus child layers.
            if self.selected_back:
                index = 0
            elif self.selected_layer in layers:
                index = layers.index(self.selected_layer) + 1
            else:
                index = 0
            index = (index + step) % target_count
            if index == 0:
                self.selected_layer = None
                self.selected_back = True
                return None
            self.selected_layer = layers[index - 1]
        else:
            if not layers:
                self.selected_layer = None
                return None
            if self.selected_back:
                index = 0 if step > 0 else len(layers) - 1
            elif self.selected_layer not in layers:
                global_layer = self._global_layer()
                if global_layer in layers:
                    index = (layers.index(global_layer) + step) % len(layers)
                else:
                    index = 0 if step > 0 else len(layers) - 1
            else:
                index = (layers.index(self.selected_layer) + step) % len(layers)
            self.selected_layer = layers[index]
        self.selected_back = False
        if self.selected_layer is self._global_layer():
            self.active_layer = None
        else:
            self.active_layer = self.selected_layer
        return self.selected_layer

    def open_selected_layer(self) -> Layer | None:
        """Activate the layer currently selected by the K1 encoder."""

        if self.selected_back and self.navigation_stack:
            self.navigation_stack.pop()
            parent = self.navigation_stack[-1] if self.navigation_stack else None
            self.selected_back = False
            if parent is None:
                self.set_global_active()
            else:
                self.set_active(parent)
            return parent

        if self.selected_layer not in self._cycle_layers():
            return None
        if self.selected_layer is self._global_layer():
            self.set_global_active()
            self.navigation_stack = []
            return self.selected_layer
        self.active_layer = self.selected_layer
        self.navigation_stack = self._layer_path(self.active_layer)
        return self.active_layer

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

        layers = self._selectable_layers()
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
        self.selected_layer = None
        self.selected_back = False

    def _selectable_layers(self) -> list[Layer]:
        """Return unlocked layers in deterministic depth-first order."""

        layers: list[Layer] = []

        def collect(items: list[Layer]) -> None:
            for layer in items:
                if not layer.locked:
                    layers.append(layer)
                    collect(layer.children)

        collect(self.backend.roots())
        return layers

    def _global_layer(self) -> Layer | None:
        """Return the reserved Global layer, if the backend contains it."""

        return next(
            (
                layer
                for layer in self.backend.roots()
                if layer.name.casefold() == "global"
            ),
            None,
        )

    def _cycle_layers(self) -> list[Layer]:
        """Return the current-level targets available to K1 navigation."""

        if self.navigation_stack:
            return [
                layer
                for layer in self.navigation_stack[-1].children
                if not layer.locked
            ]

        global_layer = self._global_layer()
        root_layers = [
            layer
            for layer in self.backend.roots()
            if not layer.locked and layer.name.casefold() != "global"
        ]
        return ([global_layer] if global_layer is not None else []) + root_layers

    def _layer_path(self, target: Layer) -> list[Layer]:
        """Return the object path from a root to ``target``."""

        def find_path(items: list[Layer], parents: list[Layer]) -> list[Layer] | None:
            for layer in items:
                path = [*parents, layer]
                if layer is target:
                    return path
                result = find_path(layer.children, path)
                if result is not None:
                    return result
            return None

        return find_path(self.backend.roots(), []) or []
