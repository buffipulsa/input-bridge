"""Tests for the host-side layer hierarchy."""

import unittest

from input_bridge.application.layer_service import LayerService
from input_bridge.domain.layers import Layer, LayerTree
from input_bridge.infrastructure.memory_layer_backend import InMemoryLayerBackend


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

    def test_imported_application_profile_gets_global_root(self) -> None:
        tree = LayerTree.from_list([{"name": "Maya", "children": []}])

        self.assertEqual([layer.name for layer in tree.roots], ["Global", "Maya"])
        self.assertTrue(tree.roots[0].locked)

    def test_active_path_excludes_global_fallback_name(self) -> None:
        backend = InMemoryLayerBackend()
        maya = backend.add_root("Maya")
        modeling = backend.add_child(maya, "Modeling")
        service = LayerService(backend)

        self.assertEqual(service.active_path(), [])
        service.set_active(modeling)
        self.assertEqual(service.active_path(), ["Maya", "Modeling"])

    def test_global_is_edited_at_root_but_is_not_a_navigable_layer(self) -> None:
        backend = InMemoryLayerBackend()
        maya = backend.add_root("Maya")
        service = LayerService(backend)

        self.assertEqual([layer.name for layer in service.visible_layers()], ["Maya"])
        self.assertEqual(service.current_layer(), None)
        self.assertEqual(service.path(), ["Layers"])

        service.enter(maya)
        self.assertEqual(service.path(), ["Layers", "Maya"])
        self.assertEqual(service.active_path(), [])

    def test_cycle_active_walks_depth_first_and_wraps(self) -> None:
        backend = InMemoryLayerBackend()
        maya = backend.add_root("Maya")
        maya.add_child("Modeling")
        backend.add_root("VS Code")
        service = LayerService(backend)

        self.assertEqual(service.cycle_active(1).name, "Maya")
        self.assertEqual(service.cycle_active(1).name, "Modeling")
        self.assertEqual(service.cycle_active(1).name, "VS Code")
        self.assertEqual(service.cycle_active(1).name, "Maya")
        self.assertEqual(service.cycle_active(-1).name, "VS Code")

    def test_cycle_active_uses_global_when_no_layers_exist(self) -> None:
        service = LayerService(InMemoryLayerBackend())

        self.assertIsNone(service.cycle_active(1))
        self.assertEqual(service.active_path(), [])

    def test_selection_is_active_before_opening_layer(self) -> None:
        backend = InMemoryLayerBackend()
        maya = backend.add_root("Maya")
        backend.add_root("VS Code")
        service = LayerService(backend)

        self.assertEqual(service.cycle_selected(1), maya)
        self.assertEqual(service.active_path(), ["Maya"])

        self.assertIs(service.open_selected_layer(), maya)
        self.assertEqual(service.active_path(), ["Maya"])
        self.assertEqual([layer.name for layer in service.navigation_stack], ["Maya"])

    def test_k1_selection_cycles_between_global_and_application_layer(self) -> None:
        backend = InMemoryLayerBackend()
        maya = backend.add_root("Maya")
        service = LayerService(backend)

        self.assertIs(service.cycle_selected(1), maya)
        self.assertIs(service.cycle_selected(-1), backend.roots()[0])
        self.assertIs(service.open_selected_layer(), backend.roots()[0])
        self.assertEqual(service.active_path(), [])

    def test_k1_inside_layer_cycles_children_and_back_target(self) -> None:
        backend = InMemoryLayerBackend()
        maya = backend.add_root("Maya")
        modeling = maya.add_child("Modeling")
        backend.add_root("VS Code")
        service = LayerService(backend)

        service.cycle_selected(1)
        service.open_selected_layer()
        self.assertEqual([layer.name for layer in service.navigation_stack], ["Maya"])

        self.assertIs(service.cycle_selected(1), modeling)
        self.assertNotEqual(service.selected_layer.name, "VS Code")
        self.assertIsNone(service.cycle_selected(-1))
        self.assertTrue(service.selected_back)
        self.assertIsNone(service.open_selected_layer())
        self.assertEqual(service.active_path(), [])

    def test_k1_root_navigation_excludes_descendants(self) -> None:
        backend = InMemoryLayerBackend()
        layer1 = backend.add_root("Layer 1")
        layer2 = backend.add_root("Layer 2")
        backend.add_root("Layer 3")
        backend.add_root("Layer 4")
        layer2.add_child("Layer 1")
        layer2.add_child("Layer 2")
        layer2.add_child("Layer 3")
        service = LayerService(backend)

        selected = [service.cycle_selected(1) for _ in range(5)]

        self.assertEqual(
            [layer.name for layer in selected if layer is not None],
            [layer1.name, layer2.name, "Layer 3", "Layer 4", "Global"],
        )


if __name__ == "__main__":
    unittest.main()
