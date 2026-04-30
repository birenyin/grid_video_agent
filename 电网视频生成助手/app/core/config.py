from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _split_csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    items = [item.strip() for item in value.split(",") if item.strip()]
    return tuple(items) if items else default


def _as_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    return int(value)


def _as_float(value: str | None, default: float) -> float:
    if value is None or not value.strip():
        return default
    return float(value)


@dataclass
class Settings:
    app_name: str
    app_env: str
    project_root: Path
    runtime_dir: Path
    database_path: Path
    automation_scheduler_enabled: bool
    automation_poll_seconds: float
    default_reference_image_path: str
    llm_provider_priority: tuple[str, ...]
    image_provider_priority: tuple[str, ...]
    video_provider_priority: tuple[str, ...]
    tts_provider_priority: tuple[str, ...]
    subtitle_provider_priority: tuple[str, ...]
    publishing_provider_priority: tuple[str, ...]
    enable_real_publish: bool
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    volcengine_ak: str
    volcengine_sk: str
    volcengine_api_key: str
    volcengine_image_req_key: str
    volcengine_image_service: str
    volcengine_image_region: str
    volcengine_image_poll_seconds: float
    volcengine_image_max_polls: int
    volcengine_video_api_key: str
    volcengine_video_submit_url: str
    volcengine_video_query_url: str
    volcengine_video_callback_url: str
    volcengine_video_model: str
    volcengine_video_req_key: str
    volcengine_video_text_req_key: str
    volcengine_video_image_req_key: str
    volcengine_video_service: str
    volcengine_video_region: str
    volcengine_video_use_operator: bool
    volcengine_video_submit_method: str
    volcengine_video_query_method: str
    volcengine_video_poll_seconds: float
    volcengine_video_max_polls: int
    volcengine_video_aspect_ratio: str
    volcengine_tts_appid: str
    volcengine_tts_token: str
    volcengine_tts_access_key: str
    volcengine_tts_secret_key: str
    volcengine_tts_resource_id: str
    volcengine_tts_voice: str
    volcengine_tts_cluster: str
    volcengine_tts_online_url: str
    volcengine_tts_user_id: str
    volcengine_tts_sample_rate: int
    volcengine_tts_poll_seconds: float
    volcengine_tts_max_polls: int
    volcengine_tts_submit_url: str
    volcengine_tts_query_url: str
    douyin_client_key: str
    douyin_client_secret: str
    default_publish_mode: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    runtime_dir = Path(os.getenv("APP_RUNTIME_DIR", project_root / "runtime"))
    database_path = Path(os.getenv("APP_DATABASE_PATH", runtime_dir / "grid_video_agent.db"))

    return Settings(
        app_name=os.getenv("APP_NAME", "Grid Video Agent"),
        app_env=os.getenv("APP_ENV", "dev"),
        project_root=project_root,
        runtime_dir=runtime_dir,
        database_path=database_path,
        automation_scheduler_enabled=_as_bool(os.getenv("AUTOMATION_SCHEDULER_ENABLED"), True),
        automation_poll_seconds=_as_float(os.getenv("AUTOMATION_POLL_SECONDS"), 30.0),
        default_reference_image_path=os.getenv(
            "DEFAULT_REFERENCE_IMAGE_PATH",
            "assets/reference/person.png",
        ),
        llm_provider_priority=_split_csv(
            os.getenv("PROVIDER_PRIORITY_LLM"),
            ("openai_llm", "mock_llm"),
        ),
        image_provider_priority=_split_csv(
            os.getenv("PROVIDER_PRIORITY_IMAGE"),
            ("volcengine_image", "mock_image"),
        ),
        video_provider_priority=_split_csv(
            os.getenv("PROVIDER_PRIORITY_VIDEO"),
            ("volcengine_video", "mock_video"),
        ),
        tts_provider_priority=_split_csv(
            os.getenv("PROVIDER_PRIORITY_TTS"),
            ("volcengine_tts", "mock_tts"),
        ),
        subtitle_provider_priority=_split_csv(
            os.getenv("PROVIDER_PRIORITY_SUBTITLE"),
            ("local_subtitle",),
        ),
        publishing_provider_priority=_split_csv(
            os.getenv("PROVIDER_PRIORITY_PUBLISH"),
            ("douyin_publisher",),
        ),
        enable_real_publish=_as_bool(os.getenv("ENABLE_REAL_PUBLISH"), False),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        volcengine_ak=os.getenv("VOLCENGINE_AK", ""),
        volcengine_sk=os.getenv("VOLCENGINE_SK", ""),
        volcengine_api_key=os.getenv("VOLCENGINE_API_KEY", ""),
        volcengine_image_req_key=os.getenv("VOLCENGINE_IMAGE_REQ_KEY", "seed3l_single_ip"),
        volcengine_image_service=os.getenv("VOLCENGINE_IMAGE_SERVICE", "cv"),
        volcengine_image_region=os.getenv("VOLCENGINE_IMAGE_REGION", "cn-north-1"),
        volcengine_image_poll_seconds=_as_float(os.getenv("VOLCENGINE_IMAGE_POLL_SECONDS"), 4.0),
        volcengine_image_max_polls=_as_int(os.getenv("VOLCENGINE_IMAGE_MAX_POLLS"), 30),
        volcengine_video_api_key=os.getenv("VOLCENGINE_VIDEO_API_KEY", os.getenv("VOLCENGINE_API_KEY", "")),
        volcengine_video_submit_url=os.getenv(
            "VOLCENGINE_VIDEO_SUBMIT_URL",
            "https://operator.las.cn-beijing.volces.com/api/v1/contents/generations/tasks",
        ),
        volcengine_video_query_url=os.getenv(
            "VOLCENGINE_VIDEO_QUERY_URL",
            "https://operator.las.cn-beijing.volces.com/api/v1/contents/generations/tasks/{task_id}",
        ),
        volcengine_video_callback_url=os.getenv("VOLCENGINE_VIDEO_CALLBACK_URL", ""),
        volcengine_video_model=os.getenv("VOLCENGINE_VIDEO_MODEL", "doubao-seedance-1-0-pro-250528"),
        volcengine_video_req_key=os.getenv("VOLCENGINE_VIDEO_REQ_KEY", "jimeng_ti2v_v30_pro"),
        volcengine_video_text_req_key=os.getenv("VOLCENGINE_VIDEO_TEXT_REQ_KEY", "jimeng_t2v_v30_1080p"),
        volcengine_video_image_req_key=os.getenv("VOLCENGINE_VIDEO_IMAGE_REQ_KEY", "jimeng_i2v_first_v30_1080"),
        volcengine_video_service=os.getenv("VOLCENGINE_VIDEO_SERVICE", "cv"),
        volcengine_video_region=os.getenv("VOLCENGINE_VIDEO_REGION", "cn-north-1"),
        volcengine_video_use_operator=_as_bool(os.getenv("VOLCENGINE_VIDEO_USE_OPERATOR"), False),
        volcengine_video_submit_method=os.getenv("VOLCENGINE_VIDEO_SUBMIT_METHOD", "POST").upper(),
        volcengine_video_query_method=os.getenv("VOLCENGINE_VIDEO_QUERY_METHOD", "GET").upper(),
        volcengine_video_poll_seconds=_as_float(os.getenv("VOLCENGINE_VIDEO_POLL_SECONDS"), 5.0),
        volcengine_video_max_polls=_as_int(os.getenv("VOLCENGINE_VIDEO_MAX_POLLS"), 24),
        volcengine_video_aspect_ratio=os.getenv("VOLCENGINE_VIDEO_ASPECT_RATIO", "9:16"),
        volcengine_tts_appid=os.getenv("VOLCENGINE_TTS_APPID", ""),
        volcengine_tts_token=os.getenv("VOLCENGINE_TTS_TOKEN", ""),
        volcengine_tts_access_key=os.getenv("VOLCENGINE_TTS_ACCESS_KEY", os.getenv("VOLCENGINE_TTS_TOKEN", "")),
        volcengine_tts_secret_key=os.getenv("VOLCENGINE_TTS_SECRET_KEY", ""),
        volcengine_tts_resource_id=os.getenv("VOLCENGINE_TTS_RESOURCE_ID", "volc.service_type.10029"),
        volcengine_tts_voice=os.getenv("VOLCENGINE_TTS_VOICE", "BV700_V2_streaming"),
        volcengine_tts_cluster=os.getenv("VOLCENGINE_TTS_CLUSTER", ""),
        volcengine_tts_online_url=os.getenv(
            "VOLCENGINE_TTS_ONLINE_URL",
            "https://openspeech.bytedance.com/api/v1/tts",
        ),
        volcengine_tts_user_id=os.getenv("VOLCENGINE_TTS_USER_ID", "grid-video-agent"),
        volcengine_tts_sample_rate=_as_int(os.getenv("VOLCENGINE_TTS_SAMPLE_RATE"), 24000),
        volcengine_tts_poll_seconds=_as_float(os.getenv("VOLCENGINE_TTS_POLL_SECONDS"), 2.0),
        volcengine_tts_max_polls=_as_int(os.getenv("VOLCENGINE_TTS_MAX_POLLS"), 15),
        volcengine_tts_submit_url=os.getenv(
            "VOLCENGINE_TTS_SUBMIT_URL",
            "https://openspeech.bytedance.com/api/v3/tts/submit",
        ),
        volcengine_tts_query_url=os.getenv(
            "VOLCENGINE_TTS_QUERY_URL",
            "https://openspeech.bytedance.com/api/v3/tts/query",
        ),
        douyin_client_key=os.getenv("DOUYIN_CLIENT_KEY", ""),
        douyin_client_secret=os.getenv("DOUYIN_CLIENT_SECRET", ""),
        default_publish_mode=os.getenv("DEFAULT_PUBLISH_MODE", "draft"),
    )
