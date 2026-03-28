from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Union

from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import Message
from nonebot.exception import FinishedException, RejectedException
from nonebot.matcher import Matcher
from nonebot.params import Arg, CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin.on import on_command
from nonebot.typing import T_State
from .ocr.OCRattrs import get_all_game_data, detect_exam_screen, get_exam_data
from .core.calcfun import (
    ATTR_CAP,
    FINAL_EXAM_STAT_BONUS,
    TRAINING_TABLE,
    _calc_rank,
    _get_final_exam_score,
    _get_midterm_eval,
)
from .core.attr_evaluator import calculate_attr_status, format_attr_simple
from .core.character_attrs import get_character_by_id, get_character_attrs


class ImageCalcState(TypedDict):
    """图片识别后暂存的训练计算上下文（按用户 ID 保存在内存中）。"""

    attrs: List[Union[int, float]]
    bonuses: List[float]
    r_num: int
    sp_list: List[int]
    character_id: int
    character_name: str
    char_name_display: str


# ====================
# 1. 算分 (Produce Rank)
# ====================
calc_rank = on_command(
    "算分",
    aliases={},
    priority=20,
    block=True,
)

@calc_rank.handle()
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    state: T_State,
    cmd_arg: Message = CommandArg(),
) -> None:
    if cmd_arg:
        state["calcrankattr"] = cmd_arg

# 【修改点 1】更新了 Prompt，提示用户自行处理额外属性
@calc_rank.got(
    "calcrankattr",
    prompt=(
        "请输入: Vo Di Vi 期中得分\n支持发送截图\n未输入期中得分则默认为50000\n"
        "期末后增加属性（如SR蓝饮料+17）\n请自行提前加到对应属性"
    ),
)
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    state: T_State,
    cmd_arg: Message = Arg("calcrankattr"),
) -> None:
    found_image = False
    
    # --- 1. 尝试图片识别 ---
    for segment in cmd_arg:
        if segment.type == "image":
            try:
                # 先检测是否为考试界面
                is_exam = await asyncio.to_thread(detect_exam_screen, segment.data["url"])
                
                if is_exam:
                    # 使用考试界面识别函数
                    data = await asyncio.to_thread(get_exam_data, segment.data["url"])
                else:
                    # 使用训练界面识别函数
                    data = await asyncio.to_thread(get_all_game_data, segment.data["url"])
            except FinishedException:
                # 让FinishedException正常向上传递，不要被捕获
                raise
            except Exception as e:
                await matcher.finish(f"OCR识别失败: {str(e)}")

            if not data or not data.get("attrs"):
                await matcher.finish("无法识别图片中的三维属性")
            
            # 提取三维属性
            attrs = data["attrs"]
            state["vo"] = str(attrs[0])
            state["di"] = str(attrs[1])
            state["vi"] = str(attrs[2])
            found_image = True
            break
    
    # --- 2. 文本解析 ---
    text_args = cmd_arg.extract_plain_text().strip().split()
    
    if found_image:
        # 图片模式下的补充参数 (只读取期中分，忽略后续参数)
        if len(text_args) >= 1: 
            state["midterm_score"] = text_args[0]
        else: 
            state["midterm_score"] = "50000"
    else:
        # 纯文本模式
        if not text_args:
            await matcher.reject("请输入有效参数")
        
        if len(text_args) < 3:
            await matcher.finish("参数不足，请至少输入三维属性 (Vo Di Vi)")
        
        state["vo"] = text_args[0]
        state["di"] = text_args[1]
        state["vi"] = text_args[2]
        
        if len(text_args) >= 4:
            state["midterm_score"] = text_args[3]
        else:
            state["midterm_score"] = "50000"


def _parse_state_scalar(value: Union[str, Message, Any]) -> str:
    """从 state 或 Message 中取出纯文本字符串。"""
    if isinstance(value, Message):
        return value.extract_plain_text().strip()
    return str(value).strip()


