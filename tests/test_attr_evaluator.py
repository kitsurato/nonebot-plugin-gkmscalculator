"""core.attr_evaluator 训练阶段与状态计算测试"""
from __future__ import annotations

import unittest

from nonebot_plugin_gkmsCalculator.core.attr_evaluator import (
    AttrStatus,
    TrainingPhase,
    calculate_attr_status,
    format_attr_simple,
    get_attr_status,
    get_next_threshold,
    get_training_phase,
)


class TestTrainingPhase(unittest.TestCase):
    def test_midterm_rounds(self) -> None:
        self.assertEqual(get_training_phase(1), TrainingPhase.MIDTERM)
        self.assertEqual(get_training_phase(2), TrainingPhase.MIDTERM)

    def test_final_rounds(self) -> None:
        self.assertEqual(get_training_phase(3), TrainingPhase.FINAL)
        self.assertEqual(get_training_phase(5), TrainingPhase.FINAL)


class TestAttrStatusHelpers(unittest.TestCase):
    def test_next_threshold_chain(self) -> None:
        self.assertEqual(get_next_threshold(AttrStatus.POOR), AttrStatus.FAIR)
        self.assertIsNone(get_next_threshold(AttrStatus.EXCELLENT))

    def test_get_attr_status_order(self) -> None:
        standards = {
            AttrStatus.EXCELLENT: 600,
            AttrStatus.GOOD: 500,
            AttrStatus.FAIR: 400,
        }
        self.assertEqual(get_attr_status(700, standards), AttrStatus.EXCELLENT)
        self.assertEqual(get_attr_status(550, standards), AttrStatus.GOOD)
        self.assertEqual(get_attr_status(300, standards), AttrStatus.POOR)


class TestCalculateAttrStatus(unittest.TestCase):
    def test_single_pole_midterm_exact_excellent(self) -> None:
        # 单极型期中 first 优秀线 642
        result = calculate_attr_status(642, 428, 357, 2, 1, character_name="月村手毬")
        self.assertEqual(result["phase"], "期中")
        simple = format_attr_simple(result)
        self.assertIn("vo", simple)
        self.assertIn("◎", simple["vo"])


if __name__ == "__main__":
    unittest.main()
