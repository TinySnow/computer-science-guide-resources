#!/usr/bin/env python3
"""Render the fixed CLK/D/Q timing diagram into a guided looping GIF."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "读边沿采样时序图.svg"
OUTPUT = HERE / "读边沿采样时序图.gif"
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

STATES = [
    dict(x=370, d_y=460, q_y=620, window=370, title="第 1 个上升沿：采到 D = 1", note="D 在边沿前后稳定，Q 原本也是 1", kind="edge"),
    dict(x=620, d_y=490, q_y=620, window=None, title="两次边沿之间：D 变成 0", note="此刻没有采样，Q 继续保持 1", kind="data"),
    dict(x=800, d_y=520, q_y=620, window=800, title="第 2 个上升沿：采到 D = 0", note="先读取稳定的 D；Q 此刻还没有变化", kind="edge"),
    dict(x=870, d_y=520, q_y=650, window=None, title="边沿过后：Q 稍晚更新为 0", note="这段短暂间隔就是时钟到 Q 的传播延迟", kind="output"),
    dict(x=1060, d_y=490, q_y=680, window=None, title="两次边沿之间：D 变回 1", note="仍未到采样时刻，Q 继续保持 0", kind="data"),
    dict(x=1230, d_y=460, q_y=680, window=1230, title="第 3 个上升沿：采到 D = 1", note="D 已避开建立、保持窗口并稳定为 1", kind="edge"),
    dict(x=1300, d_y=460, q_y=650, window=None, title="边沿过后：Q 稍晚更新为 1", note="一次完整的“采样—延迟—保持”完成", kind="output"),
]


def require(name: str) -> str:
    command = shutil.which(name)
    if command is None:
        raise SystemExit(f"缺少命令：{name}")
    return command


def find(root: ET.Element, element_id: str) -> ET.Element:
    element = root.find(f".//*[@id='{element_id}']")
    if element is None:
        raise RuntimeError(f"SVG 中找不到元素：{element_id}")
    return element


def render_state(index: int, destination: Path, renderer: str) -> None:
    state = STATES[index]
    tree = ET.parse(SOURCE)
    root = tree.getroot()
    x = str(state["x"])

    find(root, "desc").text = state["title"] + "。" + state["note"] + "。"
    find(root, "step-number").text = str(index + 1)
    find(root, "step-title").text = state["title"]
    find(root, "step-note").text = state["note"]

    cursor = find(root, "cursor-line")
    cursor.set("x1", x)
    cursor.set("x2", x)
    find(root, "cursor-head").set("d", f"M{state['x'] - 12} 218H{state['x'] + 12}L{x} 236Z")

    d_focus = find(root, "d-focus")
    d_focus.set("cx", x)
    d_focus.set("cy", str(state["d_y"]))
    q_focus = find(root, "q-focus")
    q_focus.set("cx", x)
    q_focus.set("cy", str(state["q_y"]))

    if state["kind"] == "data":
        d_focus.set("r", "17")
        q_focus.set("r", "10")
        q_focus.set("opacity", "0.55")
    elif state["kind"] == "output":
        d_focus.set("r", "10")
        d_focus.set("opacity", "0.55")
        q_focus.set("r", "17")

    window = find(root, "active-window")
    if state["window"] is None:
        window.set("opacity", "0")
    else:
        window.set("transform", f"translate({state['window']} 0)")

    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as handle:
        temp_svg = Path(handle.name)
    try:
        tree.write(temp_svg, encoding="utf-8", xml_declaration=True)
        subprocess.run([renderer, "--width", "1672", "--height", "941", "--keep-aspect-ratio", str(temp_svg), "--output", str(destination)], check=True)
    finally:
        temp_svg.unlink(missing_ok=True)


def main() -> None:
    renderer = require("rsvg-convert")
    encoder = require("gifski")
    with tempfile.TemporaryDirectory(prefix="timing-gif-") as temp_name:
        temp = Path(temp_name)
        frames = []
        for index in range(len(STATES)):
            frame = temp / f"frame-{index:02d}.png"
            render_state(index, frame, renderer)
            frames.append(frame)
        subprocess.run([encoder, "--fps", "1", "--quality", "92", "--width", "1672", "--height", "941", "--repeat", "0", "--no-sort", "--output", str(OUTPUT), *map(str, frames)], check=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
