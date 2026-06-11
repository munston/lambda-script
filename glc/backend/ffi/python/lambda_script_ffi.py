from __future__ import annotations

import ctypes
from pathlib import Path


def load_runtime(path: str | Path) -> ctypes.CDLL:
    runtime = ctypes.CDLL(str(path))
    runtime.ls_add_int.argtypes = [ctypes.c_int, ctypes.c_int]
    runtime.ls_add_int.restype = ctypes.c_int
    runtime.ls_runtime_name.argtypes = []
    runtime.ls_runtime_name.restype = ctypes.c_char_p
    return runtime


def add_int(runtime: ctypes.CDLL, left: int, right: int) -> int:
    return int(runtime.ls_add_int(left, right))


def runtime_name(runtime: ctypes.CDLL) -> str:
    raw = runtime.ls_runtime_name()
    return raw.decode("utf-8")
