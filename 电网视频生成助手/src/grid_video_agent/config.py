from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    brand_name: str = "电网调度速递"
    audience: str = "电网调度、运维、电力市场从业者"
    duration_seconds: int = 60
    model_mode: str = "rule"
    model_name: str = "gpt-4.1-mini"
    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    source_set: str = "mixed"
    per_source_limit: int = 4
    total_fetch_limit: int = 10
    fetch_timeout_seconds: int = 18
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36 GridVideoAgent/0.1"
    )


def load_agent_config() -> AgentConfig:
    return AgentConfig(
        brand_name=os.getenv("GRID_VIDEO_BRAND_NAME", "电网调度速递"),
        audience=os.getenv("GRID_VIDEO_AUDIENCE", "电网调度、运维、电力市场从业者"),
        duration_seconds=int(os.getenv("GRID_VIDEO_DURATION_SECONDS", "60")),
        model_mode=os.getenv("GRID_VIDEO_MODEL_MODE", "rule"),
        model_name=os.getenv("GRID_VIDEO_MODEL_NAME", "gpt-4.1-mini"),
        api_base=os.getenv("GRID_VIDEO_API_BASE", "https://api.openai.com/v1").rstrip("/"),
        api_key=os.getenv("GRID_VIDEO_API_KEY", ""),
        source_set=os.getenv("GRID_VIDEO_SOURCE_SET", "mixed"),
        per_source_limit=int(os.getenv("GRID_VIDEO_PER_SOURCE_LIMIT", "4")),
        total_fetch_limit=int(os.getenv("GRID_VIDEO_TOTAL_FETCH_LIMIT", "10")),
        fetch_timeout_seconds=int(os.getenv("GRID_VIDEO_FETCH_TIMEOUT", "18")),
        user_agent=os.getenv(
            "GRID_VIDEO_USER_AGENT",
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/132.0.0.0 Safari/537.36 GridVideoAgent/0.1"
            ),
        ),
    )
