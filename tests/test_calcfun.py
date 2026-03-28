"""core.calcfun 纯函数单元测试"""
from __future__ import annotations

import unittest

from nonebot_plugin_gkmsCalculator.core.calcfun import (
    ATTR_CAP,
    FINAL_EXAM_STAT_BONUS,
    TRAINING_TABLE,
    _calc_rank,
    _get_final_exam_score,
    _get_midterm_eval,
    calculate_training_gain,
)


class TestGetMidtermEval(unittest.TestCase):
    """期中分数 -> 期中评价分 分段逻辑。"""

    def test_zero_score(self) -> None:
        self.assertEqual(_get_midterm_eval(0), 0)

    def test_fifty_thousand(self) -> None:
        # 50k 段：2510 + (50000-50000)*0.002
        self.assertEqual(_get_midterm_eval(50_000), 2510)

    def test_cap_at_200k(self) -> None:
        self.assertEqual(_get_midterm_eval(200_000), 2670)
        self.assertEqual(_get_midterm_eval(500_000), 2670)


class TestGetFinalExamScore(unittest.TestCase):
    """期末评价分反推期末笔试分。"""

    def test_at_or_below_floor(self) -> None:
        self.assertEqual(_get_final_exam_score(1700), 0)
        self.assertEqual(_get_final_exam_score(0), 0)

    def test_impossible(self) -> None:
        self.assertEqual(_get_final_exam_score(20_000), -1)

    def test_first_segment(self) -> None:
        # (5000-1700)/0.015 -> ceil
        self.assertEqual(_get_final_exam_score(5000), 220_000)


class TestCalculateTrainingGain(unittest.TestCase):
    """训练增益三维预测。"""

    def test_round5_sp_choice_vo(self) -> None:
        stats = [1000, 1000, 1000]
        bonuses = [0.0, 0.0, 0.0]
        out = calculate_training_gain(stats, bonuses, round_num=5, is_sp=1, extra_item_bonus=90)
        self.assertEqual(len(out), 3)
        # 选 Vo：仅 Vo 获得 clear，三项均摊 perfect+道具
        conf = TRAINING_TABLE[5][1]
        perfect_part = (conf["perfect"] + 90) / 3
        vo_expected = int(1000 + conf["clear"] + perfect_part)
        self.assertEqual(out[0]["choice"], 0)
        self.assertEqual(out[0]["stats"][0], min(ATTR_CAP, vo_expected))


class TestCalcRank(unittest.TestCase):
    """产出评级文案：含 +120 与属性封顶。"""

    def test_contains_sections(self) -> None:
        text = _calc_rank("2000", "2000", "2000", "50000", "0")
        self.assertIn("已计算期末考试加成", text)
        self.assertIn("属性评价分", text)
        self.assertIn("期中评价分", text)
        self.assertIn("SSS", text)

    def test_stat_cap(self) -> None:
        base = ATTR_CAP - FINAL_EXAM_STAT_BONUS + 1
        text = _calc_rank(str(base), "0", "0", "50000", "0")
        self.assertIn(f"已达上限{ATTR_CAP}", text)


if __name__ == "__main__":
    unittest.main()
