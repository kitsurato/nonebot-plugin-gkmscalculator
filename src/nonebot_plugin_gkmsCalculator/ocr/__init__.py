"""
OCR 模块
包含OCR识别相关的所有功能
"""

from .ocr_init import get_ocr_instance, print_ocr_config
from .OCRattrs import get_all_game_data, detect_exam_screen, get_exam_data, getattrs
from .unified_ocr import UnifiedOCR, RateLimitError

__all__ = [
    'get_ocr_instance',
    'print_ocr_config',
    'get_all_game_data',
    'detect_exam_screen',
    'get_exam_data',
    'getattrs',
    'UnifiedOCR',
    'RateLimitError',
]
