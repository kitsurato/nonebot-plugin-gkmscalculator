"""
插件配置：通过 NoneBot 驱动配置与环境变量注入。

未填写 ``api_key`` / ``model`` 时仍可加载插件；OCR 相关指令在调用时会提示配置。
"""

from nonebot import get_plugin_config
from pydantic import BaseModel, Field


class Config(BaseModel):
    """插件主配置。"""

    # --- AI 服务 ---
    provider: str = Field(default="siliconflow", description="API 服务提供商标识")
    api_key: str = Field(default="", description="API Key；留空则 OCR 不可用")
    api_url: str = Field(
        default="https://api.siliconflow.cn/v1",
        description="OpenAI 兼容格式的 Base URL",
    )
    model: str = Field(default="", description="模型名称")
    api_timeout: int = Field(30, description="API 请求超时时间(秒)")
    max_retries: int = Field(3, description="最大重试次数")

    # ---DEBUG配置---
    debug_mode: bool = Field(False, description="输出API服务配置信息")


config = get_plugin_config(Config)
