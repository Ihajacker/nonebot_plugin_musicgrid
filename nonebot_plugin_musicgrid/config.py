import os

from pydantic import BaseModel, Extra

# 命令行模式使用的默认值
DEFAULT_COLS = 5
DEFAULT_ROWS = 5
CONCURRENCY = 5

_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
BUNDLED_FONT = os.path.join(_FONT_DIR, "LXGWWenKaiScreen.ttf")
SYSTEM_FONT = r"C:\Windows\Fonts\msyh.ttc"


class Config(BaseModel, extra=Extra.ignore):
    # 自定义字体路径，留空时自动查找
    musicgrid_font_path: str = ""
    musicgrid_default_cols: int = DEFAULT_COLS
    musicgrid_default_rows: int = DEFAULT_ROWS
    musicgrid_concurrency: int = CONCURRENCY


def resolve_font_path(font_path=""):
    # 查找可用字体：用户配置 -> 项目自带 -> 系统字体
    for path in (font_path, BUNDLED_FONT, SYSTEM_FONT):
        if path and os.path.exists(path):
            return path
    return BUNDLED_FONT
