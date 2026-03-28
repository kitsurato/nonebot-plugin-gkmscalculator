from nonebot.plugin import PluginMetadata

from .calc import (
    add_character_alias,
    calc_highattr,
    calc_rank,
    calc_strengthen_month,
    list_character_alias,
    remove_character_alias,
)
from .config import Config

__version__ = "0.2.0"
__plugin_meta__ = PluginMetadata(
    name="学马算分",
    description="学园偶像大师算分计算器，支持产出等级计算、属性训练计算、强化月算分及角色别称管理",
    usage="""
【基础功能】
1. 算分 - 计算产出等级（Produce Rank）
   格式：算分 Vo Di Vi [期中分]
   支持：发送截图自动识别

2. 算属性 - 训练属性计算
   格式：算属性 [角色名称/别名] 红 蓝 黄 红% 蓝% 黄% [道具] [第几次训练]
   支持：发送截图自动识别

3. 强化月算分 - 强化月分数计算
   格式：强化月算分 Vo Da Vi [期中分] [星星数]
   支持：发送截图自动识别

4. 角色别称列表 / 查看角色别称 / 别称列表
   查看所有或指定角色的别称
   示例：角色别称列表 角色全名

5. 添加角色别称 / 添加别称（仅管理员）
   为角色添加新别称
   格式：添加角色别称 角色全名 新别称

6. 删除角色别称 / 删除别称（仅管理员）
   删除角色的某个别称
   格式：删除角色别称 角色全名 别称
""".strip(),

    type="application",
    homepage="https://pypi.org/project/nonebot-plugin-gkmscalculator/",
    config=Config,
    supported_adapters={"~onebot.v11"},
)