@calc_rank.handle()
async def final_calc(
    bot: Bot, event: Event, matcher: Matcher, state: T_State
) -> None:
    try:
        vo = _parse_state_scalar(state["vo"])
        di = _parse_state_scalar(state["di"])
        vi = _parse_state_scalar(state["vi"])
        midterm = _parse_state_scalar(state.get("midterm_score", "50000"))
        bonus = "0"
        rank_message = await asyncio.to_thread(
            _calc_rank, vo, di, vi, midterm, bonus
        )
    except Exception:
        await matcher.finish("请输入正确的数字")
        return

    await matcher.finish(rank_message)


# ====================
# 2. 算属性 (Attr Calc) - 修改为等待图片或文本输入
# ====================


_CHARACTER_NAMES: Dict[str, List[str]] = {}

CHARACTER_CODE_MAP: Dict[str, str] = {}


def _rebuild_character_code_map() -> None:
    """根据 ``_CHARACTER_NAMES`` 重建 ``CHARACTER_CODE_MAP``。"""
    CHARACTER_CODE_MAP.clear()
    for name, codes in _CHARACTER_NAMES.items():
        for code in codes:
            CHARACTER_CODE_MAP[code] = name


def _get_character_name(code: Optional[str]) -> Optional[str]:
    """根据别称/代号（不区分大小写）解析角色全名。"""
    if not code:
        return None
    code_lower = str(code).lower().strip()
    for name, codes in _CHARACTER_NAMES.items():
        for alias in codes:
            if alias.lower() == code_lower:
                return name
    return None


# 存储已识别的图片数据（用户 ID -> 最近一次 OCR 训练上下文）
_image_calc_state: Dict[int, ImageCalcState] = {}


def _calc_attr_result(
    attrs: List[Union[int, float]],
    bonuses: List[float],
    r_num: int,
    item_bonus: Optional[int],
    character_name: Optional[str] = None,
) -> str:
    """计算三种训练选项下的预测属性与评价，返回多行说明文本。"""
    char_type = 2  # 默认单极型
    if character_name:
        try:
            char_type, _, _, _ = get_character_attrs(character_name)
        except Exception:
            pass
    
    # 计算每种选择的结果
    labels = ["红(Vo)", "蓝(Da)", "黄(Vi)"]
    item_bonus = item_bonus or 90  # 默认道具加成
    
    msg = ""
    for i in range(3):
        # 使用AI返回的SP标志决定使用哪种计算
        sp_status = 1  # 默认SP训练
        conf = TRAINING_TABLE.get(r_num, TRAINING_TABLE[5])[sp_status]
        
        res = []
        for j in range(3):
            base_gain = (conf["clear"] if i == j else 0) + (conf["perfect"] + item_bonus) / 3
            actual_gain = base_gain * (1 + bonuses[j] / 100)
            final = int(attrs[j] + actual_gain)
            res.append(min(ATTR_CAP, final))
        
        # 为每个结果生成评价
        try:
            status_result = calculate_attr_status(
                res[0],
                res[1],
                res[2],
                char_type,
                r_num,
                character_name=character_name,
            )
            formatted = format_attr_simple(status_result)
            result_str = f"{formatted['vo']} | {formatted['da']} | {formatted['vi']}"
        except Exception:
            result_str = f"{res[0]} | {res[1]} | {res[2]}"
        
        sp_tag = "[SP]"
        msg += f"选 {labels[i]}{sp_tag}: {result_str} (总:{sum(res)})\n"
    
    return msg

calc_highattr = on_command("算属性", aliases={"训练计算"}, priority=20, block=True)

@calc_highattr.handle()
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    state: T_State,
    cmd_arg: Message = CommandArg(),
) -> None:
    # 如果命令后直接带了参数，保存到state
    if cmd_arg:
        state["input_data"] = cmd_arg

