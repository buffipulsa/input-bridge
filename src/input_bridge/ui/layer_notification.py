"""Transient on-screen feedback for layer and control activity."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QSettings,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def default_codebase_directory() -> Path:
    """Return the default user-owned directory for external scripts."""

    local_app_data = os.environ.get("LOCALAPPDATA")
    base_directory = (
        Path(local_app_data)
        if local_app_data
        else Path.home() / "AppData" / "Local"
    )
    return base_directory / "InputBridge" / "code"


def load_codebase_directory(settings: QSettings) -> Path:
    """Load the user-selected external script directory."""

    configured = str(settings.value("scripts/codebase_directory", "")).strip()
    return Path(configured).expanduser() if configured else default_codebase_directory()


def save_codebase_directory(settings: QSettings, directory: Path) -> None:
    """Persist the user-selected external script directory."""

    settings.setValue("scripts/codebase_directory", str(directory))
    settings.sync()


@dataclass(frozen=True)
class LayerNotificationPreferences:
    """User-configurable display preferences for the layer notification."""

    position: str = "bottom-right"
    duration_ms: int = 1400


NOTIFICATION_POSITIONS = (
    ("Top left", "top-left"),
    ("Top center", "top-center"),
    ("Top right", "top-right"),
    ("Bottom left", "bottom-left"),
    ("Bottom center", "bottom-center"),
    ("Bottom right", "bottom-right"),
)


def load_layer_notification_preferences(
    settings: QSettings,
) -> LayerNotificationPreferences:
    """Load notification preferences from Qt's per-user settings store."""

    position = str(settings.value("layer_notification/position", "bottom-right"))
    valid_positions = {value for _, value in NOTIFICATION_POSITIONS}
    if position not in valid_positions:
        position = "bottom-right"
    try:
        duration_ms = int(settings.value("layer_notification/duration_ms", 1400))
    except (TypeError, ValueError):
        duration_ms = 1400
    return LayerNotificationPreferences(
        position=position,
        duration_ms=max(300, min(duration_ms, 10_000)),
    )


def save_layer_notification_preferences(
    settings: QSettings,
    preferences: LayerNotificationPreferences,
) -> None:
    """Persist notification preferences in Qt's per-user settings store."""

    settings.setValue("layer_notification/position", preferences.position)
    settings.setValue("layer_notification/duration_ms", preferences.duration_ms)
    settings.sync()


def notification_geometry(
    available: QRect,
    size: QSize,
    position: str,
    margin: int = 24,
) -> QRect:
    """Return a screen position for a notification of ``size``."""

    x_center = available.left() + (available.width() - size.width()) // 2
    x_left = available.left() + margin
    x_right = available.right() - size.width() - margin + 1
    y_top = available.top() + margin
    y_bottom = available.bottom() - size.height() - margin + 1

    x = x_center if "center" in position else x_left if "left" in position else x_right
    y = y_top if position.startswith("top") else y_bottom
    return QRect(x, y, size.width(), size.height())


class LayerNotification(QWidget):
    """Show the active layer briefly above other windows."""

    def __init__(self, settings: QSettings) -> None:
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.settings = settings
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        self.label = QLabel()
        self.label.setObjectName("layerNotificationLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumWidth(180)
        self.label.setContentsMargins(18, 12, 18, 12)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.fade_animation.setDuration(260)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.finished.connect(self.hide)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)
        self.setStyleSheet(
            """
            QLabel#layerNotificationLabel {
                background: #242930;
                color: #ffffff;
                border: 1px solid #568bd1;
                border-radius: 8px;
                font-size: 13pt;
                font-weight: 600;
            }
            """
        )

    def show_layer(self, layer_path: str, command: str = "Unassigned") -> None:
        """Display the active layer and submitted command."""

        preferences = load_layer_notification_preferences(self.settings)
        self.label.setText(f"{layer_path}\n{command}")
        self.adjustSize()
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen is not None:
            self.setGeometry(
                notification_geometry(
                    screen.availableGeometry(),
                    self.sizeHint(),
                    preferences.position,
                )
            )
        self.fade_animation.stop()
        self.opacity_effect.setOpacity(1.0)
        self.show()
        self.raise_()
        self.hide_timer.start(preferences.duration_ms)

    def fade_out(self) -> None:
        """Begin fading the notification away."""

        self.fade_animation.start()


class LayerNotificationPreferencesDialog(QDialog):
    """Edit and persist the layer notification display preferences."""

    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(420)

        preferences = load_layer_notification_preferences(settings)
        self.position_combo = QComboBox()
        for label, value in NOTIFICATION_POSITIONS:
            self.position_combo.addItem(label, value)
        position_index = self.position_combo.findData(preferences.position)
        self.position_combo.setCurrentIndex(max(0, position_index))

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(300, 10_000)
        self.duration_spin.setSingleStep(100)
        self.duration_spin.setSuffix(" ms")
        self.duration_spin.setValue(preferences.duration_ms)

        self.codebase_edit = QLineEdit(str(load_codebase_directory(settings)))
        self.codebase_edit.setToolTip(
            "Folder containing user-authored Python scripts referenced by profiles."
        )
        browse_codebase_button = QToolButton()
        browse_codebase_button.setText("…")
        browse_codebase_button.setToolTip("Choose the user codebase folder.")
        browse_codebase_button.clicked.connect(self.browse_codebase)
        codebase_row = QHBoxLayout()
        codebase_row.addWidget(self.codebase_edit)
        codebase_row.addWidget(browse_codebase_button)

        section_title = QLabel("Layer notifications")
        section_title.setStyleSheet("font-weight: 600; font-size: 11pt;")
        help_button = QToolButton()
        help_button.setText("?")
        help_button.setFixedSize(24, 24)
        help_button.setToolTip("What are layer notifications?")
        help_button.setAccessibleName("Layer notification help")
        help_button.clicked.connect(self.show_notification_help)

        section_header = QHBoxLayout()
        section_header.addWidget(section_title)
        section_header.addWidget(help_button)
        section_header.addStretch()

        self.position_combo.setToolTip(
            "Choose which edge or corner of the screen displays the layer notification."
        )
        self.duration_spin.setToolTip(
            "Choose how long the notification stays visible before fading out."
        )

        form = QFormLayout()
        form.addRow("Screen position", self.position_combo)
        form.addRow("Display duration", self.duration_spin)
        form.addRow("User codebase", codebase_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(section_header)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def show_notification_help(self) -> None:
        """Explain the layer notification section."""

        QMessageBox.information(
            self,
            "Layer notifications",
            "Layer notifications briefly show the active layer and submitted "
            "command when a macropad control is pressed while the Input Bridge "
            "window is not focused. These settings control where the notification "
            "appears and how long it remains visible before fading out.",
        )

    def browse_codebase(self) -> None:
        """Choose the directory used to resolve external profile scripts."""

        selected = QFileDialog.getExistingDirectory(
            self,
            "Choose Input Bridge codebase",
            self.codebase_edit.text(),
        )
        if selected:
            self.codebase_edit.setText(selected)

    def accept(self) -> None:
        """Save preferences before closing the dialog."""

        save_layer_notification_preferences(
            self.settings,
            LayerNotificationPreferences(
                position=str(self.position_combo.currentData()),
                duration_ms=self.duration_spin.value(),
            ),
        )
        save_codebase_directory(
            self.settings,
            Path(self.codebase_edit.text()).expanduser(),
        )
        super().accept()
