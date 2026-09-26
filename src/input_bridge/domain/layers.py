"""In-memory hierarchy for host-side macropad layers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Layer:
    """Represent one layer or sublayer in the layer hierarchy.

    Parameters
    ----------
    name : str
        Display name for the layer.
    children : list[Layer], optional
        Direct child layers.
    locked : bool, default=False
        Whether this layer is prevented from containing children.
    """

    name: str
    children: list[Layer] = field(default_factory=list)
    locked: bool = False

    def rename(self, name: str, siblings: list[Layer]) -> None:
        """Rename this layer while preserving sibling name uniqueness.

        Parameters
        ----------
        name : str
            New display name.
        siblings : list[Layer]
            Layers at the same hierarchy level as this layer.

        Raises
        ------
        ValueError
            If this layer is locked, the name is empty, or a sibling already
            uses the name.
        """

        if self.locked:
            raise ValueError(f"layer {self.name!r} cannot be renamed")

        clean_name = name.strip()
        if not clean_name:
            raise ValueError("layer name cannot be empty")
        if any(
            sibling is not self and sibling.name.casefold() == clean_name.casefold()
            for sibling in siblings
        ):
            raise ValueError(f"a sibling named {clean_name!r} already exists")

        self.name = clean_name

    def add_child(self, name: str) -> Layer:
        """Add and return a uniquely named direct child.

        Parameters
        ----------
        name : str
            Display name for the new child.

        Returns
        -------
        Layer
            The newly created child layer.

        Raises
        ------
        ValueError
            If the name is empty or already exists among direct children.
        """

        if self.locked:
            raise ValueError(f"layer {self.name!r} cannot contain child layers")

        clean_name = name.strip()
        if not clean_name:
            raise ValueError("layer name cannot be empty")
        if any(child.name.casefold() == clean_name.casefold() for child in self.children):
            raise ValueError(f"a child named {clean_name!r} already exists")

        child = Layer(clean_name)
        self.children.append(child)
        return child


@dataclass
class LayerTree:
    """Own the top-level layers shown by the layer editor."""

    roots: list[Layer] = field(default_factory=lambda: [Layer("Global", locked=True)])

    def add_root(self, name: str) -> Layer:
        """Add and return a uniquely named top-level layer."""

        clean_name = name.strip()
        if not clean_name:
            raise ValueError("layer name cannot be empty")
        if any(root.name.casefold() == clean_name.casefold() for root in self.roots):
            raise ValueError(f"a layer named {clean_name!r} already exists")

        root = Layer(clean_name)
        self.roots.append(root)
        return root
