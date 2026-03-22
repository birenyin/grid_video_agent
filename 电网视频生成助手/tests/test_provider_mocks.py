from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image

from app.core.config import Settings
from app.models.content import ContentInput, ContentMode, ShotType, StoryboardShot, VoiceSynthesisOptions
from app.providers.base import ProviderNotConfiguredError
from app.providers.mock import (
    LocalSubtitleProvider,
    MockImageGenerationProvider,
    MockLLMProvider,
    MockTTSProvider,
    MockVideoGenerationProvider,
)
from app.providers.volcengine_tts import VolcengineTTSProvider
from app.providers.volcengine_video import VolcengineVideoProvider
from app.services.storyboard_prompt_engine import StoryboardPromptEngine
from tests.helpers import build_test_settings, workspace_tempdir


class MockProviderTests(unittest.TestCase):
    def test_mock_providers_generate_local_assets(self) -> None:
        llm = MockLLMProvider()
        video_provider = MockVideoGenerationProvider()
        image_provider = MockImageGenerationProvider()
        tts_provider = MockTTSProvider()
        subtitle_provider = LocalSubtitleProvider()
        engine = StoryboardPromptEngine()

        content = ContentInput(
            title="Grid dispatch explainer",
            raw_text=(
                "Grid dispatch needs load forecasting, renewable balancing, and reserve scheduling "
                "to keep electricity delivery stable during peak hours."
            ),
            mode=ContentMode.explain_mode,
            target_duration_seconds=24,
        )
        summary = llm.summarize_content(content)
        script = llm.generate_script(content, summary)
        shots = engine.split_storyboard(
            summary.title,
            summary.summary,
            script.full_script,
            content.mode,
            content.target_duration_seconds,
        )

        with workspace_tempdir() as output_dir:
            reference_image = Path(output_dir) / "reference.png"
            Image.new("RGB", (1280, 720), "#4C739F").save(reference_image)
            voice = tts_provider.synthesize(
                script,
                shots,
                output_dir / "audio",
                options=VoiceSynthesisOptions(voice="test_voice"),
            )
            subtitles = subtitle_provider.generate(shots, output_dir / "subtitles")
            generated_image = image_provider.generate(shots[0], output_dir / "images" / "shot_01", reference_image)
            clip = video_provider.text_to_video(shots[0], output_dir / "shots" / "shot_01")

            self.assertTrue(Path(voice.audio_path).exists())
            self.assertTrue(Path(subtitles.subtitle_path).exists())
            self.assertTrue(Path(generated_image.image_path).exists())
            self.assertTrue(Path(clip.video_path).exists())
            self.assertTrue(Path(clip.poster_path).exists())

    def test_volcengine_tts_uses_access_key_alias_header(self) -> None:
        settings = build_test_settings(Path("F:/AICODING/grid-video-agent-test"))
        settings = Settings(
            **{
                **settings.__dict__,
                "volcengine_tts_appid": "app-id-demo",
                "volcengine_tts_access_key": "access-key-demo",
                "volcengine_tts_token": "",
            }
        )
        provider = VolcengineTTSProvider(settings)

        headers = provider._build_async_headers("req-123")

        self.assertEqual(headers["X-Api-App-Id"], "app-id-demo")
        self.assertEqual(headers["X-Api-Access-Key"], "access-key-demo")
        self.assertNotIn("Authorization", headers)

    def test_volcengine_tts_online_payload_uses_cluster_contract(self) -> None:
        settings = build_test_settings(Path("F:/AICODING/grid-video-agent-test"))
        settings = Settings(
            **{
                **settings.__dict__,
                "volcengine_tts_appid": "app-id-demo",
                "volcengine_tts_token": "token-demo",
                "volcengine_tts_cluster": "volcano_tts",
            }
        )
        provider = VolcengineTTSProvider(settings)

        payload = provider._build_online_payload("test text", VoiceSynthesisOptions(voice="voice-demo"), "req-123")

        self.assertEqual(payload["app"]["appid"], "app-id-demo")
        self.assertEqual(payload["app"]["token"], "token-demo")
        self.assertEqual(payload["app"]["cluster"], "volcano_tts")
        self.assertEqual(payload["audio"]["voice_type"], "voice-demo")

    def test_seedance_operator_requires_api_key_when_only_ak_sk_is_set(self) -> None:
        settings = build_test_settings(Path("F:/AICODING/grid-video-agent-test"))
        settings = Settings(
            **{
                **settings.__dict__,
                "volcengine_ak": "AK-demo",
                "volcengine_sk": "SK-demo",
                "volcengine_video_submit_url": "https://operator.las.cn-beijing.volces.com/api/v1/contents/generations/tasks",
                "volcengine_video_query_url": "https://operator.las.cn-beijing.volces.com/api/v1/contents/generations/tasks/{task_id}",
            }
        )
        provider = VolcengineVideoProvider(settings)

        with self.assertRaises(ProviderNotConfiguredError):
            provider._build_operator_headers(
                method="POST",
                url=settings.volcengine_video_submit_url,
                payload={"model": "demo"},
            )

    def test_volcengine_video_builds_data_url_for_operator_image_input(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            settings = Settings(
                **{
                    **settings.__dict__,
                    "volcengine_video_api_key": "video-key-demo",
                    "volcengine_video_submit_url": "https://operator.las.cn-beijing.volces.com/api/v1/contents/generations/tasks",
                    "volcengine_video_query_url": "https://operator.las.cn-beijing.volces.com/api/v1/contents/generations/tasks/{task_id}",
                }
            )
            provider = VolcengineVideoProvider(settings)
            image_path = Path(temp_dir) / "shot.png"
            Image.new("RGB", (1280, 720), "#4C739F").save(image_path)

            image_reference = provider._build_operator_image_reference(image_path)

            self.assertTrue(image_reference.startswith("data:image/png;base64,"))
            self.assertTrue(provider._prefer_operator_endpoint())

    def test_volcengine_video_prefers_openapi_when_ak_sk_are_available(self) -> None:
        settings = build_test_settings(Path("F:/AICODING/grid-video-agent-test"))
        settings = Settings(
            **{
                **settings.__dict__,
                "volcengine_ak": "AK-demo",
                "volcengine_sk": "SK-demo",
                "volcengine_video_api_key": "video-key-demo",
                "volcengine_video_submit_url": "https://operator.las.cn-beijing.volces.com/api/v1/contents/generations/tasks",
                "volcengine_video_query_url": "https://operator.las.cn-beijing.volces.com/api/v1/contents/generations/tasks/{task_id}",
                "volcengine_video_use_operator": False,
            }
        )
        provider = VolcengineVideoProvider(settings)

        self.assertFalse(provider._prefer_operator_endpoint())

    def test_volcengine_video_openapi_payload_switches_req_key_by_mode(self) -> None:
        settings = build_test_settings(Path("F:/AICODING/grid-video-agent-test"))
        provider = VolcengineVideoProvider(
            Settings(
                **{
                    **settings.__dict__,
                    "volcengine_video_submit_url": "https://visual.volcengineapi.com",
                    "volcengine_video_query_url": "https://visual.volcengineapi.com",
                    "volcengine_video_text_req_key": "jimeng_t2v_v30_1080p",
                    "volcengine_video_image_req_key": "jimeng_i2v_first_v30_1080",
                }
            )
        )
        shot = StoryboardShot(
            shot_id=1,
            shot_duration=5,
            narration_text="test narration",
            subtitle_text="test subtitle",
            visual_prompt_cn="专业真实的中国电网调度中心，稳定运镜，无字幕无水印",
            visual_prompt_en="",
            shot_type=ShotType.broll,
            camera_movement="static",
            visual_keywords=["grid dispatch center"],
            safety_notes="avoid subtitles and watermarks",
            needs_real_material=False,
            aspect_ratio="16:9",
        )

        text_payload = provider._build_openapi_submit_payload(
            shot,
            req_key=provider._resolve_openapi_req_key(is_image_to_video=False),
            image_path=None,
            image_urls=None,
        )
        image_payload = provider._build_openapi_submit_payload(
            shot,
            req_key=provider._resolve_openapi_req_key(is_image_to_video=True),
            image_path=None,
            image_urls=["https://example.com/demo.png"],
        )

        self.assertEqual(text_payload["req_key"], "jimeng_t2v_v30_1080p")
        self.assertIn("aspect_ratio", text_payload)
        self.assertEqual(image_payload["req_key"], "jimeng_i2v_first_v30_1080")
        self.assertNotIn("aspect_ratio", image_payload)


if __name__ == "__main__":
    unittest.main()