@calc_highattr.got(
    "input_data",
    prompt=(
        "请发送截图或输入属性数据\n"
        "文本格式：[角色代号] 红 蓝 黄 红加成 蓝加成 黄加成 [道具属性] [第几次训练]\n"
        "示例：mao 474 909 710 30.1 34.9 18.6 90 5"
    ),
)
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    state: T_State,
    arg: Message = Arg("input_data"),
) -> None:
    # 检查是否是图片
    for segment in arg:
        if segment.type == "image":
            try:
                # 调用OCR识别
                data = await asyncio.to_thread(get_all_game_data, segment.data["url"])
                if not data:
                    await matcher.finish("图片识别失败，请确保截图清晰且处于训练选择界面")

                # 提取数据
                attrs = data["attrs"]
                bonuses = data["bonuses"]  # 已经是百分比形式
                r_num = data["round"]
                sp_list = data.get("sp_list", [0, 0, 0])  # 从AI获取SP标志信息
                character_id = data.get("character_id", 13)  # 获取角色ID，默认为13
                
                # 获取角色名称
                character_name = get_character_by_id(character_id)
                char_name_display = character_name if character_name else "未识别"
                
                # 保存当前用户的图片识别数据
                user_id = event.user_id
                _image_calc_state[user_id] = {
                    "attrs": attrs,
                    "bonuses": bonuses,
                    "r_num": r_num,
                    "sp_list": sp_list,
                    "character_id": character_id,
                    "character_name": character_name,
                    "char_name_display": char_name_display
                }
                
                # 构建输出格式
                msg = f"进度：第 {r_num} 次训练\n"
                msg += f"当前角色：{char_name_display}\n"
                msg += f"当前属性：Vo={attrs[0]} Da={attrs[1]} Vi={attrs[2]}\n"
                msg += f"属性加成：Vo={bonuses[0]:.1f}% Da={bonuses[1]:.1f}% Vi={bonuses[2]:.1f}%\n"
                msg += f"道具属性：90\n"
                msg += "=" * 12 + "\n"
                
                # 计算每种选择的结果
                labels = ["红(Vo)", "蓝(Da)", "黄(Vi)"]
                item_bonus = 90  # 默认道具加成
                
                # 获取角色类型用于结果评价
                char_type = 2  # 默认单极型
                if character_name:
                    try:
                        char_type, _, _, _ = get_character_attrs(character_name)
                    except Exception:
                        pass
                
                for i in range(3):
                    # 使用AI返回的SP标志决定使用哪种计算
                    sp_status = sp_list[i]  # 1 = SP训练, 0 = 普通训练
                    conf = TRAINING_TABLE.get(r_num, TRAINING_TABLE[5])[sp_status]
                    
                    res = []
                    for j in range(3):
                        base_gain = (conf["clear"] if i == j else 0) + (conf["perfect"] + item_bonus) / 3
                        actual_gain = base_gain * (1 + bonuses[j] / 100)
                        final = int(attrs[j] + actual_gain)
                        res.append(min(ATTR_CAP, final))
                    
                    # 为每个结果生成评价
                    try:
                        status_result = calculate_attr_status(
                            res[0],
                            res[1],
                            res[2],
                            char_type,
                            r_num,
                            character_name=character_name,
                        )
                        formatted = format_attr_simple(status_result)
                        result_str = f"{formatted['vo']} | {formatted['da']} | {formatted['vi']}"
                    except Exception:
                        result_str = f"{res[0]} | {res[1]} | {res[2]}"
                    
                    sp_tag = "[SP]" if sp_status else "[普]"
                    msg += f"选 {labels[i]}{sp_tag}: {result_str} (总:{sum(res)})\n"
                
                msg += "\n可以输入 修改 <角色代号> 来更换角色的计算规则"
                
                # 等待用户下一条消息
                state["waiting_for_correction"] = True
                await matcher.reject(msg)
                
            except FinishedException:
                # 让FinishedException正常向上传递，不要被捕获
                raise
            except Exception as e:
                if isinstance(e, RejectedException):
                    raise
                await matcher.finish(f"识别失败: {str(e)}")
    
    # 检查是否在等待纠错消息
    user_id = event.user_id
    if user_id in _image_calc_state:
        text_input = arg.extract_plain_text().strip()
        
        # 检查是否是修改命令
        if text_input.startswith("修改"):
            parts = text_input.split()
            if len(parts) < 2:
                await matcher.reject("请输入：修改 <角色代号>\n示例：修改 mao")
            
            character_code = parts[1].lower()
            if character_code not in CHARACTER_CODE_MAP:
                available_codes = ", ".join(CHARACTER_CODE_MAP.keys())
                await matcher.reject(f"未知的角色代号：{character_code}\n支持的代号：{available_codes}")
            
            try:
                # 使用新的角色重新计算
                character_name = CHARACTER_CODE_MAP[character_code]
                state_data = _image_calc_state[user_id]
                
                # 构建输出格式
                msg = f"进度：第 {state_data['r_num']} 次训练\n"
                msg += f"当前角色：{character_name} (修改自 {state_data['char_name_display']})\n"
                msg += f"当前属性：Vo={state_data['attrs'][0]} Da={state_data['attrs'][1]} Vi={state_data['attrs'][2]}\n"
                msg += f"属性加成：Vo={state_data['bonuses'][0]:.1f}% Da={state_data['bonuses'][1]:.1f}% Vi={state_data['bonuses'][2]:.1f}%\n"
                msg += f"道具属性：90\n"
                msg += "=" * 12 + "\n"
                
                # 计算每种选择的结果
                labels = ["红(Vo)", "蓝(Da)", "黄(Vi)"]
                item_bonus = 90  # 默认道具加成
                
                # 获取角色类型用于结果评价
                char_type = 2  # 默认单极型
                try:
                    char_type, _, _, _ = get_character_attrs(character_name)
                except Exception:
                    pass

                for i in range(3):
                    # 使用AI返回的SP标志决定使用哪种计算
                    sp_status = state_data["sp_list"][i]  # 1 = SP训练, 0 = 普通训练
                    conf = TRAINING_TABLE.get(state_data['r_num'], TRAINING_TABLE[5])[sp_status]
                    
                    res = []
                    for j in range(3):
                        base_gain = (conf["clear"] if i == j else 0) + (conf["perfect"] + item_bonus) / 3
                        actual_gain = base_gain * (1 + state_data['bonuses'][j] / 100)
                        final = int(state_data['attrs'][j] + actual_gain)
                        res.append(min(ATTR_CAP, final))
                    
                    # 为每个结果生成评价
                    try:
                        status_result = calculate_attr_status(
                            res[0],
                            res[1],
                            res[2],
                            char_type,
                            state_data["r_num"],
                            character_name=character_name,
                        )
                        formatted = format_attr_simple(status_result)
                        result_str = f"{formatted['vo']} | {formatted['da']} | {formatted['vi']}"
                    except Exception:
                        result_str = f"{res[0]} | {res[1]} | {res[2]}"

                    sp_tag = "[SP]" if sp_status else "[普]"
                    msg += f"选 {labels[i]}{sp_tag}: {result_str} (总:{sum(res)})\n"

                # 清空该用户的状态
                del _image_calc_state[user_id]
                await matcher.finish(msg)
            except FinishedException:
                # 让FinishedException正常向上传递
                if user_id in _image_calc_state:
                    del _image_calc_state[user_id]
                raise
            except Exception as e:
                # 清空该用户的状态
                if user_id in _image_calc_state:
                    del _image_calc_state[user_id]
                await matcher.finish(f"修改失败: {str(e)}")
        else:
            # 直接输入文本，不是修改命令
            # 清空该用户的状态
            del _image_calc_state[user_id]
            
            # 图片识别后如果输入的不是"修改"命令，直接关闭此次计算
            await matcher.finish("计算已关闭")
    
    # 文本模式解析（非图片纠错）
    # 始终用arg，保证分开发时能识别角色
    text = arg.extract_plain_text().strip()
    text_args = text.split()

    # 先检查第一个参数是否为角色代号
    character_code = None
    character_name = None
    idx = 0
    if len(text_args) > 0:
        potential_code = text_args[0].lower()
        potential_name = _get_character_name(potential_code)
        if potential_name:
            character_code = potential_code
            character_name = potential_name
            idx = 1
    # 检查剩余参数数量：需要6-8个（3个属性 + 3个加成 + [道具属性] + [训练次数]）
    remaining_args = text_args[idx:]
    if len(remaining_args) < 6 or len(remaining_args) > 8:
        await matcher.reject("参数数量错误！\n格式：[角色代号] 红 蓝 黄 红加成 蓝加成 黄加成 [道具属性] [第几次训练]\n示例：mao 474 909 710 30.1 34.9 18.6 90 5")
    
    try:
        # 检查是否有足够的属性参数
        if len(remaining_args) < 6:
            await matcher.reject("参数不足！请至少输入三维属性和三个加成\n格式：[角色代号] 红 蓝 黄 红加成 蓝加成 黄加成 [道具属性] [第几次训练]\n示例：mao 474 909 710 30.1 34.9 18.6")
        
        # 解析参数
        attrs = [int(remaining_args[0]), int(remaining_args[1]), int(remaining_args[2])]
        bonuses = [float(remaining_args[3]), float(remaining_args[4]), float(remaining_args[5])]
        
        # 解析可选参数
        if len(remaining_args) == 6:
            # 只有基础6个参数
            item_bonus = 90
            r_num = 5
        elif len(remaining_args) == 7:
            # 7个参数：道具属性
            item_bonus = int(remaining_args[6])
            r_num = 5
        else:  # len(remaining_args) == 8
            # 8个参数：道具属性 + 训练次数
            item_bonus = int(remaining_args[6])
            r_num = int(remaining_args[7])
        
        # 验证道具属性必须是10的整数倍
        if item_bonus % 10 != 0:
            await matcher.reject(f"道具属性必须是10的整数倍，当前值：{item_bonus}")
        
        # 验证训练次数必须在1-5之间
        if not (1 <= r_num <= 5):
            await matcher.reject(f"训练次数必须在1-5之间，当前值：{r_num}")
        
        # 构建输出格式
        msg = f"进度：第 {r_num} 次训练\n"
        msg += f"当前角色：{character_name if character_name else '未知'}\n"
        msg += f"当前属性：Vo={attrs[0]} Da={attrs[1]} Vi={attrs[2]}\n"
        msg += f"属性加成：Vo={bonuses[0]:.1f}% Da={bonuses[1]:.1f}% Vi={bonuses[2]:.1f}%\n"
        msg += f"道具属性：{item_bonus}\n"
        msg += "=" * 12 + "\n"
        
        # 计算每种选择的结果
        labels = ["红(Vo)", "蓝(Da)", "黄(Vi)"]
        # 获取角色类型用于结果评价
        char_type = 2  # 默认单极型
        if character_name:
            try:
                char_type, _, _, _ = get_character_attrs(character_name)
            except Exception:
                pass

        for i in range(3):
            # 使用SP状态计算
            sp_status = 1  # 默认SP训练
            conf = TRAINING_TABLE.get(r_num, TRAINING_TABLE[5])[sp_status]
            
            res = []
            for j in range(3):
                base_gain = (conf["clear"] if i == j else 0) + (conf["perfect"] + item_bonus) / 3
                actual_gain = base_gain * (1 + bonuses[j] / 100)
                final = int(attrs[j] + actual_gain)
                res.append(min(ATTR_CAP, final))
            
            # 为每个结果生成评价
            if character_name:
                # 有指定角色，显示评级
                try:
                    status_result = calculate_attr_status(
                        res[0],
                        res[1],
                        res[2],
                        char_type,
                        r_num,
                        character_name=character_name,
                    )
                    formatted = format_attr_simple(status_result)
                    result_str = f"{formatted['vo']} | {formatted['da']} | {formatted['vi']}"
                except Exception:
                    result_str = f"{res[0]} | {res[1]} | {res[2]}"
            else:
                # 没有指定角色，只显示数字
                result_str = f"{res[0]} | {res[1]} | {res[2]}"
            
            sp_tag = "[SP]"
            msg += f"选 {labels[i]}{sp_tag}: {result_str} (总:{sum(res)})\n"
        
        await matcher.finish(msg)
        
    except (ValueError, IndexError):
        await matcher.reject(
            "输入格式错误！\n格式：[角色代号] 红 蓝 黄 红加成 蓝加成 黄加成 [道具属性] [第几次训练]\n"
            "示例1：474 909 710 30.1 34.9 18.6\n"
            "示例2：mao 474 909 710 30.1 34.9 18.6 90 5"
        )


