"""
统一的 OCR 图片识别模块（异步 HTTP：httpx）
支持通义千问、硅基流动、火山引擎三种提供商
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
from typing import Any, Dict, Optional, Tuple

import httpx

from ..config import config

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """速率限制错误"""

    pass


def _mime_from_content_type(content_type: str) -> str:
    content_type = (content_type or "image/jpeg").lower()
    if "png" in content_type:
        return "image/png"
    if "gif" in content_type:
        return "image/gif"
    if "webp" in content_type:
        return "image/webp"
    return "image/jpeg"


class UnifiedOCR:
    """统一的 OCR 识别类，支持多个提供商（异步 httpx）。"""

    SUPPORTED_PROVIDERS = ["qwen", "siliconflow", "volcengine"]

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.provider = provider or config.provider
        if self.provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"不支持的OCR提供商: {self.provider}, 支持的提供商: {self.SUPPORTED_PROVIDERS}"
            )

        self.api_key = api_key or config.api_key
        self.model = model or config.model
        self.base_url = str(config.api_url).rstrip("/")

        if not self.api_key:
            raise ValueError(
                "❌api_key未设置或为空\n请设置环境变量: api_key=your_key"
            )

        if config.debug_mode:
            logger.debug(
                f"[UnifiedOCR] 初始化完成 - 提供商: {self.provider}, 模型: {self.model}"
            )

    @staticmethod
    def _encode_local_file_to_base64(image_source: str) -> Tuple[str, int, str]:
        """本地路径读取并编码为 base64。"""
        if not (
            image_source.startswith("/")
            or (len(image_source) > 1 and image_source[1] == ":")
        ):
            image_source = os.path.abspath(image_source)

        if not os.path.exists(image_source):
            raise FileNotFoundError(f"图片文件不存在: {image_source}")

        file_ext = os.path.splitext(image_source)[1].lower()
        mime_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_type_map.get(file_ext, "image/jpeg")

        with open(image_source, "rb") as f:
            image_data = f.read()

        try:
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            base64.b64decode(image_b64)
        except Exception as e:
            raise ValueError(f"Base64编码失败: {e}") from e

        return image_b64, len(image_data), mime_type

    async def _load_image_as_base64_async(self, image_source: str) -> Tuple[str, int, str]:
        """
        加载图片为 base64：URL 用 httpx 异步下载，本地文件用线程池避免阻塞事件循环。
        """
        if image_source.startswith("http://") or image_source.startswith("https://"):
            try:
                timeout = httpx.Timeout(10.0, connect=10.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(image_source)
                    response.raise_for_status()
                    image_data = response.content
                    mime_type = _mime_from_content_type(
                        response.headers.get("content-type", "image/jpeg")
                    )
                    image_b64 = base64.b64encode(image_data).decode("utf-8")
                    return image_b64, len(image_data), mime_type
            except httpx.HTTPError as e:
                raise ValueError(f"下载URL图片失败: {e}") from e

        return await asyncio.to_thread(
            UnifiedOCR._encode_local_file_to_base64, image_source
        )

    def _build_prompt(self) -> str:
        """构建识别 prompt。"""
        return """请仔细分析下图，判断为训练模式还是考试模式。

【重要】首先提取三维属性数值（这是最重要的）：
- Vo（ボーカル） - 通常是红色标记
- Da（ダンス） - 通常是蓝色标记  
- Vi（ビジュアル） - 通常是黄色标记
这三个数值通常是3-4位数字。

【人物识别】
识别图中的人物并按照下表返回人物标号：
花海咲季：1     辅助判断信息（红发）
葛城莉莉娅：2   辅助判断信息（白发）
筱泽广：3       辅助判断信息（茶色发）
十王星南：4     辅助判断信息（金发）
花海佑芽：5     辅助判断信息（棕发）
姬崎莉波：6     辅助判断信息（棕发）
月村手毬：7     辅助判断信息（蓝发）
藤田琴音：8     辅助判断信息（黄发）
有村麻央：9     辅助判断信息（粉紫发）
仓本千奈：10    辅助判断信息（棕发）
紫云清夏：11    辅助判断信息（橙发）
秦谷美铃：12    辅助判断信息（蓝紫发）
雨夜燕：13      辅助判断信息（黑发）
如果识别到没在上表中的人物或者无法识别，请返回13

【考试/审查模式的特点】
- 显示合格条件或审查基准
- 三个属性数值在左侧按竖排列
- 无属性百分比加成

