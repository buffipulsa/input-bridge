"""Small PySide6 editor for creating layers and sublayers."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..application.actions import (
    describe_profile_action,
    execute_profile_action,
    find_profile_binding,
)
from ..application.layer_service import LayerService
from ..application.runtime import LogicalInputEvent, ProfileRuntime, RuntimeMode
from ..domain.layers import Layer, LayerTree
from ..domain.profiles import (
    BindingDefinition,
    ProfileDocument,
    ScriptDefinition,
    load_profile,
    save_profile,
)
from ..infrastructure.memory_layer_backend import InMemoryLayerBackend
from ..infrastructure.observe_raw_input import RawInputEventSource
from .style import application_stylesheet

GLOBAL_PLACEHOLDER_ACTIONS = {
    "K1-CW": "Cycle application layer forward",
    "K1-CCW": "Cycle application layer backward",
    "K2-PRESS": "Return to default layer",
    "K3-PRESS": "Emergency stop",
}


class _RuntimeStatusDispatcher:
    """Update the editor when the prototype runtime receives an event."""

    def __init__(
        self,
        on_event: Callable[[LogicalInputEvent], None],
    ) -> None:
        self.on_event = on_event

    def dispatch(self, event: LogicalInputEvent, _profile: ProfileDocument) -> None:
        """Report an event without executing its configured action."""

        self.on_event(event)


class _RuntimeEventBridge(QObject):
    """Deliver runtime events safely to the Qt GUI thread."""

    event_received = Signal(object)


class _ActionExecutionBridge(QObject):
    """Deliver background action results safely to the Qt GUI thread."""

    result_received = Signal(object)


class _BackgroundActionExecutor:
    """Run one profile action at a time outside the Qt GUI thread."""

    def __init__(self, bridge: _ActionExecutionBridge) -> None:
        self._bridge = bridge
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="input-bridge-action",
        )

    def submit(
        self,
        event: LogicalInputEvent,
        profile: ProfileDocument,
        active_layer_path: tuple[str, ...],
    ) -> None:
        """Queue one action using a snapshot of the current profile."""

        profile_snapshot = deepcopy(profile)
        future = self._executor.submit(
            execute_profile_action,
            event.control,
            profile_snapshot,
            event.trigger,
            active_layer_path,
        )
        future.add_done_callback(
            lambda completed: self._report_result(event, completed)
        )

    def _report_result(
        self,
        event: LogicalInputEvent,
        future: Future[None],
    ) -> None:
        """Send the action result back to the Qt thread."""

        error = (
            RuntimeError("action was cancelled")
            if future.cancelled()
            else future.exception()
        )
        self._bridge.result_received.emit((event, error))

    def shutdown(self) -> None:
        """Cancel queued actions and release the executor."""

        self._executor.shutdown(wait=False, cancel_futures=True)


def default_profile_directory() -> Path:
    """Return the per-user Windows directory for Input Bridge profiles."""

    local_app_data = os.environ.get("LOCALAPPDATA")
    base_directory = (
        Path(local_app_data)
        if local_app_data
        else Path.home() / "AppData" / "Local"
    )
    return base_directory / "Input Bridge" / "profiles"


class LayerEditor(QMainWindow):
    """Display a UI-first prototype for layers and macro assignments."""

    def __init__(self, layer_service: LayerService | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Input Bridge — Layers")
        self.resize(1240, 760)
        self.build_menu_bar()

        self.layer_service = layer_service or LayerService(InMemoryLayerBackend())
        self.selected_control_name: str | None = None
        self.ui_assignments: dict[tuple[tuple[str, ...], str], str] = {}
        self.profile = ProfileDocument(name="Untitled")
        self.profile_path: Path | None = None
        self.selected_script_id: str | None = None
        self.control_buttons: dict[str, QPushButton] = {}
        self.runtime_source = RawInputEventSource()
        self.runtime_event_bridge = _RuntimeEventBridge(self)
        self.runtime_event_bridge.event_received.connect(self.show_runtime_event)
        self.action_execution_bridge = _ActionExecutionBridge(self)
        self.action_execution_bridge.result_received.connect(
            self.action_execution_finished
        )
        self.action_executor = _BackgroundActionExecutor(self.action_execution_bridge)
        self.runtime = ProfileRuntime(
            self.profile,
            self.runtime_source,
            _RuntimeStatusDispatcher(self.runtime_event_bridge.event_received.emit),
        )

        self.path_layout = QHBoxLayout()
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
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
        self.editing_label = QLabel("Editing layer: Global")
        self.active_label = QLabel("Runtime active layer: Global")
        layer_layout.addWidget(self.editing_label)
        layer_layout.addWidget(self.active_label)
        layer_layout.addWidget(new_layer_button)
        layer_layout.addWidget(set_active_button)

        runtime_panel = QFrame()
        runtime_panel.setFrameShape(QFrame.Shape.StyledPanel)
        runtime_layout = QVBoxLayout(runtime_panel)
        runtime_layout.addWidget(QLabel("Runtime prototype"))
        self.runtime_status_label = QLabel(
            "Stopped — DRY RUN — Windows Raw Input"
        )
        self.runtime_event_label = QLabel("Last event: —")
        runtime_layout.addWidget(self.runtime_status_label)
        runtime_layout.addWidget(self.runtime_event_label)
        runtime_layout.addWidget(QLabel("Execution history"))
        self.runtime_history = QListWidget()
        self.runtime_history.setMaximumHeight(120)
        runtime_layout.addWidget(self.runtime_history)
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.runtime_mode_combo = QComboBox()
        self.runtime_mode_combo.addItem("Dry Run", RuntimeMode.DRY_RUN)
        self.runtime_mode_combo.addItem("Execute Actions", RuntimeMode.EXECUTE)
        self.runtime_mode_combo.currentIndexChanged.connect(self.runtime_mode_changed)
        mode_layout.addWidget(self.runtime_mode_combo)
        runtime_layout.addLayout(mode_layout)
        runtime_buttons = QHBoxLayout()
        start_runtime_button = QPushButton("Start")
        start_runtime_button.clicked.connect(self.start_runtime)
        stop_runtime_button = QPushButton("Stop")
        stop_runtime_button.clicked.connect(self.stop_runtime)
        emergency_stop_button = QPushButton("Emergency Stop")
        emergency_stop_button.clicked.connect(self.emergency_stop_runtime)
        reset_emergency_button = QPushButton("Reset Stop")
        reset_emergency_button.clicked.connect(self.reset_emergency_stop)
        simulate_button = QPushButton("Simulate Selected")
        simulate_button.clicked.connect(self.simulate_selected_event)
        runtime_buttons.addWidget(start_runtime_button)
        runtime_buttons.addWidget(stop_runtime_button)
        runtime_buttons.addWidget(emergency_stop_button)
        runtime_buttons.addWidget(reset_emergency_button)
        runtime_buttons.addWidget(simulate_button)
        runtime_layout.addLayout(runtime_buttons)
        layer_layout.addWidget(runtime_panel)

        self.control_grid = self.build_control_grid()
        self.inspector = self.build_inspector()

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(layer_panel)
        main_splitter.addWidget(self.control_grid)
        main_splitter.addWidget(self.inspector)
        main_splitter.setSizes([240, 560, 380])

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(main_splitter)
        self.setCentralWidget(central_widget)
        self.new_layer_button = new_layer_button
        self.refresh_tree()
        self.refresh_control_labels()

    def build_menu_bar(self) -> None:
        """Create profile actions and placeholder application menus."""

        file_menu = self.menuBar().addMenu("File")
        open_profile_action = file_menu.addAction("Open Profile…")
        open_profile_action.triggered.connect(self.open_profile_dialog)
        save_profile_action = file_menu.addAction("Save Profile")
        save_profile_action.triggered.connect(self.save_profile_dialog)
        save_as_profile_action = file_menu.addAction("Save Profile As…")
        save_as_profile_action.triggered.connect(self.save_profile_as_dialog)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        for menu_name in ("Edit", "View", "Help"):
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
        knob_row.setSpacing(12)
        for knob in range(1, 4):
            knob_row.addWidget(self.knob_card(knob))
        layout.addLayout(knob_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
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
        card.setObjectName("knobCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(card)
        title = QLabel(f"K{knob}")
        title.setObjectName("knobTitle")
        layout.addWidget(title)
        for trigger in ("PRESS", "CW", "CCW"):
            control = f"K{knob}-{trigger}"
            label = {
                "PRESS": "Press",
                "CW": "Clockwise",
                "CCW": "Counter Clockwise",
            }[trigger]
            button = QPushButton(label)
            button.setObjectName("knobButton")
            button.setMinimumHeight(34)
            button.clicked.connect(
                lambda _checked=False, selected=control: self.select_control(selected)
            )
            self.control_buttons[control] = button
            layout.addWidget(button)
        return card

    def control_button(self, name: str) -> QPushButton:
        """Create a placeholder control button for the prototype UI."""

        button = QPushButton(f"{name}\nUnassigned")
        button.setObjectName("controlButton")
        button.setMinimumSize(110, 80)
        button.clicked.connect(lambda _checked=False, control=name: self.select_control(control))
        self.control_buttons[name] = button
        return button

    def build_inspector(self) -> QWidget:
        """Build the assignment and script tabs for the inspector."""

        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        outer_layout = QVBoxLayout(panel)

        title = QLabel("Inspector")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        outer_layout.addWidget(title)

        tabs = QTabWidget()

        assignment_panel = QWidget()
        assignment_layout = QVBoxLayout(assignment_panel)
        self.inspector_control = QLabel("Select a control")
        self.inspector_action = QLabel("Action: —")
        self.inspector_trigger = QLabel("Trigger: —")
        for label in (self.inspector_control, self.inspector_action, self.inspector_trigger):
            label.setWordWrap(True)
            assignment_layout.addWidget(label)

        assignment_layout.addSpacing(12)
        assignment_layout.addWidget(QLabel("Assignment"))
        self.assignment_combo = QComboBox()
        self.assignment_combo.addItem("No assignment", None)
        self.assignment_combo.addItem("Open Spotify", "Open Spotify")
        self.assignment_combo.currentIndexChanged.connect(
            self.assignment_selection_changed
        )
        assignment_layout.addWidget(self.assignment_combo)

        save_assignment_button = QPushButton("Save Assignment")
        save_assignment_button.clicked.connect(self.save_assignment)
        assignment_layout.addWidget(save_assignment_button)

        test_action_button = QPushButton("Test Action")
        test_action_button.clicked.connect(self.test_action)
        assignment_layout.addWidget(test_action_button)

        assignment_layout.addWidget(
            QLabel(
                "Assignments and scripts are currently stored in memory for this "
                "UI session."
            )
        )
        assignment_layout.addStretch()
        tabs.addTab(assignment_panel, "Assignment")

        script_panel = QWidget()
        script_layout = QVBoxLayout(script_panel)
        script_layout.addWidget(QLabel("Python source"))
        self.script_list = QListWidget()
        self.script_list.currentItemChanged.connect(self.select_script)
        script_layout.addWidget(self.script_list)

        self.script_name_edit = QLineEdit()
        self.script_name_edit.setPlaceholderText("Script name")
        script_layout.addWidget(self.script_name_edit)

        self.script_editor = QPlainTextEdit()
        self.script_editor.setPlaceholderText("Write Python source here...")
        script_layout.addWidget(self.script_editor)

        script_buttons = QHBoxLayout()
        new_script_button = QPushButton("New")
        new_script_button.clicked.connect(self.create_script)
        save_script_button = QPushButton("Save")
        save_script_button.clicked.connect(self.save_script)
        delete_script_button = QPushButton("Delete")
        delete_script_button.clicked.connect(self.delete_script)
        for button in (new_script_button, save_script_button, delete_script_button):
            script_buttons.addWidget(button)
        script_layout.addLayout(script_buttons)

        assign_script_button = QPushButton("Assign Selected Script")
        assign_script_button.clicked.connect(self.assign_selected_script)
        script_layout.addWidget(assign_script_button)

        script_layout.addWidget(
            QLabel(
                "Scripts are stored as source text in the profile. Execution "
                "requires an explicit Test Action or runtime execution path."
            )
        )
        tabs.addTab(script_panel, "Scripts")

        outer_layout.addWidget(tabs)
        self.refresh_script_list()
        return panel

    def select_control(self, control: str) -> None:
        """Display details for a selected control."""

        self.selected_control_name = control
        assignment = self.ui_assignments.get(self.assignment_key(control))
        action = self.assignment_label(
            assignment,
            fallback=GLOBAL_PLACEHOLDER_ACTIONS.get(control, "No assignment"),
        )
        trigger = {
            "CW": "Clockwise",
            "CCW": "Counter Clockwise",
        }.get(control.rsplit("-", 1)[-1], "Press")
        self.inspector_control.setText(f"Control: {control}")
        self.inspector_action.setText(f"Action: {action}")
        self.inspector_trigger.setText(f"Trigger: {trigger}")
        index = self.assignment_combo.findData(assignment)
        self.assignment_combo.setCurrentIndex(max(index, 0))
        self.refresh_control_highlight()

    def save_assignment(self) -> None:
        """Save the selected assignment in the current UI session."""

        self.save_current_assignment()
        if self.selected_control_name is not None:
            self.select_control(self.selected_control_name)

    def assignment_selection_changed(self, _index: int) -> None:
        """Store an assignment as soon as it is selected in the combo box."""

        self.save_current_assignment()

    def save_current_assignment(self) -> None:
        """Copy the current assignment control into session state."""

        if self.selected_control_name is None:
            return

        assignment = self.assignment_combo.currentData()
        key = self.assignment_key(self.selected_control_name)
        if assignment is None:
            self.ui_assignments.pop(key, None)
        else:
            self.ui_assignments[key] = str(assignment)
        self.refresh_control_labels()

    def assign_selected_script(self) -> None:
        """Assign the selected script to the selected control."""

        if self.selected_control_name is None:
            QMessageBox.information(
                self,
                "No control selected",
                "Select a pad control before assigning a script.",
            )
            return
        if self.selected_script_id is None:
            QMessageBox.information(
                self,
                "No script selected",
                "Select or create a script before assigning it.",
            )
            return
        if self.script_by_id(self.selected_script_id) is None:
            return
        self.ui_assignments[self.assignment_key(self.selected_control_name)] = (
            f"script:{self.selected_script_id}"
        )
        self.select_control(self.selected_control_name)
        self.refresh_control_labels()

    def assignment_label(self, assignment: str | None, fallback: str) -> str:
        """Return the display label for an assignment identifier."""

        if assignment is None:
            return fallback
        if assignment == "Open Spotify":
            return assignment
        if assignment.startswith("script:"):
            script_id = assignment.removeprefix("script:")
            script = self.script_by_id(script_id)
            return f"Script: {script.name}" if script is not None else "Missing script"
        return assignment

    def current_layer_path(self) -> tuple[str, ...]:
        """Return the path represented by the current layer view.

        The root view represents the Global fallback and therefore uses an
        empty path. Non-global assignments use paths such as
        ``("Maya", "Modeling")``.
        """

        return tuple(layer.name for layer in self.layer_service.navigation_stack)

    def active_layer_path(self) -> tuple[str, ...]:
        """Return the active layer path used by the runtime prototype."""

        return tuple(self.layer_service.active_path())

    def assignment_key(self, control: str) -> tuple[tuple[str, ...], str]:
        """Return the session-state key for a control in the current layer."""

        return self.current_layer_path(), control

    def script_by_id(self, script_id: str) -> ScriptDefinition | None:
        """Return a session-local script by identifier."""

        return next(
            (script for script in self.profile.scripts if script.script_id == script_id),
            None,
        )

    def refresh_assignment_options(self) -> None:
        """Refresh assignment choices from the current session-local scripts."""

        selected_assignment = (
            self.ui_assignments.get(self.assignment_key(self.selected_control_name))
            if self.selected_control_name is not None
            else None
        )
        self.assignment_combo.blockSignals(True)
        self.assignment_combo.clear()
        self.assignment_combo.addItem("No assignment", None)
        self.assignment_combo.addItem("Open Spotify", "Open Spotify")
        for script in self.profile.scripts:
            self.assignment_combo.addItem(
                f"Script: {script.name}",
                f"script:{script.script_id}",
            )
        index = self.assignment_combo.findData(selected_assignment)
        self.assignment_combo.setCurrentIndex(max(index, 0))
        self.assignment_combo.blockSignals(False)

    def refresh_script_list(self) -> None:
        """Show the scripts stored in the current session-local profile."""

        self.script_list.blockSignals(True)
        self.script_list.clear()
        selected_item: QListWidgetItem | None = None
        for script in self.profile.scripts:
            item = QListWidgetItem(script.name)
            item.setData(Qt.ItemDataRole.UserRole, script.script_id)
            self.script_list.addItem(item)
            if script.script_id == self.selected_script_id:
                selected_item = item
        if selected_item is not None:
            self.script_list.setCurrentItem(selected_item)
        elif self.profile.scripts:
            self.script_list.setCurrentRow(0)
            selected_item = self.script_list.item(0)
        else:
            self.selected_script_id = None
            self.script_name_edit.clear()
            self.script_editor.clear()
        self.script_list.blockSignals(False)
        if selected_item is not None:
            self.select_script(selected_item, None)
        self.refresh_assignment_options()

    def select_script(
        self,
        item: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        """Load a selected script into the editor."""

        if item is None:
            self.selected_script_id = None
            self.script_name_edit.clear()
            self.script_editor.clear()
            return

        script_id = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(script_id, str):
            return
        script = self.script_by_id(script_id)
        if script is None:
            return
        self.selected_script_id = script.script_id
        self.script_name_edit.setText(script.name)
        self.script_editor.setPlainText(script.source)

    def create_script(self) -> None:
        """Create a new blank script in the current session-local profile."""

        number = 1
        existing_ids = {script.script_id for script in self.profile.scripts}
        while f"script{number}" in existing_ids:
            number += 1
        script = ScriptDefinition(
            script_id=f"script{number}",
            name=f"script{number}",
            source="# Add Python code here.\n",
        )
        self.profile.scripts.append(script)
        self.selected_script_id = script.script_id
        self.refresh_script_list()

    def save_script(self) -> None:
        """Save the editor contents to the selected session-local script."""

        if self.selected_script_id is None:
            return
        script = self.script_by_id(self.selected_script_id)
        if script is None:
            return
        name = self.script_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Script not saved", "Script name cannot be empty.")
            return
        script.name = name
        script.source = self.script_editor.toPlainText()
        self.refresh_script_list()
        self.refresh_control_labels()
        if self.selected_control_name is not None:
            self.select_control(self.selected_control_name)

    def delete_script(self) -> None:
        """Delete the selected session-local script after confirmation."""

        if self.selected_script_id is None:
            return
        script = self.script_by_id(self.selected_script_id)
        if script is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete script",
            f"Delete script {script.name!r}?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.profile.scripts.remove(script)
        assignment = f"script:{script.script_id}"
        self.ui_assignments = {
            key: value
            for key, value in self.ui_assignments.items()
            if value != assignment
        }
        self.selected_script_id = None
        self.refresh_script_list()
        self.refresh_control_labels()
        if self.selected_control_name is not None:
            self.select_control(self.selected_control_name)

    def test_action(self) -> None:
        """Queue the selected R1C1 action for background execution."""

        if self.selected_control_name != "R1C1":
            QMessageBox.information(
                self,
                "Action not available",
                "The first test action is available for R1C1 only.",
            )
            return
        self.save_current_assignment()
        assignment = self.ui_assignments.get(self.assignment_key("R1C1"))
        if assignment is None:
            QMessageBox.information(
                self,
                "No action assigned",
                "Assign an action to R1C1 before testing it.",
            )
            return

        self.sync_profile_bindings()
        self.action_executor.submit(
            LogicalInputEvent(control="R1C1"),
            self.profile,
            tuple(self.active_layer_path()),
        )
        self.runtime_event_label.setText("Test Action: R1C1 → queued")
        self.record_runtime_history("R1C1 (press) → Test Action — queued")

    def start_runtime(self) -> None:
        """Start the read-only Windows Raw Input runtime."""

        try:
            self.runtime.start()
        except RuntimeError as error:
            QMessageBox.warning(self, "Runtime failed to start", str(error))
            return
        self.update_runtime_status("Running")

    def stop_runtime(self) -> None:
        """Stop the UI-only runtime prototype."""

        self.runtime.stop()
        try:
            self.runtime.stop()
        except RuntimeError as error:
            QMessageBox.warning(self, "Runtime failed to stop", str(error))
            return
        self.update_runtime_status("Stopped")

    def emergency_stop_runtime(self) -> None:
        """Stop runtime input and lock it until explicitly reset."""

        try:
            self.runtime.emergency_stop()
        except RuntimeError as error:
            QMessageBox.warning(self, "Emergency stop failed", str(error))
            return
        self.runtime_status_label.setText("EMERGENCY STOP — reset required")

    def reset_emergency_stop(self) -> None:
        """Clear the runtime emergency stop without starting input."""

        self.runtime.reset_emergency_stop()
        self.update_runtime_status("Stopped")

    def runtime_mode_changed(self, index: int) -> None:
        """Change runtime mode after confirming executable dispatch."""

        mode = self.runtime_mode_combo.itemData(index)
        if mode == RuntimeMode.EXECUTE:
            answer = QMessageBox.question(
                self,
                "Enable action execution",
                "Live macropad events may run profile scripts and commands. "
                "Enable execution mode?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.runtime_mode_combo.blockSignals(True)
                self.runtime_mode_combo.setCurrentIndex(0)
                self.runtime_mode_combo.blockSignals(False)
                return
        self.runtime.set_mode(mode)
        state = "Running" if self.runtime.is_running else "Stopped"
        self.update_runtime_status(state)

    def update_runtime_status(self, state: str) -> None:
        """Show runtime state and whether action execution is enabled."""

        mode = "DRY RUN" if self.runtime.mode == RuntimeMode.DRY_RUN else "EXECUTION ENABLED"
        self.runtime_status_label.setText(f"{state} — {mode} — Windows Raw Input")

    def simulate_selected_event(self) -> None:
        """Send the selected control through the runtime without executing it."""

        if self.selected_control_name is None:
            QMessageBox.information(
                self,
                "No control selected",
                "Select a button or encoder action first.",
            )
            return
        if not self.runtime.is_running:
            QMessageBox.information(
                self,
                "Runtime stopped",
                "Start the runtime prototype before simulating an event.",
            )
            return
        self.save_current_assignment()
        self.sync_profile_bindings()
        self.runtime.dispatch(LogicalInputEvent(control=self.selected_control_name))

    def show_runtime_event(
        self,
        event: LogicalInputEvent,
    ) -> None:
        """Display the latest event and dry-run action description."""

        self.sync_profile_bindings()
        active_layer_path = tuple(self.active_layer_path())
        if self.handle_builtin_layer_action(event, active_layer_path):
            return
        description = describe_profile_action(
            event.control,
            self.runtime.profile,
            event.trigger,
            active_layer_path,
        )
        self.runtime_event_label.setText(
            f"Last event: {event.control} ({event.trigger}) → {description}"
        )
        if description == "Unassigned":
            self.record_runtime_history(
                f"{event.control} ({event.trigger}) "
                f"[{self.layer_path_label(active_layer_path)}] "
                "→ unassigned — ignored"
            )
            return
        if self.runtime.mode != RuntimeMode.EXECUTE:
            self.record_runtime_history(
                f"{event.control} ({event.trigger}) [{self.layer_path_label(active_layer_path)}] "
                f"→ {description} — dry run"
            )
            return

        self.action_executor.submit(
            event,
            self.runtime.profile,
            active_layer_path,
        )
        self.runtime_event_label.setText(
            f"Last event: {event.control} ({event.trigger}) → "
            f"{description} [queued]"
        )
        self.record_runtime_history(
            f"{event.control} ({event.trigger}) [{self.layer_path_label(active_layer_path)}] "
            f"→ {description} — queued"
        )

    def action_execution_finished(self, result: object) -> None:
        """Display the result of an action executed by the worker."""

        event, error = result
        if error is not None:
            self.runtime_event_label.setText(
                f"Last event: {event.control} ({event.trigger}) → "
                f"action failed: {error}"
            )
            self.record_runtime_history(
                f"{event.control} ({event.trigger}) → action failed"
            )
            return
        self.runtime_event_label.setText(
            f"Last event: {event.control} ({event.trigger}) → action executed"
        )
        self.record_runtime_history(
            f"{event.control} ({event.trigger}) → action executed"
        )

    def handle_builtin_layer_action(
        self,
        event: LogicalInputEvent,
        active_layer_path: tuple[str, ...],
    ) -> bool:
        """Handle an unassigned built-in control for layer navigation."""

        if event.trigger != "press" and event.control not in {"K1-CW", "K1-CCW"}:
            return False
        if find_profile_binding(
            event.control,
            self.runtime.profile,
            event.trigger,
            active_layer_path,
        ) is not None:
            return False

        step = {"K1-CW": 1, "K1-CCW": -1}.get(event.control)
        if event.control == "K2-PRESS":
            if self.runtime.mode == RuntimeMode.DRY_RUN:
                self.record_runtime_history("K2-PRESS → Global — dry run")
                return True
            self.layer_service.set_global_active()
            self.refresh_tree()
            self.record_runtime_history("K2-PRESS → Global — active")
            return True
        if step is None:
            return False

        if self.runtime.mode == RuntimeMode.DRY_RUN:
            direction = "next" if step > 0 else "previous"
            self.record_runtime_history(
                f"{event.control} → {direction} layer — dry run"
            )
            return True

        layer = self.layer_service.cycle_active(step)
        self.refresh_tree()
        active_name = "/".join(self.active_layer_path()) if layer else "Global"
        self.record_runtime_history(f"{event.control} → {active_name} — active")
        return True

    def layer_path_label(self, layer_path: tuple[str, ...]) -> str:
        """Format a layer path for the local execution history."""

        return "/".join(layer_path) if layer_path else "Global"

    def record_runtime_history(self, message: str) -> None:
        """Add one bounded, metadata-only entry to the execution history."""

        timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
        self.runtime_history.insertItem(0, QListWidgetItem(f"{timestamp}  {message}"))
        while self.runtime_history.count() > 50:
            self.runtime_history.takeItem(self.runtime_history.count() - 1)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Stop input and release the background action executor."""

        self.runtime.stop()
        self.action_executor.shutdown()
        super().closeEvent(event)

    def sync_profile_bindings(self) -> None:
        """Copy the UI's current script assignments into the profile model."""

        bindings: list[BindingDefinition] = []
        for (layer_path, control), assignment in self.ui_assignments.items():
            if assignment == "Open Spotify":
                bindings.append(
                    BindingDefinition(
                        control=control,
                        action_id="open_spotify",
                        layer_path=list(layer_path),
                    )
                )
            elif assignment.startswith("script:"):
                bindings.append(
                    BindingDefinition(
                        control=control,
                        action_id="run_script",
                        layer_path=list(layer_path),
                        script_id=assignment.removeprefix("script:"),
                    )
                )
        self.profile.bindings = bindings

    def sync_profile_layers(self) -> None:
        """Copy the current layer tree into the profile model."""

        self.profile.layers = [
            layer.to_dict() for layer in self.layer_service.backend.roots()
        ]

    def restore_profile_layers(self) -> None:
        """Restore the profile layer tree into the layer service."""

        roots = LayerTree.from_list(self.profile.layers).roots
        self.layer_service.replace_roots(roots)

    def restore_profile_bindings(self) -> None:
        """Copy profile bindings into the UI assignment state."""

        self.ui_assignments = {}
        for binding in self.profile.bindings:
            key = (tuple(binding.layer_path), binding.control)
            if binding.action_id == "run_script" and binding.script_id is not None:
                self.ui_assignments[key] = f"script:{binding.script_id}"
            elif binding.action_id == "open_spotify":
                self.ui_assignments[key] = "Open Spotify"

    def save_profile_as_dialog(self) -> None:
        """Choose a path and save the current profile as JSON."""

        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Input Bridge Profile",
            str(
                self.profile_path
                or default_profile_directory() / "profile.input-bridge.json"
            ),
            "Input Bridge profiles (*.json);;All files (*.*)",
        )
        if filename:
            self.profile_path = Path(filename)
            self.save_profile()

    def save_profile_dialog(self) -> None:
        """Save the current profile, prompting for a path when necessary."""

        if self.profile_path is None:
            self.save_profile_as_dialog()
        else:
            self.save_profile()

    def save_profile(self) -> None:
        """Write the current UI profile to its selected JSON path."""

        if self.profile_path is None:
            return
        self.save_current_assignment()
        self.sync_profile_layers()
        self.sync_profile_bindings()
        try:
            self.profile_path.parent.mkdir(parents=True, exist_ok=True)
            save_profile(self.profile, self.profile_path)
        except OSError as error:
            QMessageBox.warning(self, "Profile not saved", str(error))
            return
        self.statusBar().showMessage(f"Profile saved: {self.profile_path}", 3000)

    def open_profile_dialog(self) -> None:
        """Choose and load a JSON profile into the editor."""

        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Open Input Bridge Profile",
            str(self.profile_path or default_profile_directory()),
            "Input Bridge profiles (*.json);;All files (*.*)",
        )
        if filename:
            self.load_profile(Path(filename))

    def load_profile(self, path: Path) -> None:
        """Load a profile from disk and refresh the editor state."""

        try:
            self.profile = load_profile(path)
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.warning(self, "Profile not loaded", str(error))
            return
        self.profile_path = path
        self.runtime.profile = self.profile
        self.restore_profile_layers()
        self.restore_profile_bindings()
        self.refresh_script_list()
        self.refresh_control_labels()
        if self.selected_control_name is not None:
            self.select_control(self.selected_control_name)
        self.statusBar().showMessage(f"Profile loaded: {path}", 3000)

    def refresh_control_labels(self) -> None:
        """Show the current assignment on each control button."""

        for control, button in self.control_buttons.items():
            assignment = self.ui_assignments.get(self.assignment_key(control))
            label = self.assignment_label(assignment, "No assignment")
            button.setText(f"{control}\n{label}")

    def refresh_control_highlight(self) -> None:
        """Highlight the currently selected control with a blue border."""

        for control, button in self.control_buttons.items():
            if control == self.selected_control_name:
                button.setStyleSheet(
                    "QPushButton { border: 2px solid #3b82f6; "
                    "border-radius: 8px; }"
                )
            else:
                button.setStyleSheet("")

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
        editing_path = self.current_layer_path()
        editing_name = "/".join(editing_path) if editing_path else "Global"
        active_path = self.active_layer_path()
        active_name = "/".join(active_path) if active_path else "Global"
        self.editing_label.setText(f"Editing layer: {editing_name}")
        self.active_label.setText(f"Runtime active layer: {active_name}")
        self.refresh_control_labels()
        if self.selected_control_name is not None:
            self.select_control(self.selected_control_name)

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
            if index == 0:
                root_label = QLabel(name)
                root_label.setObjectName("breadcrumbRoot")
                self.path_layout.addWidget(root_label)
            else:
                path_button = QPushButton(name)
                path_button.setObjectName("breadcrumbButton")
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
        if layer is self.layer_service.active_layer:
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
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
        active_path = self.active_layer_path()
        active_name = "/".join(active_path) if active_path else "Global"
        self.active_label.setText(f"Runtime active layer: {active_name}")


def main() -> int:
    """Run the layer editor application."""

    app = QApplication(sys.argv)
    app.setStyleSheet(application_stylesheet())
    window = LayerEditor()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
