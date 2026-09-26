"""Small PySide6 editor for creating layers and sublayers."""

from __future__ import annotations

import sys

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..application.actions import execute_action
from ..application.layer_service import LayerService
from ..domain.layers import Layer
from ..infrastructure.memory_layer_backend import InMemoryLayerBackend

GLOBAL_PLACEHOLDER_ACTIONS = {
    "K1-CW": "Cycle application layer forward",
    "K1-CCW": "Cycle application layer backward",
    "K2-PRESS": "Return to default layer",
    "K3-PRESS": "Emergency stop",
}


class LayerEditor(QMainWindow):
    """Display a UI-first prototype for layers and macro assignments."""

    def __init__(self, layer_service: LayerService | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Input Bridge — Layers")
        self.resize(1120, 700)
        self.build_menu_bar()

        self.layer_service = layer_service or LayerService(InMemoryLayerBackend())
        self.selected_control_name: str | None = None
        self.ui_assignments: dict[str, str] = {}

        self.path_layout = QHBoxLayout()
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("Layers")
        self.tree_widget.itemDoubleClicked.connect(self.enter_layer)
        self.tree_widget.itemChanged.connect(self.rename_layer)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_tree_context_menu)

        new_layer_button = QPushButton("New Layer")
        new_layer_button.clicked.connect(self.create_layer)
        set_active_button = QPushButton("Set Active")
        set_active_button.clicked.connect(self.set_active)

        layer_panel = QWidget()
        layer_layout = QVBoxLayout(layer_panel)
        layer_layout.addLayout(self.path_layout)
        layer_layout.addWidget(self.tree_widget)
        self.active_label = QLabel("Active layer: Global")
        layer_layout.addWidget(self.active_label)
        layer_layout.addWidget(new_layer_button)
        layer_layout.addWidget(set_active_button)

        self.control_grid = self.build_control_grid()
        self.inspector = self.build_inspector()

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(layer_panel)
        main_splitter.addWidget(self.control_grid)
        main_splitter.addWidget(self.inspector)
        main_splitter.setSizes([240, 560, 280])

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(main_splitter)
        self.setCentralWidget(central_widget)
        self.new_layer_button = new_layer_button
        self.refresh_tree()

    def build_menu_bar(self) -> None:
        """Create placeholder application menus for the prototype UI."""

        for menu_name in ("File", "Edit", "View", "Help"):
            menu = self.menuBar().addMenu(menu_name)
            placeholder = menu.addAction("Coming soon")
            placeholder.setEnabled(False)

    def build_control_grid(self) -> QWidget:
        """Build the placeholder grid and encoder controls."""

        panel = QWidget()
        layout = QVBoxLayout(panel)
        title = QLabel("Controls")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        knob_row = QHBoxLayout()
        for knob in range(1, 4):
            knob_row.addWidget(self.knob_card(knob))
        layout.addLayout(knob_row)

        grid = QGridLayout()
        for row in range(4):
            for column in range(4):
                control_name = f"R{row + 1}C{column + 1}"
                grid.addWidget(self.control_button(control_name), row, column)
        layout.addLayout(grid)
        layout.addStretch()
        return panel

    def knob_card(self, knob: int) -> QWidget:
        """Create a placeholder card for one encoder and its triggers."""

        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(card)
        layout.addWidget(QLabel(f"K{knob}"))
        for trigger in ("PRESS", "CW", "CCW"):
            control = f"K{knob}-{trigger}"
            label = {
                "PRESS": "Press",
                "CW": "Clockwise",
                "CCW": "Counter Clockwise",
            }[trigger]
            button = QPushButton(label)
            button.clicked.connect(
                lambda _checked=False, selected=control: self.select_control(selected)
            )
            layout.addWidget(button)
        return card

    def control_button(self, name: str) -> QPushButton:
        """Create a placeholder control button for the prototype UI."""

        button = QPushButton(f"{name}\nUnassigned")
        button.setMinimumSize(110, 80)
        button.clicked.connect(lambda _checked=False, control=name: self.select_control(control))
        return button

    def build_inspector(self) -> QWidget:
        """Build the placeholder assignment inspector."""

        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)

        title = QLabel("Inspector")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.inspector_control = QLabel("Select a control")
        self.inspector_action = QLabel("Action: —")
        self.inspector_trigger = QLabel("Trigger: —")
        for label in (self.inspector_control, self.inspector_action, self.inspector_trigger):
            label.setWordWrap(True)
            layout.addWidget(label)

        layout.addSpacing(12)
        layout.addWidget(QLabel("Assignment"))
        self.assignment_combo = QComboBox()
        self.assignment_combo.addItems(["Unassigned", "Open Spotify"])
        layout.addWidget(self.assignment_combo)

        save_assignment_button = QPushButton("Save Assignment")
        save_assignment_button.clicked.connect(self.save_assignment)
        layout.addWidget(save_assignment_button)

        test_action_button = QPushButton("Test Action")
        test_action_button.clicked.connect(self.test_action)
        layout.addWidget(test_action_button)

        layout.addWidget(
            QLabel(
                "Assignments are currently stored in memory for this UI session."
            )
        )
        layout.addStretch()
        return panel

    def select_control(self, control: str) -> None:
        """Display placeholder details for a selected control."""

        self.selected_control_name = control
        action = self.ui_assignments.get(
            control, GLOBAL_PLACEHOLDER_ACTIONS.get(control, "Unassigned")
        )
        trigger = {
            "CW": "Clockwise",
            "CCW": "Counter Clockwise",
        }.get(control.rsplit("-", 1)[-1], "Press")
        self.inspector_control.setText(f"Control: {control}")
        self.inspector_action.setText(f"Action: {action}")
        self.inspector_trigger.setText(f"Trigger: {trigger}")
        self.assignment_combo.setCurrentText(action)

    def save_assignment(self) -> None:
        """Save the selected placeholder assignment in the current UI session."""

        if self.selected_control_name is None:
            return

        assignment = self.assignment_combo.currentText()
        if assignment == "Unassigned":
            self.ui_assignments.pop(self.selected_control_name, None)
        else:
            self.ui_assignments[self.selected_control_name] = assignment
        self.select_control(self.selected_control_name)

    def test_action(self) -> None:
        """Test the supported Spotify assignment for the selected control."""

        if self.selected_control_name != "R1C1":
            QMessageBox.information(
                self,
                "Action not available",
                "The first test action is available for R1C1 only.",
            )
            return
        if self.ui_assignments.get("R1C1") != "Open Spotify":
            QMessageBox.information(
                self,
                "No action assigned",
                "Assign Open Spotify to R1C1 before testing it.",
            )
            return

        try:
            execute_action("R1C1")
        except (OSError, RuntimeError) as error:
            QMessageBox.warning(self, "Action failed", str(error))

    def refresh_tree(self) -> None:
        """Show the direct children of the current layer view."""

        self.tree_widget.clear()
        visible_layers = self.layer_service.visible_layers()
        if self.layer_service.current_layer() is not None:
            parent_item = QTreeWidgetItem([".."])
            parent_item.setData(0, Qt.ItemDataRole.UserRole, "__parent__")
            self.tree_widget.addTopLevelItem(parent_item)
        for layer in visible_layers:
            self.add_layer_item(None, layer)

        self.refresh_path()
        current_layer = self.layer_service.current_layer()
        self.new_layer_button.setEnabled(current_layer is None or not current_layer.locked)

    def show_tree_context_menu(self, position: QPoint) -> None:
        """Show actions for the current tree view location."""

        menu = QMenu(self.tree_widget)
        item = self.tree_widget.itemAt(position)
        layer = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        if isinstance(layer, Layer) and not layer.locked:
            self.tree_widget.setCurrentItem(item)
            rename_action = menu.addAction("Rename Layer")
            rename_action.triggered.connect(
                lambda: self.tree_widget.editItem(item, 0)
            )
            menu.addSeparator()

        create_action = menu.addAction("Create Layer")
        create_action.setEnabled(self.new_layer_button.isEnabled())
        create_action.triggered.connect(self.create_layer)
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    def refresh_path(self) -> None:
        """Rebuild the clickable layer path above the tree view."""

        while self.path_layout.count():
            layout_item = self.path_layout.takeAt(0)
            widget = layout_item.widget()
            if widget is not None:
                widget.deleteLater()

        path = self.layer_service.path()
        for index, name in enumerate(path):
            if index:
                self.path_layout.addWidget(QLabel("/"))
            path_button = QPushButton(name)
            path_button.setFlat(True)
            path_button.clicked.connect(
                lambda _checked=False, depth=index: self.navigate_to(depth)
            )
            self.path_layout.addWidget(path_button)
        self.path_layout.addStretch()

    def add_layer_item(
        self,
        parent_item: QTreeWidgetItem | None,
        layer: Layer,
    ) -> None:
        """Add one layer and its descendants to the Qt tree."""

        item = QTreeWidgetItem([layer.name])
        item.setData(0, Qt.ItemDataRole.UserRole, layer)
        if not layer.locked:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        if parent_item is None:
            self.tree_widget.addTopLevelItem(item)
        else:
            parent_item.addChild(item)

    def enter_layer(self, item: QTreeWidgetItem, _column: int) -> None:
        """Enter the layer represented by a double-clicked tree item."""

        if item.data(0, Qt.ItemDataRole.UserRole) == "__parent__":
            self.go_back()
            return

        layer = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(layer, Layer) or layer.locked:
            return
        self.layer_service.enter(layer)
        self.refresh_tree()

    def go_back(self) -> None:
        """Return to the parent layer view."""

        self.layer_service.go_back()
        self.refresh_tree()

    def navigate_to(self, depth: int) -> None:
        """Navigate to a layer represented by a breadcrumb depth."""

        self.layer_service.navigate_to(depth)
        self.refresh_tree()

    def selected_layer(self) -> Layer | None:
        """Return the currently selected layer, if any."""

        item = self.tree_widget.currentItem()
        if item is None:
            return None
        layer = item.data(0, Qt.ItemDataRole.UserRole)
        return layer if isinstance(layer, Layer) else None

    def next_layer_name(self) -> str:
        """Return the next available automatic layer name."""

        existing_names = {
            layer.name.casefold() for layer in self.layer_service.visible_layers()
        }
        number = 1
        while f"layer{number}".casefold() in existing_names:
            number += 1
        return f"layer{number}"

    def create_layer(self) -> None:
        """Create a layer at the current navigation level."""

        name = self.next_layer_name()
        try:
            layer = self.layer_service.create_current_layer(name)
        except ValueError as error:
            QMessageBox.warning(self, "Layer not created", str(error))
            return
        self.refresh_tree()
        for index in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(index)
            if item.data(0, Qt.ItemDataRole.UserRole) is layer:
                self.tree_widget.setCurrentItem(item)
                break

    def rename_layer(self, item: QTreeWidgetItem, _column: int) -> None:
        """Validate and store a layer name edited in the tree."""

        layer = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(layer, Layer):
            return
        try:
            layer.rename(item.text(0), self.layer_service.visible_layers())
        except ValueError as error:
            QMessageBox.warning(self, "Layer not renamed", str(error))
            self.refresh_tree()
        else:
            self.refresh_path()

    def set_active(self) -> None:
        """Mark the selected layer as active in the UI."""

        layer = self.selected_layer()
        if layer is None:
            return
        self.layer_service.set_active(layer)
        self.active_label.setText(f"Active layer: {layer.name}")


def main() -> int:
    """Run the layer editor application."""

    app = QApplication(sys.argv)
    window = LayerEditor()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
