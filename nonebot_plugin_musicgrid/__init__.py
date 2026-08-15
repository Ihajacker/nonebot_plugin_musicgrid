import re

from nonebot import get_driver
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="音乐墙",
    description="网易云歌单音乐墙生成器：粘贴歌单链接，生成 Topsters 风格专辑墙拼图",
    usage="音乐墙 <歌单链接或ID> [行x列] [notext]",
    type="application",
    homepage="https://github.com/Ihajacker/music-grid-generator",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

# 命令行环境下没有初始化的 driver，跳过指令注册
try:
    driver = get_driver()
except ValueError:
    driver = None

if driver is not None:
    from nonebot import on_command
    from nonebot.adapters import Message
    from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
    from nonebot.params import CommandArg

    from . import config
    from .fetch import parse_playlist_id, fetch_playlist, download_covers
    from .render import render_grid

    plugin_config = Config.parse_obj(driver.config.dict())

    music_grid = on_command("音乐墙", aliases={"musicgrid"}, priority=5, block=True)

    @music_grid.handle()
    async def music_grid_handle(event: MessageEvent, args: Message = CommandArg()):
        # 解析参数：歌单链接、可选 行x列、可选 notext
        cols = plugin_config.musicgrid_default_cols
        rows = plugin_config.musicgrid_default_rows
        include_text = True
        playlist = ""

        for part in args.extract_plain_text().strip().split():
            if part.lower() == "notext":
                include_text = False
            elif re.fullmatch(r"\d{1,2}[xX×]\d{1,2}", part):
                m = re.fullmatch(r"(\d{1,2})[xX×](\d{1,2})", part)
                rows, cols = map(int, m.groups())
            else:
                playlist = part

        if not playlist:
            await music_grid.finish("用法: 音乐墙 <歌单链接或ID> [行x列] [notext]")
        if not (1 <= cols <= 10 and 1 <= rows <= 10):
            await music_grid.finish("行列数需在 1~10 之间")

        try:
            playlist_id = parse_playlist_id(playlist)
            tracks = await fetch_playlist(playlist_id)
        except Exception as e:
            await music_grid.finish(f"获取歌单失败: {e}")

        tracks = tracks[: cols * rows]
        if not tracks:
            await music_grid.finish("歌单为空或不存在")

        try:
            images = await download_covers([t["pic"] for t in tracks], plugin_config.musicgrid_concurrency)
            font_path = config.resolve_font_path(plugin_config.musicgrid_font_path)
            data = render_grid(images, tracks, cols, rows, include_text, font_path)
        except Exception as e:
            await music_grid.finish(f"生成失败: {e}")

        await music_grid.finish(MessageSegment.image(data))
