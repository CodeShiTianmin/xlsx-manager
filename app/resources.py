"""打包(PyInstaller)与源码运行两种场景下的资源/数据路径解析。

- 只读资源（如输出模板）：打包后位于 PyInstaller 解包目录 sys._MEIPASS，
  源码运行时位于包目录内。
- 可写数据（如 SQLite 数据库）：打包后写到 exe 同目录的 data/ 下（解包目录是临时只读的，
  不能用来持久化）；源码运行时仍写到包目录内的 data/。
"""

from __future__ import annotations

import os
import sys

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def resource_path(*parts: str) -> str:
    """只读资源路径：打包后取 _MEIPASS，否则取包目录。"""
    base = getattr(sys, "_MEIPASS", _PKG_DIR)
    return os.path.join(base, *parts)


def writable_data_dir() -> str:
    """可写数据目录：打包后用 exe 同目录的 data/，源码运行用包内 data/。"""
    if is_frozen():
        base = os.path.dirname(sys.executable)
    else:
        base = _PKG_DIR
    path = os.path.join(base, "data")
    os.makedirs(path, exist_ok=True)
    return path
