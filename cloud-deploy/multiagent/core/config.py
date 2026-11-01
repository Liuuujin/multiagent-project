"""
配置加载
========
从项目根目录的 .env 读取配置到环境变量(轻量实现,不依赖 python-dotenv)。
已存在的系统环境变量优先,不会被 .env 覆盖。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_LOADED = False


def load_env(path: Optional[str] = None) -> None:
    """读取 .env 到 os.environ(只执行一次)。"""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True

    env_path = Path(path) if path else Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except ValueError:
        return default


def get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "") or default)
    except ValueError:
        return default
