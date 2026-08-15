import io
import os

from PIL import Image, ImageDraw, ImageFont

IMG_SIZE = 200
TEXT_WIDTH = 450
TEXT_MAX_WIDTH = 400
BG_DARK = "#151515"
BG_LIGHT = "#ffffff"


def _truncate_to_width(text, font, max_width):
    # 超宽截断并加省略号
    if font.getlength(text) <= max_width:
        return text
    while font.getlength(text + "…") > max_width and text:
        text = text[:-1]
    return text + "…"


def render_grid(images, tracks, cols, rows, include_text, font_path):
    # 封面网格拼图，可选右侧文字列表
    canvas_width = cols * IMG_SIZE + (TEXT_WIDTH if include_text else 0)
    canvas_height = rows * IMG_SIZE
    background = BG_DARK if include_text else BG_LIGHT
    canvas = Image.new("RGB", (canvas_width, canvas_height), background)

    for i, img in enumerate(images[: cols * rows]):
        col, row = i % cols, i // cols
        canvas.paste(img, (col * IMG_SIZE, row * IMG_SIZE))

    lines = [f"{i + 1}. {t['artist']} - {t['name']}" for i, t in enumerate(tracks[: cols * rows])]
    if not include_text or not lines:
        return _to_jpeg(canvas)

    if not os.path.exists(font_path):
        raise FileNotFoundError(f"字体文件不存在: {font_path}")

    # 字号从18递减到10，直到最宽行不超过400px
    font_size = 18
    font = ImageFont.truetype(font_path, font_size)
    while font_size > 10 and max(font.getlength(line) for line in lines) > TEXT_MAX_WIDTH:
        font_size -= 1
        font = ImageFont.truetype(font_path, font_size)

    draw = ImageDraw.Draw(canvas)
    padding_left = cols * IMG_SIZE + 30
    padding_top = 40
    line_height = (canvas_height - padding_top * 2) / len(lines)
    for index, line in enumerate(lines):
        draw.text(
            (padding_left, padding_top + index * line_height + font_size),
            _truncate_to_width(line, font, TEXT_MAX_WIDTH),
            fill="#ffffff",
            font=font,
        )

    return _to_jpeg(canvas)


def _to_jpeg(image):
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=90)
    return buf.getvalue()
