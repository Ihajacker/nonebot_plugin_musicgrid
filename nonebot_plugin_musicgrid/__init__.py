import re

from nonebot import get_driver
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="音乐墙",
    description="网易云歌单音乐墙生成器：粘贴歌单链接，生成 Topsters 风格专辑墙拼图",
    usage="音乐墙 <歌单链接或ID> [行x列] [notext] [album] [dedup]",
    type="application",
    homepage="https://github.com/Ihajacker/music-grid-generator",
    config=Config,
    supported_adapters={"~onebot.v11", "~qq"},
)

# 命令行环境下没有初始化的 driver，跳过指令注册
try:
    driver = get_driver()
except ValueError:
    driver = None

if driver is not None:
    from nonebot import on_command
    from nonebot.adapters import Event, Message
    from nonebot.params import CommandArg

    from . import config
    from .fetch import parse_playlist_id, get_tracks, download_covers
    from .render import render_grid

    plugin_config = Config.parse_obj(driver.config.dict())

    def make_image_segment(event, data):
        # qq 官方适配器用 file_image，其余按 onebot 的 image 发送
        try:
            from nonebot.adapters.qq import Event as QQEvent

            if isinstance(event, QQEvent):
                from nonebot.adapters.qq import MessageSegment

                return MessageSegment.file_image(data)
        except ImportError:
            pass
        from nonebot.adapters.onebot.v11 import MessageSegment

        return MessageSegment.image(data)

    music_grid = on_command("音乐墙", aliases={"musicgrid"}, priority=5, block=True)

    @music_grid.handle()
    async def music_grid_handle(event: Event, args: Message = CommandArg()):
        # 解析参数：歌单链接、可选 行x列、可选 notext/album/dedup
        cols = plugin_config.musicgrid_default_cols
        rows = plugin_config.musicgrid_default_rows
        include_text = True
        album_mode = False
        dedup = False
        playlist = ""

        for part in args.extract_plain_text().strip().split():
            if part.lower() == "notext":
                include_text = False
            elif part.lower() == "album":
                album_mode = True
            elif part.lower() == "dedup":
                dedup = True
            elif re.fullmatch(r"\d{1,2}[xX×]\d{1,2}", part):
                m = re.fullmatch(r"(\d{1,2})[xX×](\d{1,2})", part)
                rows, cols = map(int, m.groups())
            else:
                playlist = part

        if not playlist:
            usage = (
                "音乐墙使用说明\n"
                "音乐墙 <歌单链接或歌单ID> [参数]\n\n"
                "可选参数:\n"
                "行x列   拼图尺寸，如 3x3，默认 5x5\n"
                "notext  不生成右侧文字列表\n"
                "album   专辑名模式（显示真实专辑名）\n"
                "dedup   去重（跳过重复专辑/封面并凑满）\n"
                "默认为歌曲名模式，加 album 切换为专辑名模式\n\n"
                "示例:\n"
                "音乐墙 3778678\n"
                "音乐墙 3778678 3x3 album dedup"
            )
            await music_grid.finish(usage)
        if not (1 <= cols <= 10 and 1 <= rows <= 10):
            await music_grid.finish("行列数需在 1~10 之间")

        try:
            playlist_id = parse_playlist_id(playlist)
            tracks = await get_tracks(playlist_id, cols * rows, album=album_mode, dedup=dedup)
            text_key = "album" if album_mode else "name"
        except Exception as e:
            await music_grid.finish(f"获取歌单失败: {e}")

        tracks = tracks[: cols * rows]
        if not tracks:
            await music_grid.finish("歌单为空或不存在")

        try:
            images = await download_covers([t["pic"] for t in tracks], plugin_config.musicgrid_concurrency)
            font_path = config.resolve_font_path(plugin_config.musicgrid_font_path)
            data = render_grid(images, tracks, cols, rows, include_text, font_path, text_key)
        except Exception as e:
            await music_grid.finish(f"生成失败: {e}")

        await music_grid.finish(make_image_segment(event, data))
