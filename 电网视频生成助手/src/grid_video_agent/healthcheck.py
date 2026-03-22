from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import sys


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def collect_health() -> dict:
    packages = {
        "PIL": has_module("PIL"),
        "fastapi": has_module("fastapi"),
        "httpx": has_module("httpx"),
        "imageio": has_module("imageio"),
        "numpy": has_module("numpy"),
        "imageio_ffmpeg": has_module("imageio_ffmpeg"),
        "pyttsx3": has_module("pyttsx3"),
        "uvicorn": has_module("uvicorn"),
        "volcengine": has_module("volcengine"),
    }
    return {
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "conda_default_env": os.getenv("CONDA_DEFAULT_ENV", ""),
        "cwd": os.getcwd(),
        "packages": packages,
        "ffmpeg_on_path": bool(shutil.which("ffmpeg")),
    }


def main() -> None:
    print(json.dumps(collect_health(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
