"""
角色属性状态评价模块
根据属性值、角色类型和训练次数判断属性的状态等级和到下一等级的差值
"""
from typing import Any, Dict, Optional, Tuple
from enum import Enum


class AttrStatus(Enum):
    """属性状态枚举"""
    EXCELLENT = "◎"     # 优秀
    GOOD = "○"          # 良好
    FAIR = "△"          # 及格
    POOR = "×"           # 未达标
    
    def __str__(self) -> str:
        return self.value


class TrainingPhase(Enum):
    """训练阶段"""
    MIDTERM = "期中"     # 训练次数1-2
    FINAL = "最终"       # 训练次数3-5


STANDARDS_SINGLE_POLE = {
    TrainingPhase.MIDTERM: {
        "first": {AttrStatus.EXCELLENT: 642, AttrStatus.GOOD: 584, AttrStatus.FAIR: 525},
        "second": {AttrStatus.EXCELLENT: 428, AttrStatus.GOOD: 390, AttrStatus.FAIR: 351},
        "third": {AttrStatus.EXCELLENT: 357, AttrStatus.GOOD: 325, AttrStatus.FAIR: 292},
    },
    TrainingPhase.FINAL: {
        "first": {AttrStatus.EXCELLENT: 2124, AttrStatus.GOOD: 1914, AttrStatus.FAIR: 1722},
        "second": {AttrStatus.EXCELLENT: 1417, AttrStatus.GOOD: 1277, AttrStatus.FAIR: 1149},
        "third": {AttrStatus.EXCELLENT: 1180, AttrStatus.GOOD: 1064, AttrStatus.FAIR: 957},
    }
}

STANDARDS_BALANCED = {
    TrainingPhase.MIDTERM: {
        "first": {AttrStatus.EXCELLENT: 612, AttrStatus.GOOD: 557, AttrStatus.FAIR: 501},
        "second": {AttrStatus.EXCELLENT: 456, AttrStatus.GOOD: 415, AttrStatus.FAIR: 373},
        "third": {AttrStatus.EXCELLENT: 356, AttrStatus.GOOD: 324, AttrStatus.FAIR: 291},
    },
    TrainingPhase.FINAL: {
        "first": {AttrStatus.EXCELLENT: 2050, AttrStatus.GOOD: 1828, AttrStatus.FAIR: 1645},
        "second": {AttrStatus.EXCELLENT: 1496, AttrStatus.GOOD: 1361, AttrStatus.FAIR: 1224},
        "third": {AttrStatus.EXCELLENT: 1169, AttrStatus.GOOD: 1063, AttrStatus.FAIR: 956},
    }
}


def get_training_phase(training_round: int) -> TrainingPhase:
    """
    根据训练次数获取训练阶段
    
    Args:
        training_round: 训练次数 (1-5)
        
    Returns:
        TrainingPhase: 期中 (1-2) 或 最终 (3-5)
    """
    if 1 <= training_round <= 2:
        return TrainingPhase.MIDTERM
    elif 3 <= training_round <= 5:
        return TrainingPhase.FINAL
    else:
        # 默认按最终处理
        return TrainingPhase.FINAL


def get_attr_status(attr_value: int, standards: Dict[AttrStatus, int]) -> AttrStatus:
    """
    根据属性值和标准判断状态
    
    Args:
        attr_value: 属性值
        standards: 该属性的评价标准字典 {状态: 分数}
        
    Returns:
        AttrStatus: 属性状态
    """
    if attr_value >= standards[AttrStatus.EXCELLENT]:
        return AttrStatus.EXCELLENT
    elif attr_value >= standards[AttrStatus.GOOD]:
        return AttrStatus.GOOD
    elif attr_value >= standards[AttrStatus.FAIR]:
        return AttrStatus.FAIR
    else:
        return AttrStatus.POOR


def get_next_threshold(current_status: AttrStatus) -> Optional[AttrStatus]:
    """
    获取下一个状态等级
    
    Args:
        current_status: 当前状态
        
    Returns:
        下一个更高的状态，如果已经是最高等级则返回 None
    """
    next_status_map = {
        AttrStatus.POOR: AttrStatus.FAIR,
        AttrStatus.FAIR: AttrStatus.GOOD,
        AttrStatus.GOOD: AttrStatus.EXCELLENT,
        AttrStatus.EXCELLENT: None
    }
    return next_status_map.get(current_status)


