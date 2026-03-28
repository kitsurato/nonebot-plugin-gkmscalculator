"""异步下载图片（httpx），供需要自行拉取图片 URL 的场景使用。"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

import cv2
import httpx
import numpy as np


async def getpic(pic_url: str, *, timeout: float = 30.0, verify: bool = False) -> Optional[Any]:
    """
    异步 GET 图片并解码为 OpenCV BGR 图像。

    Args:
        pic_url: 图片 URL。
        timeout: 请求超时（秒）。
        verify: 是否校验 TLS 证书（部分 CDN 需 False，生产环境建议 True）。
    """
    timeout_cfg = httpx.Timeout(timeout, connect=min(10.0, timeout))
    async with httpx.AsyncClient(timeout=timeout_cfg, verify=verify) as client:
        response = await client.get(pic_url)

    if response.status_code != 200:
        print(f"Failed to download image. Status code: {response.status_code}")
        return None

    image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return image


def getpic2(__pic_url: str) -> Optional[Any]:
    """从与当前模块同目录的相对路径读取图片（本地文件）。"""
    current_directory = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_directory, __pic_url)
    return cv2.imread(path)


if __name__ == "__main__":
    _url = (
        "http://multimedia.nt.qq.com.cn/download?appid=1406&fileid=CgoyNTExNDYyNTA4EhQfVzcAN61BTyouY_v7PhboAGHN_BjJ5Qkg_gooyvuciOLQiAMyBHByb2RQgLsv&spec=0&rkey=CAESKBkcro_MGujokCQEjS-KTYkIVJASmREiXxD3z7jj0Bs6IXK_pGbJH3s"
    )
    ret = asyncio.run(getpic(_url))
    print(ret)
