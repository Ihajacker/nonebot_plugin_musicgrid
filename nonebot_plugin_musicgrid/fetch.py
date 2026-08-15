import asyncio
import io
import re

import httpx
from PIL import Image

METING_API = "https://api.injahow.cn/meting/"


def parse_playlist_id(text):
    # 从分享链接提取歌单ID，纯数字则直接使用
    m = re.search(r"[?&]id=(\d+)", text)
    if m:
        return m.group(1)
    if text.strip().isdigit():
        return text.strip()
    raise ValueError("无法从输入中解析出歌单ID")


async def fetch_playlist(playlist_id):
    # 拉取歌单，返回歌曲列表
    params = {"server": "netease", "type": "playlist", "id": playlist_id}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get(METING_API, params=params)
        resp.raise_for_status()
        data = resp.json()
    if not isinstance(data, list) or not data:
        raise ValueError("歌单为空或不存在")
    return [
        {"name": item.get("name", ""), "artist": item.get("artist", ""), "pic": item.get("pic", "")}
        for item in data
    ]


def _make_square(image, size):
    # 居中裁方后缩放
    width, height = image.size
    edge = min(width, height)
    left = (width - edge) // 2
    top = (height - edge) // 2
    return image.crop((left, top, left + edge, top + edge)).resize((size, size), Image.LANCZOS)


def _placeholder(size=200):
    return Image.new("RGB", (size, size), (50, 50, 50))


async def _download_cover(client, sem, url):
    # 单张封面下载，失败时用深灰块占位
    if not url:
        return _placeholder()
    async with sem:
        try:
            resp = await client.get(url, timeout=20)
            resp.raise_for_status()
            return _make_square(Image.open(io.BytesIO(resp.content)), 200)
        except Exception:
            return _placeholder()


async def download_covers(pic_urls, concurrency=5):
    # 并发下载封面，限流防止请求过猛
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [_download_cover(client, sem, url) for url in pic_urls]
        return await asyncio.gather(*tasks)
