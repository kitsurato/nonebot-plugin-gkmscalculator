# nonebot-plugin-gkmscalculator

学园偶像大师算分插件：产出评级（算分）、训练属性（算属性）、强化月算分、角色别称管理；支持截图 OCR。

## 安装

在 NoneBot2 项目根目录执行：

```bash
nb plugin install nonebot-plugin-gkmscalculator
```

或使用包管理器：

```bash
pip install nonebot-plugin-gkmscalculator
```

在 `pyproject.toml` 的 `[tool.nonebot]` 中加载插件（若使用 nb-cli 管理）：

```toml
plugins = ["nonebot_plugin_gkmsCalculator"]
```

## 配置

在 NoneBot 环境配置（如 `.env`）中设置插件配置项，前缀与 NoneBot 全局配置一致，例如：

| 配置项 | 说明 | 默认 |
|--------|------|------|
| `api_key` | 视觉/OCR 所用 API Key | 空（未配置时 OCR 不可用） |
| `api_url` | OpenAI 兼容接口 Base URL | `https://api.siliconflow.cn/v1` |
| `model` | 模型名 | 空 |
| `provider` | 提供商标识 | `siliconflow` |
| `api_timeout` | 请求超时（秒） | `30` |
| `max_retries` | 最大重试次数 | `3` |
| `debug_mode` | 调试日志 | `false` |

具体字段名以项目中 `Config` 类及 NoneBot 驱动配置规则为准。

## 用法概要

- **算分**：`算分 Vo Di Vi [期中分]`，支持截图  
- **算属性**：`算属性 [角色代号] 红 蓝 黄 红% 蓝% 黄% [道具] [第几次训练]`，支持截图  
- **强化月算分**：`强化月算分 Vo Da Vi [期中分] [星星数]`，支持截图  
- **别称**：`角色别称列表`、`添加角色别称`、`删除角色别称`（后两者需超级用户）

完整说明见插件元数据 `usage` 或源码 `__init__.py`。

本项目布局遵循 [NoneBot 插件发布指南](https://nonebot.dev/docs/developer/plugin-publishing) 与 [RF-Tar-Railt/nonebot-plugin-template](https://github.com/RF-Tar-Railt/nonebot-plugin-template)（PDM、`src` 布局、`pdm-backend`）。

```bash
pdm sync -G dev
pdm run test
pdm build
```

发布：将 `pyproject.toml` 的 `version` 与 Git 标签（如 `v0.2.0`）对齐后推送 `v*`，由 `.github/workflows/release.yml` 执行 `pdm publish`。请先在 [PyPI Trusted Publisher](https://pypi.org/manage/account/publishing/) 绑定本仓库，并把 `src/nonebot_plugin_gkmsCalculator/__init__.py` 中 `homepage` 与 `pyproject.toml` 的 `[project.urls]` 改为你自己的项目主页。

### 与旧版「扁平插件目录」的对接

若此前把整个文件夹直接放在机器人的 `plugins/` 下，迁移后请任选其一：在本仓库根目录执行 `pip install -e .` 后按模块名加载，或使用 `nb plugin install` / `pip install` 安装发布包。勿再将 `src` 子目录单独当作插件路径。

## 许可证

MIT
