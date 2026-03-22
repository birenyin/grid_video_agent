from __future__ import annotations

import json
from urllib import error, request

from .config import AgentConfig
from .models import GridNewsItem, VideoPlan, VideoSegment
from .prompts import SYSTEM_POSITIONING, build_user_prompt


def maybe_generate_with_llm(items: list[GridNewsItem], config: AgentConfig) -> VideoPlan | None:
    if config.model_mode not in {"auto", "api"}:
        return None
    if not config.api_key:
        return None

    payload = {
        "model": config.model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_POSITIONING},
            {"role": "user", "content": build_user_prompt(items, config.brand_name, config.audience)},
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }
    req = request.Request(
        f"{config.api_base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None

    try:
        content = result["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return parse_video_plan(parsed)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None


def parse_video_plan(data: dict) -> VideoPlan:
    segments = [
        VideoSegment(
            scene=int(segment.get("scene", index + 1)),
            visual=str(segment.get("visual", "")),
            narration=str(segment.get("narration", "")),
            subtitle=str(segment.get("subtitle", segment.get("narration", ""))),
        )
        for index, segment in enumerate(data.get("segments", []))
        if isinstance(segment, dict)
    ]
    return VideoPlan(
        title=str(data.get("title", "电网视频解读")),
        cover_text=str(data.get("cover_text", "电网速递\n一分钟看懂")),
        intro_hook=str(data.get("intro_hook", "")),
        takeaway=str(data.get("takeaway", "")),
        hashtags=[str(tag) for tag in data.get("hashtags", [])],
        selected_news=list(data.get("selected_news", [])),
        segments=segments,
        generation_mode="llm",
        warnings=[str(item) for item in data.get("warnings", [])],
    )