【训练模式的特点】
- 底部有三个颜色块（红/蓝/黄）代表三维属性
- 每个属性块下方显示属性百分比加成
- 显示训练周数信息
- 某些属性上方可能有紫色SP标记

【SP识别】
- 在训练属性颜色块上有紫色/紫粉色渐变图标表示有SP

【训练次数】
距期中/中期6周：1
距期中/中期3周：2
距最终6周：3
距最终4周：4
距最终2周：5

【返回格式要求】
模式：[训练/考试]
Vo：[3-4位数字]
Da：[3-4位数字]
Vi：[3-4位数字]
人物标号：[1-13的数字]

如果是训练模式，继续返回：
Vo加成：[百分比数字，如30.1]
Da加成：[百分比数字，如34.9]
Vi加成：[百分比数字，如18.6]
训练次数：[1-5的数字，或从文本推断]
Vo_SP：[有/无]
Da_SP：[有/无]
Vi_SP：[有/无]

严格按照上述格式返回，每行一个数据，不要添加其他说明文字。"""

    def _build_payload(
        self, image_b64: str, mime_type: str, prompt: str
    ) -> Dict[str, Any]:
        if self.provider in ["qwen", "siliconflow"]:
            return {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_b64}"
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 500,
            }

        if self.provider == "volcengine":
            return {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_b64}"
                                },
                            },
                        ],
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 500,
            }

        raise ValueError(f"未知提供商: {self.provider}")

    async def recognize_game_data_async(
        self, image_source: str
    ) -> Optional[Dict[str, Any]]:
        image_b64, _image_size, mime_type = await self._load_image_as_base64_async(
            image_source
        )

        prompt = self._build_prompt()
        payload = self._build_payload(image_b64, mime_type, prompt)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        timeout = httpx.Timeout(
            float(config.api_timeout), connect=float(config.api_timeout)
        )

        try:
            if config.debug_mode:
                logger.debug(
                    f"[UnifiedOCR] 发送请求 - 提供商: {self.provider}, 模型: {self.model}"
                )

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.base_url, json=payload, headers=headers
                )
                response.raise_for_status()
                result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                text_content = result["choices"][0]["message"]["content"]

                if config.debug_mode:
                    logger.debug(
                        f"[UnifiedOCR] 识别成功 - 返回长度: {len(text_content)}"
                    )

                logger.info(f"[UnifiedOCR] {self.provider} 识别成功")
                return self._parse_game_data(text_content)

            logger.warning("[UnifiedOCR] API返回为空")
            return None

        except httpx.HTTPStatusError as e:
            error_msg = f"API请求失败: {e}"
            logger.error(f"[UnifiedOCR] {error_msg}")
            if e.response is not None:
                logger.error(f"[UnifiedOCR] 状态码: {e.response.status_code}")
                logger.error(f"[UnifiedOCR] 响应: {e.response.text[:500]}")
            return None
        except httpx.RequestError as e:
            error_msg = f"API请求失败: {str(e)}"
            logger.error(f"[UnifiedOCR] {error_msg}")
            return None

    def _parse_game_data(self, text: str) -> Optional[Dict[str, Any]]:
        is_exam = "考试" in text or "exam" in text.lower()
        is_training = "训练" in text or "training" in text.lower()

        character_id = 13
        character_match = re.search(r"人物标号[：:\s]*(\d{1,2})", text)
        if character_match:
            character_id = int(character_match.group(1))
            if not (1 <= character_id <= 13):
                character_id = 13

        if is_exam:
            data = {"attrs": [0, 0, 0], "mode": "exam"}

            vo_match = re.search(r"Vo[：:\s]*(\d{3,4})", text) or re.search(
                r"Vo\s*:?\s*(\d{3,4})", text
            )
            da_match = re.search(r"Da[：:\s]*(\d{3,4})", text) or re.search(
                r"Da\s*:?\s*(\d{3,4})", text
            )
            vi_match = re.search(r"Vi[：:\s]*(\d{3,4})", text) or re.search(
                r"Vi\s*:?\s*(\d{3,4})", text
            )

            if vo_match:
                data["attrs"][0] = int(vo_match.group(1))
            if da_match:
                data["attrs"][1] = int(da_match.group(1))
            if vi_match:
                data["attrs"][2] = int(vi_match.group(1))

            if sum(data["attrs"]) == 0:
                numbers = re.findall(r"\b(\d{3,4})\b", text)
                if len(numbers) >= 3:
                    data["attrs"] = [int(numbers[0]), int(numbers[1]), int(numbers[2])]

            logger.info(f"[OCR] 考试模式解析: attrs={data['attrs']}")
            return data

        if is_training:
            data = {
                "attrs": [0, 0, 0],
                "bonuses": [0.0, 0.0, 0.0],
                "round": 5,
                "sp_list": [0, 0, 0],
                "mode": "training",
                "character_id": character_id,
            }

            vo_match = re.search(r"Vo[：:\s]*(\d{3,4})", text)
            if not vo_match:
                vo_match = re.search(r"Vo\s*:\s*(\d{3,4})", text)
            if not vo_match:
                vo_match = re.search(r"Vo[^0-9]*(\d{3,4})", text)

            da_match = re.search(r"Da[：:\s]*(\d{3,4})", text)
            if not da_match:
                da_match = re.search(r"Da\s*:\s*(\d{3,4})", text)
            if not da_match:
                da_match = re.search(r"Da[^0-9]*(\d{3,4})", text)

            vi_match = re.search(r"Vi[：:\s]*(\d{3,4})", text)
            if not vi_match:
                vi_match = re.search(r"Vi\s*:\s*(\d{3,4})", text)
            if not vi_match:
                vi_match = re.search(r"Vi[^0-9]*(\d{3,4})", text)

            if vo_match:
                data["attrs"][0] = int(vo_match.group(1))
            if da_match:
                data["attrs"][1] = int(da_match.group(1))
            if vi_match:
                data["attrs"][2] = int(vi_match.group(1))

            if sum(data["attrs"]) == 0:
                numbers = re.findall(r"\b(\d{3,4})\b", text)
                if len(numbers) >= 3:
                    data["attrs"] = [int(numbers[0]), int(numbers[1]), int(numbers[2])]

            vo_bonus_match = re.search(r"Vo加成[：:\s]*(\d{1,2}\.?\d*)", text)
            if not vo_bonus_match:
                vo_bonus_match = re.search(
                    r"Vo[^加]*加成[：:\s]*(\d{1,2}\.?\d*)", text
                )
            if vo_bonus_match:
                data["bonuses"][0] = float(vo_bonus_match.group(1))

            da_bonus_match = re.search(r"Da加成[：:\s]*(\d{1,2}\.?\d*)", text)
            if not da_bonus_match:
                da_bonus_match = re.search(
                    r"Da[^加]*加成[：:\s]*(\d{1,2}\.?\d*)", text
                )
            if da_bonus_match:
                data["bonuses"][1] = float(da_bonus_match.group(1))

            vi_bonus_match = re.search(r"Vi加成[：:\s]*(\d{1,2}\.?\d*)", text)
            if not vi_bonus_match:
                vi_bonus_match = re.search(
                    r"Vi[^加]*加成[：:\s]*(\d{1,2}\.?\d*)", text
                )
            if vi_bonus_match:
                data["bonuses"][2] = float(vi_bonus_match.group(1))

            vo_sp_match = re.search(r"Vo_SP[：:\s]*(有|无|是|否)", text)
            if vo_sp_match and vo_sp_match.group(1) in ["有", "是"]:
                data["sp_list"][0] = 1

            da_sp_match = re.search(r"Da_SP[：:\s]*(有|无|是|否)", text)
            if da_sp_match and da_sp_match.group(1) in ["有", "是"]:
                data["sp_list"][1] = 1

            vi_sp_match = re.search(r"Vi_SP[：:\s]*(有|无|是|否)", text)
            if vi_sp_match and vi_sp_match.group(1) in ["有", "是"]:
                data["sp_list"][2] = 1

            week_match = re.search(r"训练次数[：:\s]*(\d+)", text)
            if not week_match:
                week_match = re.search(r"返回[：:\s]*(\d+)", text)
            if week_match:
                weeks = int(week_match.group(1))
                if 1 <= weeks <= 5:
                    data["round"] = weeks

            logger.info(
                f"[OCR] 训练模式解析: attrs={data['attrs']}, bonuses={data['bonuses']}, "
                f"round={data['round']}, sp={data['sp_list']}, character_id={data['character_id']}"
            )
            return data

        logger.warning("[OCR] 无法判断模式")
        return None

    def recognize_game_data(self, image_source: str) -> Optional[Dict[str, Any]]:
        """
        同步包装：在无运行中事件循环的线程内调用异步实现（如 asyncio.to_thread）。
        """
        return asyncio.run(self.recognize_game_data_async(image_source))


__all__ = [
    "UnifiedOCR",
    "RateLimitError",
]
