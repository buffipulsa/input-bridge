"""Tests for layer notification placement."""

import unittest

from PySide6.QtCore import QRect, QSize

from input_bridge.ui.layer_notification import notification_geometry


class LayerNotificationTests(unittest.TestCase):
    """Verify notification placement stays inside the available screen."""

    def test_top_left_position_uses_screen_margin(self) -> None:
        geometry = notification_geometry(
            QRect(100, 50, 1200, 800),
            QSize(200, 60),
            "top-left",
        )

        self.assertEqual(geometry.topLeft().x(), 124)
        self.assertEqual(geometry.topLeft().y(), 74)

    def test_bottom_right_position_uses_screen_margin(self) -> None:
        geometry = notification_geometry(
            QRect(100, 50, 1200, 800),
            QSize(200, 60),
            "bottom-right",
        )

        self.assertEqual(geometry.right(), 1275)
        self.assertEqual(geometry.bottom(), 825)

    def test_center_position_is_centered_on_screen(self) -> None:
        geometry = notification_geometry(
            QRect(100, 50, 1200, 800),
            QSize(200, 60),
            "bottom-center",
        )

        self.assertEqual(geometry.center().x(), 699)
        self.assertEqual(geometry.bottom(), 825)


if __name__ == "__main__":
    unittest.main()