def calculate_attr_status(
    vo: int,
    da: int,
    vi: int,
    character_type: int,
    training_round: int,
    character_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    计算三属性的状态和差值
    
    Args:
        vo: Vo属性值
        da: Da属性值
        vi: Vi属性值
        character_type: 角色类型 (1=均衡型，2=单极型)
        training_round: 训练次数 (1-5)
        
    Returns:
        包含每个属性状态和差值信息的字典
        
    Examples:
        >>> result = calculate_attr_status(642, 428, 357, 2, 1)
        >>> result['vo']['status']
        '◎'
        >>> result['vo']['diff_to_next']
        None  # 已经是最高等级
        
        >>> result = calculate_attr_status(600, 400, 350, 2, 1)
        >>> result['vo']['status']
        '○'
        >>> result['vo']['diff_to_next']
        42  # 到◎还需要42分
    """
    # 确定训练阶段
    phase = get_training_phase(training_round)
    
    # 选择相应的标准
    if character_type == 1:  # 均衡型
        standards = STANDARDS_BALANCED[phase]
    else:  # 单极型 (2)
        standards = STANDARDS_SINGLE_POLE[phase]
    
    # 属性名与优先级映射
    attr_name_map = {1: "vo", 2: "da", 3: "vi"}
    priority_key_map = {1: "first", 2: "second", 3: "third"}
    attr_order = ["first", "second", "third"]
    attr_value_map = {"vo": vo, "da": da, "vi": vi}
    # 角色优先级与属性名
    if character_name:
        from .character_attrs import get_character_attrs
        _, vo_p, da_p, vi_p = get_character_attrs(character_name)
        # 优先级为1/2/3，按优先级升序排列，获得每个优先级对应的属性名
        priority_to_attr = {vo_p: "vo", da_p: "da", vi_p: "vi"}
        attr_order = [priority_key_map[i] for i in sorted(priority_to_attr.keys()) if i in priority_key_map]
        # 反向映射：优先级key->属性名
        key_to_attr = {priority_key_map[i]: priority_to_attr[i] for i in priority_to_attr if i in priority_key_map}
    else:
        # 默认顺序
        key_to_attr = {"first": "vo", "second": "da", "third": "vi"}

    result = {
        "phase": phase.value,
        "character_type": "均衡型" if character_type == 1 else "单极型",
        "attr_order": attr_order,
    }
    # 计算每个优先级属性
    for key in ["first", "second", "third"]:
        attr_name = key_to_attr.get(key, attr_name_map.get({"first":1,"second":2,"third":3}[key]))
        attr_value = attr_value_map[attr_name]
        attr_standards = standards[key]
        current_status = get_attr_status(attr_value, attr_standards)
        result[key] = {
            "attr_name": attr_name,
            "value": attr_value,
            "status": str(current_status)
        }
        next_status = get_next_threshold(current_status)
        if next_status:
            threshold = attr_standards[next_status]
            diff = threshold - attr_value
            result[key]["diff_to_next"] = max(0, diff)
            result[key]["next_status"] = str(next_status)
        else:
            result[key]["diff_to_next"] = None
            result[key]["next_status"] = None
    return result


def format_attr_status(status_result: Dict[str, Any]) -> str:
    """
    格式化属性状态结果为可读字符串
    
    Args:
        status_result: calculate_attr_status 的返回结果
        
    Returns:
        格式化的字符串
        
    Examples:
        >>> result = calculate_attr_status(642, 428, 357, 2, 1)
        >>> print(format_attr_status(result))
        期中 - 单极型
        Vo: 642 ◎ (已达最高等级)
        Da: 428 ◎ (已达最高等级)
        Vi: 357 ◎ (已达最高等级)
    """
    lines = [
        f"{status_result['phase']} - {status_result['character_type']}"
    ]
    attr_order = status_result.get("attr_order", ["first", "second", "third"])
    key_to_cn = {"first": "第一优先", "second": "第二优先", "third": "第三优先"}
    attr_to_cn = {"vo": "Vo", "da": "Da", "vi": "Vi"}
    for key in attr_order:
        attr_info = status_result[key]
        attr_name = attr_info.get("attr_name", key)
        value = attr_info["value"]
        status = attr_info["status"]
        label = attr_to_cn.get(attr_name, attr_name)
        if attr_info["diff_to_next"] is None:
            line = f"{key_to_cn.get(key, key)}({label}): {value} {status} (已达最高等级)"
        else:
            diff = attr_info["diff_to_next"]
            next_status = attr_info["next_status"]
            line = f"{key_to_cn.get(key, key)}({label}): {value} {status} → {next_status} 还需 {diff} 分"
        lines.append(line)
    return "\n".join(lines)


def format_attr_simple(status_result: Dict[str, Any]) -> Dict[str, str]:
    """
    格式化属性为简洁的内联格式
    用于直接显示在属性值后面
    
    Args:
        status_result: calculate_attr_status 的返回结果
        
    Returns:
        包含格式化结果的字典 {属性名: 格式化字符串}
        
    Examples:
        >>> result = calculate_attr_status(2000, 1300, 1100, 1, 5)
        >>> formatted = format_attr_simple(result)
        >>> formatted['vo']
        '2000（◎）'  # 如果已达最高等级
        
        >>> result = calculate_attr_status(1900, 1300, 1100, 1, 5)
        >>> formatted = format_attr_simple(result)
        >>> formatted['vo']
        '1900（○,+128）'  # 如果需要提升
    """
    formatted = {}
    for key in ["first", "second", "third"]:
        attr_info = status_result[key]
        value = attr_info["value"]
        status = attr_info["status"]
        diff_to_next = attr_info["diff_to_next"]
        attr_name = attr_info.get("attr_name", key)
        if diff_to_next is None:
            formatted[attr_name] = f"{value}（{status}）"
        else:
            formatted[attr_name] = f"{value}（{status},+{diff_to_next}）"
    return formatted


# 导出所有公共API
__all__ = [
    'AttrStatus',
    'TrainingPhase',
    'get_training_phase',
    'get_attr_status',
    'get_next_threshold',
    'calculate_attr_status',
    'format_attr_status',
    'format_attr_simple',
]
