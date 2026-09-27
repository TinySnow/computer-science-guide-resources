#!/usr/bin/env python3
"""Render the two approved Chapter 18 SVG animations into GIFs."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


HERE = Path(__file__).resolve().parent
INVERTER_SOURCE = HERE / "单个非门反馈为何振荡.svg"
INVERTER_OUTPUT = HERE / "单个非门反馈为何振荡.gif"
SR_SOURCE = HERE / "SR锁存器怎样写入并保持.svg"
SR_OUTPUT = HERE / "SR锁存器怎样写入并保持.gif"
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

HOT = "#F85C0C"
HOT_TEXT = "#C84500"
MUTED = "#A8B7CA"
MUTED_TEXT = "#65748D"

INVERTER_STATES = [
    dict(step="第 1 步", input="0", output="1", title="Q 刚变成 1", line1="输入端暂时还是 0", line2="非门于是输出 1", next1="这个 1 会沿反馈线", next2="重新回到输入端", hot="forward"),
    dict(step="第 2 步", input="1", output="1", title="1 回到输入端", line1="反馈抵达：输入变成 1", line2="输出暂时仍然是 1", next1="非门发现两端相同", next2="开始要求 Q 变成 0", hot="feedback"),
    dict(step="第 3 步", input="1", output="0", title="Q 又变成 0", line1="输入端暂时还是 1", line2="非门于是输出 0", next1="这个 0 会沿反馈线", next2="重新回到输入端", hot="forward"),
    dict(step="第 4 步", input="0", output="0", title="0 回到输入端", line1="反馈抵达：输入变成 0", line2="输出暂时仍然是 0", next1="非门再次要求翻转", next2="循环重新回到第 1 步", hot="feedback"),
]

SR_STATES = [
    dict(step="1", s="0", r="0", q="0", qb="1", title="初始：保持 0", line1="S = 0，R = 0", line2="Q = 0，Q̅ = 1", focus1="Q̅ = 1 的反馈路径", focus2="外部没有一直按住按钮", active="qb"),
    dict(step="2", s="1", r="0", q="1", qb="0", title="S 短暂变成 1：写 1", line1="S = 1，R = 0", line2="Q 被写成 1", focus1="写入请求从 S 进入", focus2="状态随即翻到 Q = 1", active="s"),
    dict(step="3", s="0", r="0", q="1", qb="0", title="S 回到 0：仍保持 1", line1="S 回到 0，R 仍为 0", line2="Q 继续等于 1", focus1="Q = 1 的反馈路径", focus2="接手维持刚写入的状态", active="q"),
    dict(step="4", s="0", r="1", q="0", qb="1", title="R 短暂变成 1：写 0", line1="S = 0，R = 1", line2="Q 被写成 0", focus1="写入请求从 R 进入", focus2="状态随即翻到 Q = 0", active="r"),
    dict(step="5", s="0", r="0", q="0", qb="1", title="R 回到 0：仍保持 0", line1="R 回到 0，S 仍为 0", line2="Q 继续等于 0", focus1="Q̅ = 1 的反馈路径", focus2="接手维持刚写入的状态", active="qb"),
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


def set_wire(root: ET.Element, element_id: str, active: bool) -> None:
    element = find(root, element_id)
    element.set("stroke", HOT if active else MUTED)
    element.set("stroke-width", "5" if active else "3")
    element.set("marker-end", "url(#arrow-hot)" if active else "url(#arrow-muted)")


def set_chip(root: ET.Element, prefix: str, value: str, active: bool) -> None:
    chip = find(root, f"{prefix}-chip")
    chip.set("fill", "#FEF2E5" if active else "#F5F8FE")
    chip.set("stroke", HOT if active else "#C4D4E9")
    chip.set("stroke-width", "3" if active else "2")
    label = find(root, f"{prefix}-value")
    label.text = value
    label.set("fill", HOT_TEXT if active else MUTED_TEXT)


def write_png(tree: ET.ElementTree, destination: Path, renderer: str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as handle:
        temp_svg = Path(handle.name)
    try:
        tree.write(temp_svg, encoding="utf-8", xml_declaration=True)
        subprocess.run([renderer, "--width", "1672", "--height", "941", "--keep-aspect-ratio", str(temp_svg), "--output", str(destination)], check=True)
    finally:
        temp_svg.unlink(missing_ok=True)


def render_inverter(state: dict[str, str], destination: Path, renderer: str) -> None:
    tree = ET.parse(INVERTER_SOURCE)
    root = tree.getroot()
    find(root, "desc").text = f"非门输入为 {state['input']}，输出 Q 为 {state['output']}。{state['next1']}，{state['next2']}。"
    set_chip(root, "input", state["input"], state["hot"] == "feedback")
    set_chip(root, "output", state["output"], state["hot"] == "forward")
    set_wire(root, "forward-wire", state["hot"] == "forward")
    set_wire(root, "output-wire", state["hot"] == "forward")
    set_wire(root, "feedback-wire", state["hot"] == "feedback")
    for element_id, key in [("phase-number", "step"), ("state-title", "title"), ("state-line-1", "line1"), ("state-line-2", "line2"), ("next-line-1", "next1"), ("next-line-2", "next2")]:
        find(root, element_id).text = state[key]
    write_png(tree, destination, renderer)


def render_sr(state: dict[str, str], destination: Path, renderer: str) -> None:
    tree = ET.parse(SR_SOURCE)
    root = tree.getroot()
    find(root, "desc").text = f"S 等于 {state['s']}，R 等于 {state['r']}，锁存器输出 Q 等于 {state['q']}，Q 反等于 {state['qb']}。"
    active = state["active"]
    # 写入帧高亮整条因果链；保持帧只强调接手维持状态的反馈支路。
    s_path = active == "s"
    r_path = active == "r"
    q_hold = active == "q"
    qb_hold = active == "qb"
    set_chip(root, "s", state["s"], s_path)
    set_chip(root, "r", state["r"], r_path)
    set_chip(root, "q", state["q"], q_hold or s_path or r_path)
    set_chip(root, "qbar", state["qb"], qb_hold or s_path or r_path)
    set_wire(root, "s-wire", s_path)
    set_wire(root, "r-wire", r_path)
    set_wire(root, "q-wire", q_hold or s_path or r_path)
    set_wire(root, "qbar-wire", qb_hold or s_path or r_path)
    set_wire(root, "feedback-q", q_hold or r_path)
    set_wire(root, "feedback-qbar", qb_hold or s_path)
    find(root, "junction-q").set("fill", HOT if q_hold or r_path else MUTED)
    find(root, "junction-qbar").set("fill", HOT if qb_hold or s_path else MUTED)
    for element_id, key in [("phase-number", "step"), ("state-title", "title"), ("state-line-1", "line1"), ("state-line-2", "line2"), ("focus-line-1", "focus1"), ("focus-line-2", "focus2")]:
        find(root, element_id).text = state[key]
    active_index = SR_STATES.index(state)
    for index in range(len(SR_STATES)):
        selected = index == active_index
        circle = find(root, f"timeline-circle-{index}")
        circle.set("fill", "#1568E0" if selected else "#FFFFFF")
        circle.set("stroke", "#1568E0" if selected else "#C4D4E9")
        circle.set("stroke-width", "2")
        find(root, f"timeline-number-{index}").set("fill", "#FFFFFF" if selected else MUTED_TEXT)
        label = find(root, f"timeline-label-{index}")
        label.set("fill", "#155ECF" if selected else MUTED_TEXT)
        label.set("font-weight", "700" if selected else "400")
    write_png(tree, destination, renderer)


def encode_gif(frames: list[Path], output: Path, encoder: str) -> None:
    subprocess.run([encoder, "--fps", "1", "--quality", "92", "--width", "1672", "--height", "941", "--repeat", "0", "--no-sort", "--output", str(output), *map(str, frames)], check=True)


def main() -> None:
    renderer = require("rsvg-convert")
    encoder = require("gifski")
    with tempfile.TemporaryDirectory(prefix="chapter18-") as temp_name:
        temp = Path(temp_name)
        inverter_frames = []
        for index, state in enumerate(INVERTER_STATES):
            frame = temp / f"inverter-{index:02d}.png"
            render_inverter(state, frame, renderer)
            inverter_frames.append(frame)
        encode_gif(inverter_frames, INVERTER_OUTPUT, encoder)

        sr_frames = []
        for index, state in enumerate(SR_STATES):
            frame = temp / f"sr-{index:02d}.png"
            render_sr(state, frame, renderer)
            sr_frames.append(frame)
        encode_gif(sr_frames, SR_OUTPUT, encoder)

    print(INVERTER_OUTPUT)
    print(SR_OUTPUT)


if __name__ == "__main__":
    main()
