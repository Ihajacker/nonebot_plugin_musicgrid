import argparse
import asyncio
import sys

from . import config
from .fetch import parse_playlist_id, get_tracks, download_covers
from .render import render_grid


async def main(args):
    playlist_id = parse_playlist_id(args.playlist)
    print(f"歌单ID: {playlist_id}")

    count = args.cols * args.rows
    tracks = await get_tracks(playlist_id, count, album=args.album, dedup=args.dedup)
    text_key = "album" if args.album else "name"
    print(f"获取到 {len(tracks)} 首歌曲")

    print(f"下载 {len(tracks)} 张封面...")
    images = await download_covers([t["pic"] for t in tracks], config.CONCURRENCY)

    data = render_grid(images, tracks, args.cols, args.rows, not args.no_text, config.resolve_font_path(), text_key)
    with open(args.output, "wb") as f:
        f.write(data)
    print(f"已生成: {args.output} ({args.cols}x{args.rows})")


def build_parser():
    parser = argparse.ArgumentParser(description="网易云歌单音乐墙生成器")
    parser.add_argument("playlist", help="歌单分享链接或歌单ID")
    parser.add_argument("-c", "--cols", type=int, default=config.DEFAULT_COLS)
    parser.add_argument("-r", "--rows", type=int, default=config.DEFAULT_ROWS)
    parser.add_argument("--no-text", action="store_true", help="不生成右侧文字列表")
    parser.add_argument("--album", action="store_true", help="专辑名模式（使用网易云官方 API）")
    parser.add_argument("--dedup", action="store_true", help="去重：跳过重复封面/专辑，向后凑满")
    parser.add_argument("-o", "--output", default="music_grid.jpg")
    return parser


def run(argv=None):
    args = build_parser().parse_args(argv)
    if not (1 <= args.cols <= 10 and 1 <= args.rows <= 10):
        print("行列数需在 1~10 之间")
        sys.exit(1)
    try:
        asyncio.run(main(args))
    except Exception as e:
        print(f"生成失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
