"""Tests for normalized macropad keyboard sequences."""

import unittest

from input_bridge.domain.event_normalizer import MacropadEventNormalizer


class MacropadEventNormalizerTests(unittest.TestCase):
    """Verify logical controls emitted from modifier-qualified keys."""

    def test_k1_direction_mapping_matches_physical_capture(self) -> None:
        normalizer = MacropadEventNormalizer()
        normalizer.feed(0x10, 0)
        normalizer.feed(0x12, 0)

        self.assertEqual(normalizer.feed(0x7D, 0), "K1-CW")
        self.assertEqual(normalizer.feed(0x7E, 0), "K1-CCW")

    def test_k2_direction_mapping_matches_physical_capture(self) -> None:
        normalizer = MacropadEventNormalizer()
        normalizer.feed(0x10, 0)
        normalizer.feed(0x12, 0)

        self.assertEqual(normalizer.feed(0x80, 0), "K2-CW")
        self.assertEqual(normalizer.feed(0x81, 0), "K2-CCW")

    def test_k3_direction_mapping_matches_physical_capture(self) -> None:
        normalizer = MacropadEventNormalizer()
        normalizer.feed(0x10, 0)
        normalizer.feed(0x12, 0)

        self.assertEqual(normalizer.feed(0x83, 0), "K3-CW")
        self.assertEqual(normalizer.feed(0x84, 0), "K3-CCW")


if __name__ == "__main__":
    unittest.main()
