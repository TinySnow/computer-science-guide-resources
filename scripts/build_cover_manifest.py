#!/usr/bin/env python3
"""Build a reproducible cover manifest from the guide source and its chapter plan."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


SECTION_BY_CHAPTER = (
    (36, 47, "程序与编程基础"),
    (48, 100, "操作系统"),
    (101, 155, "计算机网络"),
    (156, 219, "数据结构与算法"),
    (220, 281, "编译原理"),
    (282, 297, "软件构造"),
)
CHAPTER_RE = re.compile(r"^- \*\*第\s*(\d+)\s*章：(.+?)\*\*", re.MULTILINE)
COVER_RE = re.compile(r"computer-science-guide/cover/([^?#)]+?\.png)")
HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
CHAPTER_PREFIX_RE = re.compile(r"^第[零〇一二三四五六七八九十百千万\d]+章：")


def heading(path: Path) -> str | None:
    match = HEADING_RE.search(path.read_text(encoding="utf-8"))
    if not match:
        return None
    return CHAPTER_PREFIX_RE.sub("", match.group(1).strip())


def cover_filename(path: Path, fallback: str) -> str:
    match = COVER_RE.search(path.read_text(encoding="utf-8"))
    return Path(match.group(1)).stem if match else fallback


def section_for_chapter(number: int) -> str:
    for start, end, section in SECTION_BY_CHAPTER:
        if start <= number <= end:
            return section
    raise ValueError(f"第 {number} 章不属于规划范围。")


def main() -> None:
    parser = argparse.ArgumentParser(description="从指南文章和规划生成封面清单")
    parser.add_argument("--source", type=Path, required=True, help="TinySnowBlog 中的指南源目录")
    parser.add_argument("--planning", type=Path, required=True, help="后续章节规划 Markdown")
    parser.add_argument("--output", type=Path, required=True, help="输出 TSV 清单")
    args = parser.parse_args()

    rows: list[tuple[str, str, str]] = []
    outputs: set[tuple[str, str]] = set()
    topics: set[tuple[str, str]] = set()

    def add(folder: str, title: str, filename: str) -> None:
        key = (folder, filename)
        topic_key = (folder, re.sub(r"\s+", "", title))
        if key in outputs or topic_key in topics:
            return
        outputs.add(key)
        topics.add(topic_key)
        rows.append((folder, title, filename))

    for path in sorted(args.source.glob("*.md")):
        if path.name == "计算机科学极简入门指南总览.md":
            add("", "总览", cover_filename(path, "总览"))

    for directory in sorted(path for path in args.source.iterdir() if path.is_dir()):
        for path in sorted(directory.glob("*.md")):
            title = heading(path)
            if title:
                add(directory.name, title, cover_filename(path, title))

    plan_text = args.planning.read_text(encoding="utf-8")
    for chapter, title in CHAPTER_RE.findall(plan_text):
        add(section_for_chapter(int(chapter)), title, title)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "# 目录\t展示标题\t文件名；由 build_cover_manifest.py 自动生成。\n"
        + "\n".join("\t".join(row) for row in rows)
        + "\n",
        encoding="utf-8",
    )
    by_folder: dict[str, int] = {}
    for folder, _, _ in rows:
        by_folder[folder or "（根目录）"] = by_folder.get(folder or "（根目录）", 0) + 1
    print(f"已写入 {len(rows)} 条封面清单：{args.output}")
    for folder, count in by_folder.items():
        print(f"  {folder}: {count}")


if __name__ == "__main__":
    main()
