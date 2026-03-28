"""
核心计算模块
包含角色属性计算、评分计算、训练计算等核心功能
"""

from .calcfun import (
    ATTR_CAP,
    FINAL_EXAM_STAT_BONUS,
    TRAINING_TABLE,
    calculate_training_gain,
    _get_midterm_eval,
    _get_final_exam_score,
    _calc_rank,
)

from .character_attrs import (
    CHARACTER_ATTRS,
    CHARACTER_ID_TO_NAME,
    get_character_by_id,
    get_character_attrs,
    get_character_attrs_by_id,
    get_character_type_name,
    get_priority_name,
    format_character_attrs,
)

from .attr_evaluator import (
    AttrStatus,
    TrainingPhase,
    get_training_phase,
    get_attr_status,
    get_next_threshold,
    calculate_attr_status,
    format_attr_status,
    format_attr_simple,
)

__all__ = [
    # calcfun
    'ATTR_CAP',
    'FINAL_EXAM_STAT_BONUS',
    'TRAINING_TABLE',
    'calculate_training_gain',
    '_get_midterm_eval',
    '_get_final_exam_score',
    '_calc_rank',
    # character_attrs
    'CHARACTER_ATTRS',
    'CHARACTER_ID_TO_NAME',
    'get_character_by_id',
    'get_character_attrs',
    'get_character_attrs_by_id',
    'get_character_type_name',
    'get_priority_name',
    'format_character_attrs',
    # attr_evaluator
    'AttrStatus',
    'TrainingPhase',
    'get_training_phase',
    'get_attr_status',
    'get_next_threshold',
    'calculate_attr_status',
    'format_attr_status',
    'format_attr_simple',
]
