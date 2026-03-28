"""OCR 入口"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from .ocr_init import get_ocr_instance

current_directory = os.path.dirname(os.path.abspath(__file__))


def _get_ocr_provider_info() -> Tuple[str, str]:
    """返回当前配置的 OCR 提供商中文名与模型名（失败时返回占位）。"""
    try:
        from ..config import config

        provider_map = {
            "qwen": "通义千问",
            "siliconflow": "硅基流动",
            "volcengine": "火山引擎",
        }
        provider_name = provider_map.get(config.provider, "未知")
        model_name = config.model
        return provider_name, model_name
    except Exception:
        return "未知", "unknown"


def get_exam_data(url: str) -> Optional[Dict[str, Any]]:
    """
    识别考试/审查界面的属性数据。

    Returns:
        成功时含 ``attrs`` 键；失败时为 ``None``。
    """
    try:
        ocr = get_ocr_instance()
        provider_name, model_name = _get_ocr_provider_info()
        result = ocr.recognize_game_data(url)

        if result and sum(result["attrs"]) > 0:
            detected_mode = result.get("mode", "unknown")
            print(
                f"[OCR] get_exam_data - {provider_name} ({model_name}) "
                f"识别成功 (检测模式: {detected_mode})"
            )
            print(f"  属性: {result['attrs']}")
            return {"attrs": result["attrs"]}

        print("[错误] OCR 识别结果为空或无效")
        return None

    except Exception as e:
        print(f"[错误] 考试数据识别失败: {e}")
        return None


def detect_exam_screen(url: str) -> bool:
    """检测图片是否为考试/审查界面。"""
    try:
        ocr = get_ocr_instance()
        result = ocr.recognize_game_data(url)
        if result and result.get("mode") == "exam":
            return True
        return False
    except Exception as e:
        print(f"[警告] 考试界面检测失败: {e}")
        return False


def get_all_game_data(url: str) -> Optional[Dict[str, Any]]:
    """
    识别训练界面的完整数据（属性、加成、回合、SP 标记等）。

    Returns:
        训练模式返回识别结果；考试模式返回带默认加成/回合的兼容结构；失败为 ``None``。
    """
    try:
        ocr = get_ocr_instance()
        provider_name, model_name = _get_ocr_provider_info()
        result = ocr.recognize_game_data(url)

        if result and sum(result["attrs"]) > 0:
            detected_mode = result.get("mode", "unknown")
            print(
                f"[OCR] get_all_game_data - {provider_name} ({model_name}) "
                f"识别成功 (检测模式: {detected_mode})"
            )
            print(f"  属性: {result['attrs']}")

            if detected_mode == "exam":
                print("[提示] 检测到考试界面，建议使用 get_exam_data() 函数")
                return {
                    "attrs": result["attrs"],
                    "bonuses": [0.0, 0.0, 0.0],
                    "round": 5,
                    "sp_list": [0, 0, 0],
                }

            print(f"  加成: {result.get('bonuses', [])}")
            print(f"  周数: {result.get('round', 5)}")
            print(f"  SP: {result.get('sp_list', [])}")
            return result

        print("[错误] OCR 识别结果为空或无效")
        return None

    except Exception as e:
        print(f"[错误] OCR识别失败: {e}")
        return None


def getattrs(url: str) -> List[str]:
    """仅返回三维属性的字符串列表（识别失败返回空列表）。"""
    data = get_all_game_data(url)
    if not data:
        return []
    return [str(x) for x in data["attrs"]]
