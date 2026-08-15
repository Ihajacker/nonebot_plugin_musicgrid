import asyncio
import io
import re
from itertools import islice

import httpx
from PIL import Image

METING_API = "https://api.injahow.cn/meting/"
NETEASE_API = "https://music.163.com/api"
NETEASE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://music.163.com/",
}


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


def _chunks(seq, size):
    # 按 size 切分列表
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def iter_unique(tracks, get_keys):
    # 任一去重键重复则跳过，保留首次出现
    seen = set()
    for t in tracks:
        keys = get_keys(t)
        if any(k in seen for k in keys):
            continue
        seen.update(keys)
        yield t


def _song_keys(t):
    return (t.get("pic", ""), (t.get("artist", ""), t.get("name", "")))


def _album_keys(t):
    return (t.get("album_id") or t.get("pic", ""), (t.get("artist", ""), t.get("album", "")))


async def fetch_playlist_album(playlist_id, limit=100, dedup=False, max_scan=500):
    # 专辑名模式：网易云官方 API，返回 [{name, artist, album, album_id, pic}]
    async with httpx.AsyncClient(timeout=20, headers=NETEASE_HEADERS) as client:
        resp = await client.get(f"{NETEASE_API}/v3/playlist/detail", params={"id": playlist_id})
        resp.raise_for_status()
        data = resp.json()

    track_ids = data.get("playlist", {}).get("trackIds")
    if data.get("code") != 200 or not track_ids:
        raise ValueError("歌单不存在或未公开")
    # 去重时向后多扫一些，凑满 limit 首
    scan = max_scan if dedup else limit
    ids = [item["id"] for item in track_ids[:scan]]

    tracks = []
    async with httpx.AsyncClient(timeout=20, headers=NETEASE_HEADERS) as client:
        for batch in _chunks(ids, 100):
            params = {"ids": f"[{','.join(map(str, batch))}]"}
            resp = await client.get(f"{NETEASE_API}/song/detail", params=params)
            resp.raise_for_status()
            detail = resp.json()
            for song in detail.get("songs", []):
                album = song.get("album", {})
                tracks.append(
                    {
                        "name": song.get("name", ""),
                        "artist": "/".join(a.get("name", "") for a in song.get("artists", [])),
                        "album": album.get("name", ""),
                        "album_id": album.get("id", ""),
                        "pic": album.get("picUrl", ""),
                    }
                )
    if not tracks:
        raise ValueError("歌单为空或获取失败")
    if dedup:
        return list(islice(iter_unique(tracks, _album_keys), limit))
    return tracks[:limit]


async def get_tracks(playlist_id, count, album=False, dedup=False):
    # 拉取歌曲并处理去重，凑满 count 首
    if album:
        return await fetch_playlist_album(playlist_id, count, dedup=dedup)
    tracks = await fetch_playlist(playlist_id)
    if dedup:
        return list(islice(iter_unique(tracks, _song_keys), count))
    return tracks[:count]


async def download_covers(pic_urls, concurrency=5):
    # 并发下载封面，限流防止请求过猛
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [_download_cover(client, sem, url) for url in pic_urls]
        return await asyncio.gather(*tasks)
