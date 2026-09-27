#!/usr/bin/env python3
"""Render the ALU SVG prototype into a four-state looping GIF."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "第十五章-ALU控制码切换.svg"
OUTPUT = HERE / "第十五章-ALU控制码切换.gif"
SVG_NS = "http://www.w3.org/2000/svg"

ET.register_namespace("", SVG_NS)

STATES = {
    "00": {"row": 0, "route": "R0", "result": "1000"},
    "01": {"row": 1, "route": "R1", "result": "0010"},
    "10": {"row": 2, "route": "R2", "result": "0001"},
    "11": {"row": 3, "route": "R3", "result": "0111"},
}

BASE_CARD_STROKES = {
    "00": "#5295DF",
    "01": "#F85C0C",
    "10": "#259A5E",
    "11": "#886EC6",
}


def require_command(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise SystemExit(f"缺少命令：{name}")
    return path


def find(root: ET.Element, element_id: str) -> ET.Element:
    element = root.find(f".//*[@id='{element_id}']")
    if element is None:
        raise RuntimeError(f"SVG 中找不到元素：{element_id}")
    return element


def render_state(code: str, destination: Path, renderer: str) -> None:
    tree = ET.parse(SOURCE)
    root = tree.getroot()
    state = STATES[code]

    description = find(root, "desc")
    description.text = (
        f"输入 A 和 B 同时进入四条运算路径。控制码 OP 等于 {code} 时，"
        f"多路选择器只放行 {state['route']}，输出 {state['result']}。"
    )

    for candidate in STATES:
        active = candidate == code

        card = find(root, f"card-{candidate}")
        card.set("stroke", "#F85C0C" if active else BASE_CARD_STROKES[candidate])
        card.set("stroke-width", "4" if active else "2")

        path = find(root, f"path-{candidate}")
        path.set("stroke", "#F85C0C" if active else "#A8B7CA")
        path.set("stroke-width", "5" if active else "2.6")
        path.set("marker-end", "url(#arrow-orange)" if active else "url(#arrow-muted)")

        label = find(root, f"result-label-{candidate}")
        label.set("fill", "#C84500" if active else "#65748D")
        label.set("font-size", "21" if active else "19")
        label.set("font-weight", "700" if active else "400")

        pill = find(root, f"pill-{candidate}")
        pill.set("fill", "#FEF2E5" if active else "#F5F8FE")
        pill.set("stroke", "#F85C0C" if active else "#C4D4E9")
        pill.set("stroke-width", "2.5" if active else "1.5")

        pill_label = find(root, f"pill-label-{candidate}")
        pill_label.set("fill", "#C84500" if active else "#65748D")

    badge = find(root, "selected-badge")
    badge.set("transform", f"translate(0 {state['row'] * 112})")

    find(root, "mux-selection").text = f"放行 {state['route']}"
    find(root, "result-value").text = state["result"]
    find(root, "op-value").text = f"OP = {code}"

    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as svg_file:
        temp_svg = Path(svg_file.name)
    try:
        tree.write(temp_svg, encoding="utf-8", xml_declaration=True)
        subprocess.run(
            [
                renderer,
                "--width",
                "1672",
                "--height",
                "941",
                "--keep-aspect-ratio",
                str(temp_svg),
                "--output",
                str(destination),
            ],
            check=True,
        )
    finally:
        temp_svg.unlink(missing_ok=True)


def main() -> None:
    renderer = require_command("rsvg-convert")
    encoder = require_command("gifski")

    with tempfile.TemporaryDirectory(prefix="alu-gif-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        frames: list[Path] = []

        for index, code in enumerate(STATES):
            frame = temp_dir / f"frame-{index:02d}-{code}.png"
            render_state(code, frame, renderer)
            frames.append(frame)

        subprocess.run(
            [
                encoder,
                "--fps",
                "1",
                "--quality",
                "92",
                "--width",
                "1672",
                "--height",
                "941",
                "--repeat",
                "0",
                "--no-sort",
                "--output",
                str(OUTPUT),
                *map(str, frames),
            ],
            check=True,
        )

    print(OUTPUT)


if __name__ == "__main__":
    main()
