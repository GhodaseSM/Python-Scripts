import importlib.util
import random
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


TARGET = Path(__file__).resolve().parents[2] / "Turtle Art" / "art2.py"
BASE_COLORS = ["sky blue", "navy", "steel blue", "cyan"]


def load_art_module():
    """Import only art2, replacing its GUI dependency before execution."""
    turtle_stub = types.ModuleType("turtle")
    turtle_stub.__all__ = ["speed", "width", "color", "circle"]
    turtle_stub.speed = Mock(name="speed")
    turtle_stub.width = Mock(name="width")
    turtle_stub.color = Mock(name="color")
    turtle_stub.circle = Mock(name="circle")
    spec = importlib.util.spec_from_file_location("art2_under_test", TARGET)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"turtle": turtle_stub}):
        spec.loader.exec_module(module)
    return module


def expected_output(seed, iterations):
    rng = random.Random(seed)
    colors = BASE_COLORS.copy()
    chosen_colors = []
    circles = []
    for index in range(iterations):
        rng.shuffle(colors)
        chosen_colors.append(colors[0])
        circles.append((10 + 2 * index, 100, 2))
    return chosen_colors, circles, colors


class TestTurtleArt(unittest.TestCase):
    def setUp(self):
        self.module = load_art_module()
        self.colors = BASE_COLORS.copy()
        self.module.colors = self.colors

    def assert_draw_matches(self, iterations, seed):
        expected_colors, expected_circles, expected_final_colors = expected_output(
            seed, iterations
        )
        random.seed(seed)
        result = self.module.main(iterations)
        actual_colors = [call.args[0] for call in self.module.color.call_args_list]
        actual_circles = [call.args for call in self.module.circle.call_args_list]

        self.assertIsNone(result)
        self.assertEqual(actual_colors, expected_colors)
        self.assertEqual(actual_circles, expected_circles)
        self.assertEqual(self.colors, expected_final_colors)
        self.assertIs(self.module.colors, self.colors)
        self.assertEqual(len(actual_circles), iterations)

    def test_default_preserves_original_102_circle_art(self):
        expected_colors, expected_circles, expected_final_colors = expected_output(
            314159, 102
        )
        random.seed(314159)
        result = self.module.main()
        self.assertIsNone(result)
        self.assertEqual(
            [call.args[0] for call in self.module.color.call_args_list], expected_colors
        )
        self.assertEqual(
            [call.args for call in self.module.circle.call_args_list], expected_circles
        )
        self.assertEqual(self.colors, expected_final_colors)

    def test_zero_iterations_has_no_draws_or_color_mutation(self):
        original_colors = self.colors.copy()
        random.seed(23)
        self.assertIsNone(self.module.main(0))
        self.module.color.assert_not_called()
        self.module.circle.assert_not_called()
        self.assertEqual(self.colors, original_colors)

    def test_scaled_sizes_have_expected_draws_and_mutation(self):
        for size, seed in ((32, 20261122), (64, 20261123), (102, 20261124)):
            with self.subTest(size=size):
                self.module.color.reset_mock()
                self.module.circle.reset_mock()
                self.colors[:] = BASE_COLORS
                self.assert_draw_matches(size, seed)


if __name__ == "__main__":
    unittest.main()