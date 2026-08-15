# nonebot-plugin-musicgrid

网易云歌单音乐墙生成器：粘贴网易云公开歌单链接，生成 Topsters 风格的专辑墙拼图。

## 命令行使用

```bash
python -m nonebot_plugin_musicgrid.cli <歌单链接或ID> [-c 5] [-r 5] [--no-text] [--album] [-o out.jpg]
```

- `-c/--cols`：列数（1~10，默认 5）
- `-r/--rows`：行数（1~10，默认 5）
- `--no-text`：不生成右侧文字列表
- `--album`：专辑名模式（网易云官方 API，显示真实专辑名，速度较慢）
- `--dedup`：去重（跳过重复封面/专辑，向后扫描凑满格子）
- `-o`：输出文件路径（默认 music_grid.jpg）

## QQ 插件使用

群内发送 `音乐墙 <歌单链接>`，可选参数：`行x列`（如 3x3）、`notext`（无文字列表）、`album`（专辑名模式）、`dedup`（去重凑满）。

## 说明

- 歌单需为公开歌单
- 数据来自 Meting API（歌曲名模式）
- 内置霞鹜文楷字体（随包分发），无需安装字体即可跨平台使用
- 仅供学习交流使用
