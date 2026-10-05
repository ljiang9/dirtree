#!/usr/bin/env python3
"""dirtree：把目录结构画成经典的树形，符号链接不跟随、排序可预期。

标准库 only，无第三方依赖。
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys

__version__ = "0.1.0"

# ── 工具函数 ────────────────────────────────────────────────────────────

_NUM_RE = re.compile(r"(\d+)")


def natural_key(name: str):
    """自然排序键：忽略大小写，数字段按数值比。"""
    return [int(t) if t.isdigit() else t.lower() for t in _NUM_RE.split(name)]


def sort_entries(entries: list[os.DirEntry], dirs_first: bool) -> list[os.DirEntry]:
    def key(e: os.DirEntry):
        is_dir = e.is_dir(follow_symlinks=False)
        dir_rank = 0 if is_dir else 1
        if not dirs_first:
            dir_rank = 0
        return (dir_rank, natural_key(e.name))

    return sorted(entries, key=key)


def human_size(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    for u in units:
        if f < 1024 or u == units[-1]:
            return f"{f:.1f} {u}" if u != "B" else f"{int(f)} B"
        f /= 1024
    return f"{f:.1f} PB"


def matches(name: str, is_dir: bool, include: list[str], exclude: list[str]) -> bool:
    # --include 只过滤文件：目录永远保留以便继续下钻
    if include and not is_dir and not any(fnmatch.fnmatch(name, p) for p in include):
        return False
    if exclude and any(fnmatch.fnmatch(name, p) for p in exclude):
        return False
    return True


# ── 树形渲染 ────────────────────────────────────────────────────────────

class Counts:
    def __init__(self):
        self.dirs = 0
        self.files = 0


def _render(path: str, prefix: str, depth: int, args, include: list[str],
            lines: list[str], counts: Counts):
    try:
        with os.scandir(path) as it:
            entries = [e for e in it
                       if matches(e.name, e.is_dir(follow_symlinks=False), include, args.exclude)]
    except OSError as e:
        lines.append(f"{prefix}└── [无法读取: {e.strerror}]")
        return
    if args.dirs_only:
        entries = [e for e in entries if e.is_dir(follow_symlinks=False)]
    entries = sort_entries(entries, args.dirs_first)
    last = len(entries) - 1
    for i, e in enumerate(entries):
        is_last = (i == last)
        conn = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        is_link = e.is_symlink()
        is_dir = e.is_dir(follow_symlinks=False)

        label = e.name
        if is_link:
            try:
                label += " -> " + os.readlink(e.path)
            except OSError:
                label += " -> [坏链]"
        if args.sizes and not is_dir:
            try:
                label += f"  ({human_size(e.stat(follow_symlinks=False).st_size)})"
            except OSError:
                pass

        lines.append(f"{prefix}{conn}{label}")

        if is_dir and not is_link and (args.depth < 0 or depth + 1 < args.depth):
            counts.dirs += 1
            _render(e.path, prefix + ext, depth + 1, args, include, lines, counts)
        elif is_dir:
            counts.dirs += 1
        else:
            counts.files += 1


# ── JSON 结构输出 ───────────────────────────────────────────────────────

def _node(path: str, depth: int, max_depth: int, include, exclude, dirs_first) -> dict:
    st = os.lstat(path)
    name = os.path.basename(path) or path
    is_link = os.path.islink(path)
    if is_link:
        try:
            target = os.readlink(path)
        except OSError:
            target = "[坏链]"
        return {"name": name, "type": "symlink", "target": target}
    if os.path.isdir(path):
        children = []
        if max_depth < 0 or depth + 1 < max_depth:
            try:
                with os.scandir(path) as it:
                    entries = [e for e in it
                               if matches(e.name, e.is_dir(follow_symlinks=False),
                                          include, exclude)]
            except OSError:
                entries = []
            for e in sort_entries(entries, dirs_first):
                children.append(_node(e.path, depth + 1, max_depth, include, exclude, dirs_first))
        return {"name": name, "type": "directory", "children": children}
    return {"name": name, "type": "file", "size": st.st_size}


def render_json(root: str, **kwargs) -> str:
    return json.dumps(_node(os.path.abspath(root), 0,
                           kwargs.get("max_depth", -1),
                           kwargs.get("include") or [],
                           kwargs.get("exclude") or [],
                           kwargs.get("dirs_first", True)),
                      ensure_ascii=False, indent=2)


# ── CLI ─────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dirtree",
        description="把目录结构画成树：dirtree <目录>。符号链接不跟随，只显示。")
    p.add_argument("path", nargs="?", default=".",
                   help="要列出的目录（默认当前目录）")
    p.add_argument("-d", "--depth", type=int, default=-1,
                   help="最大深度（默认不限制）")
    p.add_argument("--dirs-only", action="store_true", help="只显示目录")
    p.add_argument("--include", action="append", default=[],
                   help='只包含匹配 glob 的名字，可多次使用，如 --include "*.py"')
    p.add_argument("--exclude", action="append", default=[],
                   help='排除匹配 glob 的名字，可多次使用，如 --exclude "__pycache__"')
    p.add_argument("--sizes", action="store_true", help="在文件名后显示大小")
    p.add_argument("--json", action="store_true", help="输出嵌套 JSON 结构")
    p.add_argument("--dirs-first", dest="dirs_first", action="store_true", default=True,
                   help="目录排在文件前面（默认）")
    p.add_argument("--no-dirs-first", dest="dirs_first", action="store_false",
                   help="不分目录/文件，统一自然排序")
    p.add_argument("--version", action="version", version=f"dirtree {__version__}")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"error: 不是目录：{args.path}", file=sys.stderr)
        return 1
    if args.depth == 0:
        args.depth = 1  # --depth 按"显示层数"计，最少 1 层

    include = list(args.include)

    if args.json:
        print(render_json(root, max_depth=args.depth, include=include,
                          exclude=args.exclude, dirs_first=args.dirs_first))
        return 0

    lines = [root]
    counts = Counts()
    _render(root, "", 0, args, include, lines, counts)
    print("\n".join(lines))
    print(f"\n{counts.dirs} 个目录，{counts.files} 个文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
