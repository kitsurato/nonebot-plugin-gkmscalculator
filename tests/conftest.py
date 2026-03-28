"""在收集用例前初始化 NoneBot，以便加载插件包内的 get_plugin_config。"""
from __future__ import annotations

import nonebot

# 仅用于单元测试环境；不加载适配器与具体驱动
nonebot.init()