# ====================
# 3. 强化月算分 (Strengthen Month Rank)
# ====================
# 公式：强化月分数 = 一般分数 × 0.72 + 星星数 × 11.016（向下取整）
calc_strengthen_month = on_command(
    "强化月算分",
    aliases={"强化月分数"},
    priority=20,
    block=True,
)

@calc_strengthen_month.handle()
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    state: T_State,
    cmd_arg: Message = CommandArg(),
) -> None:
    if cmd_arg:
        state["strengthen_input"] = cmd_arg

@calc_strengthen_month.got(
    "strengthen_input",
    prompt=(
        "请输入三维属性、期中分、星星数\n支持发送截图（默认期中分60000、星星数610）\n"
        "文本格式：Vo Da Vi [期中分] [星星数]\n示例：2400 2000 1200 60000 610"
    ),
)
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    state: T_State,
    arg: Message = Arg("strengthen_input"),
) -> None:
    stars = 610  # 默认星星数
    midterm_score = "60000"  # 默认期中分
    general_score = 0
    vo = 0
    da = 0
    vi = 0
    
    # 检查是否是图片
    for segment in arg:
        if segment.type == "image":
            try:
                # 先检测是否为考试界面
                is_exam = await asyncio.to_thread(detect_exam_screen, segment.data["url"])
                
                if is_exam:
                    # 使用考试界面识别函数
                    data = await asyncio.to_thread(get_exam_data, segment.data["url"])
                else:
                    # 使用训练界面识别函数
                    data = await asyncio.to_thread(get_all_game_data, segment.data["url"])
            except FinishedException:
                raise
            except Exception as e:
                await matcher.finish(f"OCR识别失败: {str(e)}")

            if not data or not data.get("attrs"):
                await matcher.finish("无法识别图片中的三维属性")
            
            # 提取三维属性
            attrs = data["attrs"]
            vo, da, vi = attrs[0], attrs[1], attrs[2]
            
            break
    
    # 文本解析
    text_args = arg.extract_plain_text().strip().split()
    
    if vo == 0:
        # 纯文本模式
        if not text_args:
            await matcher.reject("请输入有效参数")
        
        if len(text_args) < 3:
            await matcher.finish("参数不足，请至少输入三维属性 (Vo Da Vi)")
        
        try:
            vo = int(text_args[0])
            da = int(text_args[1])
            vi = int(text_args[2])
            
            if len(text_args) >= 4:
                midterm_score = text_args[3]
            
            if len(text_args) >= 5:
                stars = int(text_args[4])
        except ValueError:
            await matcher.reject("请输入正确的数字")
    else:
        # 图片模式，检查文本中的参数
        if text_args:
            try:
                # 图片模式：先是期中分，再是星星数
                if len(text_args) >= 1:
                    midterm_score = text_args[0]
                if len(text_args) >= 2:
                    stars = int(text_args[1])
            except Exception:
                pass

    # 计算一般分数（显式计算：最终属性×2.1 + 期中评价分 + 期末评价分）
    # 计算最终属性（加上+120加成，受限于2800上限）
    vo_final = min(int(vo) + FINAL_EXAM_STAT_BONUS, ATTR_CAP)
    da_final = min(int(da) + FINAL_EXAM_STAT_BONUS, ATTR_CAP)
    vi_final = min(int(vi) + FINAL_EXAM_STAT_BONUS, ATTR_CAP)
    
    # 合计属性（最终）
    total_attr_final = vo_final + da_final + vi_final
    
    # 属性分 = 最终属性合计 × 2.1
    attr_score = int(total_attr_final * 2.1)
    
    # 期中评价分
    midterm_eval = _get_midterm_eval(int(midterm_score))
    
    # 期末评价分（暂时为0，强化月时期末还未进行）
    final_exam_eval = 0
    
    # 一般分数 = 属性分 + 期中评价分 + 期末评价分
    general_score = attr_score + midterm_eval + final_exam_eval
    
    if general_score > 0:
        # 计算强化月分数
        # 公式：强化月分数 = 一般分数 × 0.72 + 星星数 × 11.016（向下取整）
        strengthen_score = int(general_score * 0.72 + stars * 11.016)
        
        # 计算目前已有的强化月分数 = (属性分 + 期中评价分) * 0.72 + 星星数 * 11.016
        current_base_score = attr_score + midterm_eval
        current_strengthen_score = int(current_base_score * 0.72 + stars * 11.016)
        
        # 计算理论上限
        theoretical_base_score = attr_score + midterm_eval + 10400
        theoretical_max_strengthen = int(theoretical_base_score * 0.72 + stars * 11.016)
        
        msg = f"最终属性：Vo={vo_final} Da={da_final} Vi={vi_final} (合计={total_attr_final})\n"
        msg += f"期中分数：{midterm_score}\n"
        msg += f"星星数：{stars}\n\n"
        msg += "【目标分值表】\n"
        # rank表
        ranks = [
            ("SSS", 20000), ("SSS+", 23000), 
            ("23500", 23500), ("24000", 24000), 
            ("24500", 24500), ("25000", 25000), 
            ("25500", 25500), ("S4", 26000)
        ]

        for rank_name, rank_score in ranks:
            if rank_score <= current_strengthen_score:
                msg += f"{rank_name.ljust(5)}: 已达成\n"
            else:
                # 计算需要增加的强化月分数
                needed_strengthen = rank_score - current_strengthen_score
                
                # 需要的期末评价分 = (需要增加的强化月分) / 0.72 向上取整
                needed_final_eval = math.ceil(needed_strengthen / 0.72)
                
                # 反推期末分数（跨分数阶段权重自动处理）
                # 权重规则：
                #   1700~ 6200 eval: (eval-1700)/0.015
                #   6200~ 7200 eval: 300000 + (eval-6200)/0.01
                #   7200~ 8200 eval: 400000 + (eval-7200)/0.01
                #   8200~ 9000 eval: 500000 + (eval-8200)/0.008
                #   9000~10400 eval: 600000 + (eval-9000)/0.001
                required_final_score = _get_final_exam_score(needed_final_eval)
                
                if required_final_score == -1:
                    msg += f"{rank_name.ljust(5)}: ❌ 无法达成\n"
                else:
                    msg += f"{rank_name.ljust(5)}: {required_final_score:,}\n"
        
        msg += f"\n理论上限：{theoretical_max_strengthen}"
        await matcher.finish(msg)
    else:
        await matcher.finish("无法计算一般分数，请检查输入")


