from __future__ import annotations

import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path

from app.core.config import Settings


def build_test_settings(runtime_dir: Path) -> Settings:
    return Settings(
        app_name="Grid Video Agent Test",
        app_env="test",
        project_root=runtime_dir,
        runtime_dir=runtime_dir / "runtime",
        database_path=runtime_dir / "runtime" / "test.db",
        automation_scheduler_enabled=False,
        automation_poll_seconds=0.1,
        default_reference_image_path="",
        llm_provider_priority=("mock_llm",),
        image_provider_priority=("mock_image",),
        video_provider_priority=("mock_video",),
        tts_provider_priority=("mock_tts",),
        subtitle_provider_priority=("local_subtitle",),
        publishing_provider_priority=("mock_publisher",),
        enable_real_publish=False,
        llm_api_key="",
        llm_base_url="https://api.openai.com/v1",
        llm_model="gpt-4o-mini",
        volcengine_ak="",
        volcengine_sk="",
        volcengine_api_key="",
        volcengine_image_req_key="seed3l_single_ip",
        volcengine_image_service="cv",
        volcengine_image_region="cn-north-1",
        volcengine_image_poll_seconds=0.01,
        volcengine_image_max_polls=2,
        volcengine_video_api_key="",
        volcengine_video_submit_url="",
        volcengine_video_query_url="",
        volcengine_video_callback_url="",
        volcengine_video_model="doubao-seedance-1-0-pro-250528",
        volcengine_video_req_key="jimeng_ti2v_v30_pro",
        volcengine_video_text_req_key="jimeng_t2v_v30_1080p",
        volcengine_video_image_req_key="jimeng_i2v_first_v30_1080",
        volcengine_video_service="cv",
        volcengine_video_region="cn-north-1",
        volcengine_video_use_operator=False,
        volcengine_video_submit_method="POST",
        volcengine_video_query_method="GET",
        volcengine_video_poll_seconds=0.01,
        volcengine_video_max_polls=2,
        volcengine_video_aspect_ratio="9:16",
        volcengine_tts_appid="",
        volcengine_tts_token="",
        volcengine_tts_access_key="",
        volcengine_tts_secret_key="",
        volcengine_tts_resource_id="volc.service_type.10029",
        volcengine_tts_voice="BV700_V2_streaming",
        volcengine_tts_cluster="",
        volcengine_tts_online_url="https://openspeech.bytedance.com/api/v1/tts",
        volcengine_tts_user_id="grid-video-agent-test",
        volcengine_tts_sample_rate=24000,
        volcengine_tts_poll_seconds=0.01,
        volcengine_tts_max_polls=2,
        volcengine_tts_submit_url="https://openspeech.bytedance.com/api/v3/tts/submit",
        volcengine_tts_query_url="https://openspeech.bytedance.com/api/v3/tts/query",
        douyin_client_key="",
        douyin_client_secret="",
        default_publish_mode="draft",
    )


@contextmanager
def workspace_tempdir():
    root = Path("F:/AICODING/电网视频生成助手/.tmp_test")
    root.mkdir(parents=True, exist_ok=True)
    temp_dir = root / uuid.uuid4().hex
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
