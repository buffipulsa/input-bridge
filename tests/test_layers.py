"""Tests for the host-side layer hierarchy."""

import unittest

from input_bridge.domain.layers import Layer, LayerTree


class LayerTests(unittest.TestCase):
    """Verify layer naming and hierarchy rules."""

    def test_global_layer_is_locked(self) -> None:
        tree = LayerTree()

        with self.assertRaisesRegex(ValueError, "cannot contain child layers"):
            tree.roots[0].add_child("Maya")

        with self.assertRaisesRegex(ValueError, "cannot be renamed"):
            tree.roots[0].rename("Root", tree.roots)

    def test_child_names_are_unique_case_insensitively(self) -> None:
        maya = Layer("Maya")
        maya.add_child("Modeling")

        with self.assertRaisesRegex(ValueError, "already exists"):
            maya.add_child("modeling")

    def test_rename_trims_name_and_rejects_duplicate_sibling(self) -> None:
        tree = LayerTree()
        first = tree.add_root(" Layer 1 ")
        second = tree.add_root("Layer 2")

        first.rename(" Maya ", tree.roots)
        self.assertEqual(first.name, "Maya")

        with self.assertRaisesRegex(ValueError, "already exists"):
            second.rename("maya", tree.roots)

    def test_nested_tree_round_trips_and_preserves_global_lock(self) -> None:
        tree = LayerTree()
        maya = tree.add_root("Maya")
        modeling = maya.add_child("Modeling")
        modeling.add_child("Hard Surface")

        serialized = tree.to_list()
        restored = LayerTree.from_list(serialized)

        self.assertEqual(restored.roots[0].name, "Global")
        self.assertTrue(restored.roots[0].locked)
        self.assertEqual(restored.roots[1].children[0].children[0].name, "Hard Surface")

    def test_empty_serialized_tree_uses_default_global_layer(self) -> None:
        tree = LayerTree.from_list([])

        self.assertEqual([layer.name for layer in tree.roots], ["Global"])
        self.assertTrue(tree.roots[0].locked)


if __name__ == "__main__":
    unittest.main()
