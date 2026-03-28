"""
角色属性优先级计算模块
根据角色名称返回属性类型和优先级信息
"""
from typing import Any, Dict, Tuple

# 角色属性优先级数据
# 键：角色名称
# 值：(属性类型, Vo优先级, Da优先级, Vi优先级)
# 属性类型：1=均衡型，2=单极型
# 优先级：1=第一优先，2=第二优先，3=第三优先

CHARACTER_ATTRS = {
    # 均衡型 (1)
    "花海咲季": (1, 3, 2, 1),      # 黄蓝红 -> Vi=1, Da=2, Vo=3
    "葛城莉莉娅": (1, 3, 2, 1),    # 黄蓝红 -> Vi=1, Da=2, Vo=3
    "筱泽广": (1, 1, 2, 3),        # 红蓝黄 -> Vo=1, Da=2, Vi=3
    "十王星南": (1, 2, 3, 1),      # 黄红蓝 -> Vi=1, Vo=2, Da=3
    "花海佑芽": (1, 2, 1, 3),      # 蓝红黄 -> Da=1, Vo=2, Vi=3
    "姬崎莉波": (1, 3, 2, 1),      # 黄蓝红 -> Vi=1, Da=2, Vo=3
    
    # 单极型 (2)
    "月村手毬": (2, 1, 2, 3),      # 红蓝黄 -> Vo=1, Da=2, Vi=3
    "藤田琴音": (2, 3, 1, 2),      # 蓝黄红 -> Da=1, Vi=2, Vo=3
    "雨夜燕": (2, 2, 1, 3),        # 蓝红黄 -> Da=1, Vo=2, Vi=3
    "有村麻央": (2, 1, 3, 2),      # 红黄蓝 -> Vo=1, Vi=2, Da=3
    "仓本千奈": (2, 3, 1, 2),      # 蓝黄红 -> Da=1, Vi=2, Vo=3
    "紫云清夏": (2, 3, 1, 2),      # 蓝黄红 -> Da=1, Vi=2, Vo=3
    "秦谷美铃": (2, 1, 3, 2),      # 红黄蓝 -> Vo=1, Vi=2, Da=3
}

# 角色ID到角色名的映射
CHARACTER_ID_TO_NAME = {
    1: "花海咲季",
    2: "葛城莉莉娅",
    3: "筱泽广",
    4: "十王星南",
    5: "花海佑芽",
    6: "姬崎莉波",
    7: "月村手毬",
    8: "藤田琴音",
    9: "有村麻央",
    10: "仓本千奈",
    11: "紫云清夏",
    12: "秦谷美铃",
    13: "雨夜燕",
}


def get_character_by_id(character_id: int) -> str:
    """
    根据角色ID获取角色名称
    
    Args:
        character_id: 角色ID (1-13)
        
    Returns:
        角色名称，如果ID不存在则返回空字符串
    """
    return CHARACTER_ID_TO_NAME.get(character_id, "")


def get_character_attrs(character_name: str) -> Tuple[int, int, int, int]:
    """
    根据角色名称获取属性优先级信息
    
    Args:
        character_name: 角色名称
        
    Returns:
        元组 (属性类型, Vo优先级, Da优先级, Vi优先级)
        - 属性类型: 1=均衡型，2=单极型
        - 优先级: 1=第一优先，2=第二优先，3=第三优先
        
    Examples:
        >>> get_character_attrs("花海咲季")
        (1, 3, 2, 1)  # 均衡型，Vo第三优先，Da第二优先，Vi第一优先
        
        >>> get_character_attrs("月村手毬")
        (2, 1, 2, 3)  # 单极型，Vo第一优先，Da第二优先，Vi第三优先
    """
    return CHARACTER_ATTRS.get(character_name, (0, 0, 0, 0))


def get_character_attrs_by_id(character_id: int) -> Tuple[int, int, int, int]:
    """
    根据角色ID获取属性优先级信息
    
    Args:
        character_id: 角色ID (1-13)
        
    Returns:
        元组 (属性类型, Vo优先级, Da优先级, Vi优先级)
    """
    character_name = get_character_by_id(character_id)
    if character_name:
        return get_character_attrs(character_name)
    return (0, 0, 0, 0)


def get_character_type_name(attrs_type: int) -> str:
    """
    获取属性类型的名称
    
    Args:
        attrs_type: 属性类型 (1=均衡型，2=单极型)
        
    Returns:
        属性类型名称
    """
    type_map = {
        1: "均衡型",
        2: "单极型"
    }
    return type_map.get(attrs_type, "未知")


def get_priority_name(priority: int) -> str:
    """
    获取优先级的名称
    
    Args:
        priority: 优先级 (1=第一优先，2=第二优先，3=第三优先)
        
    Returns:
        优先级名称
    """
    priority_map = {
        1: "第一优先",
        2: "第二优先",
        3: "第三优先"
    }
    return priority_map.get(priority, "未知")


def format_character_attrs(character_name: str) -> Dict[str, Any]:
    """
    格式化角色属性信息为字典
    
    Args:
        character_name: 角色名称
        
    Returns:
        包含格式化属性信息的字典
        
    Examples:
        >>> format_character_attrs("花海咲季")
        {
            'character': '花海咲季',
            'type': '均衡型',
            'vo_priority': '第三优先',
            'da_priority': '第二优先',
            'vi_priority': '第一优先'
        }
    """
    attrs_type, vo_priority, da_priority, vi_priority = get_character_attrs(character_name)
    
    if attrs_type == 0:
        return {"error": f"角色 '{character_name}' 不存在"}
    
    return {
        "character": character_name,
        "type": get_character_type_name(attrs_type),
        "vo_priority": get_priority_name(vo_priority),
        "da_priority": get_priority_name(da_priority),
        "vi_priority": get_priority_name(vi_priority),
        "raw": (attrs_type, vo_priority, da_priority, vi_priority)
    }


# 导出所有公共API
__all__ = [
    'CHARACTER_ATTRS',
    'CHARACTER_ID_TO_NAME',
    'get_character_by_id',
    'get_character_attrs',
    'get_character_attrs_by_id',
    'get_character_type_name',
    'get_priority_name',
    'format_character_attrs',
]
