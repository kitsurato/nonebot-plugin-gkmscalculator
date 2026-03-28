"""
OCR 模块初始化和选择器
根据环境变量自动选择合适的OCR实现（通义千问、硅基流动或火山引擎）
"""

from ..config import config


def get_ocr_instance(provider: str = None, **kwargs):
    """
    获取OCR实例
    
    Args:
        provider: OCR提供商，可选 "qwen"、"siliconflow" 或 "volcengine"（不指定则从环境变量读取）
        **kwargs: 传递给OCR类的其他参数（如 api_key, model 等）
        
    Returns:
        UnifiedOCR实例
    """
    # 动态读取提供商配置
    provider = provider or config.provider
    
    from .unified_ocr import UnifiedOCR
    
    if config.debug_mode:
        print(f"[调试] 使用 UnifiedOCR - 提供商: {provider}")
    
    return UnifiedOCR(provider=provider, **kwargs)


def print_ocr_config():
    """打印当前OCR配置"""
    try:
        from ..config import config
        
        print("=" * 50)
        print("当前 OCR 配置")
        print("=" * 50)
        print(f"活跃提供商: {config.provider}")
        print(f"  模型: {config.model}")
        print(f"  URL: {config.api_url}")
        print(f"  API Key: {config.api_key}")
        print()
        print(f"API超时: {config.api_timeout}秒")
        print(f"最大重试: {config.max_retries}次")
        print()
        
    except ImportError:
        print("[警告] 无法读取配置文件")


# 导出公共API
__all__ = [
    'get_ocr_instance',
    'print_ocr_config',
]