# ====================
# 4. 角色别称管理
# ====================

def _get_alias_config_path() -> Path:
    """别称 JSON 配置文件路径（与 ``calc.py`` 同目录）。"""
    return Path(__file__).resolve().parent / "character_aliases.json"


def _save_aliases() -> bool:
    """将 ``_CHARACTER_NAMES`` 写入 JSON 文件。"""
    config_path = _get_alias_config_path()
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(_CHARACTER_NAMES, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _load_aliases() -> bool:
    """从 JSON 文件加载角色别称并重建代号映射。"""
    global _CHARACTER_NAMES
    config_path = _get_alias_config_path()
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
                _CHARACTER_NAMES.update(loaded_data)
            _rebuild_character_code_map()
            return True
    except Exception:
        return False
    return False


# 启动时加载别称配置
_load_aliases()

# 添加角色别称
add_character_alias = on_command(
    "添加角色别称",
    aliases={"添加别称", "增加角色别称"},
    priority=20,
    block=True,
    permission=SUPERUSER
)

@add_character_alias.handle()
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    state: T_State,
    cmd_arg: Message = CommandArg(),
) -> None:
    if cmd_arg:
        state["alias_input"] = cmd_arg

@add_character_alias.got(
    "alias_input", prompt="请输入：角色全名 新别称\n示例：有村麻央 小麻央"
)
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    state: T_State,
    arg: Message = Arg("alias_input"),
) -> None:
    text = arg.extract_plain_text().strip()
    parts = text.split()
    
    if len(parts) < 2:
        await matcher.finish("格式错误！请输入：角色全名 新别称\n示例：有村麻央 小麻央")
    
    character_name = parts[0]
    new_alias = parts[1]
    
    # 检查角色是否存在
    if character_name not in _CHARACTER_NAMES:
        available_names = "、".join(_CHARACTER_NAMES.keys())
        await matcher.finish(f"未找到角色：{character_name}\n可用角色：{available_names}")
    
    # 检查别称是否已被使用
    for name, aliases in _CHARACTER_NAMES.items():
        if new_alias in aliases or new_alias.lower() in [a.lower() for a in aliases]:
            await matcher.finish(f"别称 {new_alias} 已被角色 {name} 使用")
    
    # 添加新别称
    _CHARACTER_NAMES[character_name].append(new_alias)
    CHARACTER_CODE_MAP[new_alias] = character_name
    
    # 保存到文件
    if _save_aliases():
        await matcher.finish(f"✅ 成功为 {character_name} 添加别称：{new_alias}\n当前所有别称：{', '.join(_CHARACTER_NAMES[character_name])}")
    else:
        await matcher.finish(f"⚠️ 别称已添加到内存，但保存到文件失败，重启后可能丢失")

