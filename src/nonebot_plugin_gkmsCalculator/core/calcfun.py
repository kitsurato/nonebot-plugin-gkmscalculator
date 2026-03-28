"""学马算分核心数值：训练表、期中/期末评价分、产出评级文案生成。"""
from __future__ import annotations

from decimal import Decimal
from math import ceil
from typing import List, Sequence, Tuple, Union

# 单属性上限（游戏内封顶）
ATTR_CAP: int = 2800
# 期末考试给予的三维固定加成（每项）
FINAL_EXAM_STAT_BONUS: int = 120

# 训练回合 -> SP 与否 -> CLEAR / PERFECT 基数
TrainingRoundConf = dict[str, int]
TrainingTable = dict[int, dict[int, TrainingRoundConf]]

TRAINING_TABLE: TrainingTable = {
    1: {0: {"clear": 60, "perfect": 60}, 1: {"clear": 85, "perfect": 75}},
    2: {0: {"clear": 90, "perfect": 70}, 1: {"clear": 120, "perfect": 90}},
    3: {0: {"clear": 155, "perfect": 85}, 1: {"clear": 190, "perfect": 120}},
    4: {0: {"clear": 245, "perfect": 135}, 1: {"clear": 280, "perfect": 180}},
    5: {0: {"clear": 395, "perfect": 235}, 1: {"clear": 455, "perfect": 255}},
}

StatTriple = Union[Sequence[int], Sequence[float]]


def calculate_training_gain(
    current_stats: StatTriple,
    bonuses: StatTriple,
    round_num: int = 5,
    is_sp: int = 1,
    extra_item_bonus: int = 90,
) -> List[dict[str, object]]:
    """
    计算三种训练选择下预测后的三维属性。

    Args:
        current_stats: 当前 Vo, Da, Vi。
        bonuses: 各属性加成百分比（如 50 表示 50%）。
        round_num: 训练次数 1–5。
        is_sp: 1 为 SP 训练，0 为普通。
        extra_item_bonus: 道具提供的额外 PERFECT 相关加成。

    Returns:
        长度为 3 的列表，每项为 {"choice": 0|1|2, "stats": [vo, da, vi]}。
    """
    conf = TRAINING_TABLE.get(round_num, TRAINING_TABLE[5])[is_sp]
    clear_base = conf["clear"]
    perfect_per_stat = (conf["perfect"] + extra_item_bonus) / 3

    results: List[dict[str, object]] = []
    for choice in range(3):
        projected: List[int] = []
        for i in range(3):
            base_gain = (clear_base if i == choice else 0) + perfect_per_stat
            final_gain = base_gain * (1 + float(bonuses[i]) / 100)
            total = min(ATTR_CAP, int(float(current_stats[i]) + final_gain))
            projected.append(total)
        results.append({"choice": choice, "stats": projected})

    return results


def _get_midterm_eval(score: int) -> int:
    """由期中考试分数换算期中评价分。"""
    score = int(score)

    if score >= 200_000:
        return 2670

    if score <= 10_000:
        return int(score * 0.11)
    if score <= 20_000:
        return 1100 + int((score - 10_000) * 0.08)
    if score <= 30_000:
        return 1900 + int((score - 20_000) * 0.05)

    if score <= 40_000:
        return 2400 + int((score - 30_000) * 0.008)
    if score <= 50_000:
        return 2480 + int((score - 40_000) * 0.003)
    if score <= 60_000:
        return 2510 + int((score - 50_000) * 0.002)

    return 2530 + int((score - 60_000) * 0.001)


def _get_final_exam_score(needed_eval: int) -> int:
    """
    由「还需要的期末评价分」反推期末笔试分数需求。

    Returns:
        所需分数；无法达成时返回 -1；评价分已满足时返回 0。
    """
    if needed_eval <= 1700:
        return 0

    if needed_eval > 10400:
        return -1

    if needed_eval <= 6200:
        return ceil((needed_eval - 1700) / 0.015)

    if needed_eval <= 7200:
        return 300_000 + ceil((needed_eval - 6200) / 0.01)

    if needed_eval <= 8200:
        return 400_000 + ceil((needed_eval - 7200) / 0.01)

    if needed_eval <= 9000:
        return 500_000 + ceil((needed_eval - 8200) / 0.008)

    if needed_eval <= 10400:
        return 600_000 + ceil((needed_eval - 9000) / 0.001)

    return -1


def _calc_rank(
    vo: Union[str, int, float],
    di: Union[str, int, float],
    vi: Union[str, int, float],
    midterm_score: Union[str, int],
    extra_bonus: Union[str, int, float],
) -> str:
    """
    计算产出评级说明文案（含期末 +120 加成与期中评价分）。

    Args:
        vo, di, vi: 当前三维属性（字符串或数字）。
        midterm_score: 期中分数。
        extra_bonus: 额外固定属性加成（如 P 卡等），计入属性评价分。
    """
    vo_raw = Decimal(str(vo)) + FINAL_EXAM_STAT_BONUS
    di_raw = Decimal(str(di)) + FINAL_EXAM_STAT_BONUS
    vi_raw = Decimal(str(vi)) + FINAL_EXAM_STAT_BONUS

    extra = Decimal(str(extra_bonus))
    mid = int(midterm_score)

    stat_overflow = False

    if vo_raw > ATTR_CAP:
        vo_final = Decimal(ATTR_CAP)
        stat_overflow = True
    else:
        vo_final = vo_raw

    if di_raw > ATTR_CAP:
        di_final = Decimal(ATTR_CAP)
        stat_overflow = True
    else:
        di_final = di_raw

    if vi_raw > ATTR_CAP:
        vi_final = Decimal(ATTR_CAP)
        stat_overflow = True
    else:
        vi_final = vi_raw

    attr_total = vo_final + di_final + vi_final + extra
    attr_eval_score = int(attr_total * Decimal("2.1"))

    midterm_eval = _get_midterm_eval(mid)
    current_fixed_score = attr_eval_score + midterm_eval

    ranks: List[Tuple[str, int]] = [
        ("SSS", 20000),
        ("SSS+", 23000),
        ("23500", 23500),
        ("24000", 24000),
        ("24500", 24500),
        ("25000", 25000),
        ("25500", 25500),
        ("S4", 26000),
    ]

    lines: List[str] = []
    lines.append("已计算期末考试加成(+120)")
    if stat_overflow:
        lines.append(f"注：部分属性计算加成后已达上限{ATTR_CAP}")
    lines.append(
        f"最终计算属性：{int(vo_final)} + {int(di_final)} + {int(vi_final)}"
    )
    lines.append(f"属性评价分：{attr_eval_score}")
    lines.append(f"期中评价分：{midterm_eval} (期中得分: {mid})")
    lines.append(f"当前基础分：{current_fixed_score}")
    lines.append("============")
    lines.append("【距离各评级所需期末分数】")

    for rank_name, rank_score in ranks:
        needed_eval = rank_score - current_fixed_score

        if needed_eval <= 1700:
            if needed_eval <= 0:
                lines.append(f"{rank_name.ljust(4)}: 已达成")
            else:
                lines.append(f"{rank_name.ljust(4)}: 随便打")
        else:
            required_score = _get_final_exam_score(needed_eval)
            if required_score == -1:
                lines.append(f"{rank_name.ljust(4)}: ❌ 无法达成")
            else:
                lines.append(f"{rank_name.ljust(4)}: {required_score:,}")

    max_final_eval = 10400
    theoretical_max = current_fixed_score + max_final_eval
    lines.append(f"\n理论上限：{theoretical_max}")

    return "\n".join(lines)
