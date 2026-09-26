"""In-memory layer storage used by the initial UI and tests."""

from __future__ import annotations

from ..domain.layers import Layer, LayerTree


class InMemoryLayerBackend:
    """Store layers in memory using the domain layer tree."""

    def __init__(self) -> None:
        self.layer_tree = LayerTree()

    def roots(self) -> list[Layer]:
        """Return the top-level layers."""

        return self.layer_tree.roots

    def add_root(self, name: str) -> Layer:
        """Create and return a top-level layer."""

        return self.layer_tree.add_root(name)

    def add_child(self, parent: Layer, name: str) -> Layer:
        """Create and return a child layer."""

        return parent.add_child(name)

    def replace_roots(self, roots: list[Layer]) -> None:
        """Replace the in-memory root layers."""

        self.layer_tree.roots = roots