# 删除角色别称
remove_character_alias = on_command(
    "删除角色别称",
    aliases={"删除别称", "移除角色别称"},
    priority=20,
    block=True,
    permission=SUPERUSER
)

@remove_character_alias.handle()
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    state: T_State,
    cmd_arg: Message = CommandArg(),
) -> None:
    if cmd_arg:
        state["remove_input"] = cmd_arg

@remove_character_alias.got(
    "remove_input", prompt="请输入：角色全名 要删除的别称\n示例：有村麻央 小麻央"
)
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    state: T_State,
    arg: Message = Arg("remove_input"),
) -> None:
    text = arg.extract_plain_text().strip()
    parts = text.split()
    
    if len(parts) < 2:
        await matcher.finish("格式错误！请输入：角色全名 要删除的别称\n示例：有村麻央 小麻央")
    
    character_name = parts[0]
    alias_to_remove = parts[1]
    
    # 检查角色是否存在
    if character_name not in _CHARACTER_NAMES:
        available_names = "、".join(_CHARACTER_NAMES.keys())
        await matcher.finish(f"未找到角色：{character_name}\n可用角色：{available_names}")
    
    # 检查别称是否存在
    if alias_to_remove not in _CHARACTER_NAMES[character_name]:
        await matcher.finish(f"角色 {character_name} 没有别称：{alias_to_remove}\n当前别称：{', '.join(_CHARACTER_NAMES[character_name])}")
    
    # 删除别称
    _CHARACTER_NAMES[character_name].remove(alias_to_remove)
    if alias_to_remove in CHARACTER_CODE_MAP:
        del CHARACTER_CODE_MAP[alias_to_remove]
    
    # 保存到文件
    if _save_aliases():
        await matcher.finish(f"✅ 成功删除 {character_name} 的别称：{alias_to_remove}\n剩余别称：{', '.join(_CHARACTER_NAMES[character_name])}")
    else:
        await matcher.finish(f"⚠️ 别称已从内存删除，但保存到文件失败，重启后可能恢复")

# 查看角色别称
list_character_alias = on_command(
    "角色别称列表",
    aliases={"查看角色别称", "别称列表"},
    priority=20,
    block=True
)

@list_character_alias.handle()
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    cmd_arg: Message = CommandArg(),
) -> None:
    # 检查是否指定了角色
    text = cmd_arg.extract_plain_text().strip()
    
    if text:
        # 查看特定角色的别称
        character_name = text
        if character_name not in _CHARACTER_NAMES:
            available_names = "、".join(_CHARACTER_NAMES.keys())
            await matcher.finish(f"未找到角色：{character_name}\n可用角色：{available_names}")
        
        aliases = _CHARACTER_NAMES[character_name]
        msg = f"【{character_name}】的别称：\n" + "、".join(aliases)
        await matcher.finish(msg)
    else:
        # 查看所有角色的别称
        msg = "【角色别称列表】\n"
        for name, aliases in _CHARACTER_NAMES.items():
            msg += f"\n{name}：\n  {', '.join(aliases)}\n"
        await matcher.finish(msg)