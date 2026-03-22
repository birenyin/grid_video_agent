from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image

from app.core.database import Database
from app.models.project import (
    CreateProjectFromFeedRequest,
    CreateProjectFromScriptRequest,
    CreateProjectFromTextRequest,
    ProjectStatus,
    RenderProjectRequest,
    WorkflowGenerateImagesRequest,
    WorkflowScriptUpdateRequest,
)
from app.services.project_service import ProjectOrchestrator
from tests.helpers import build_test_settings, workspace_tempdir


class OrchestrationTests(unittest.TestCase):
    def test_project_can_render_end_to_end_with_mock_providers(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            orchestrator = ProjectOrchestrator(settings=settings, database=Database(settings.database_path))

            project = orchestrator.create_from_text(
                CreateProjectFromTextRequest(
                    title="电网行业日报",
                    content_text="国家能源局发布电力市场相关工作安排，强调调度、保供和新能源消纳要协同推进，同时要求各地持续完善电力市场秩序。",
                    mode="news_mode",
                    target_duration_seconds=24,
                )
            )
            rendered = orchestrator.render_project(project.project_id, RenderProjectRequest())

            self.assertEqual(rendered.status, ProjectStatus.rendered)
            self.assertIsNotNone(rendered.artifacts.composition)
            self.assertIsNotNone(rendered.artifacts.publish_package)
            self.assertTrue(Path(rendered.artifacts.composition.video_path).exists())  # type: ignore[union-attr]
            self.assertTrue(Path(rendered.artifacts.publish_package.payload_path).exists())  # type: ignore[union-attr]
            self.assertGreater(len(orchestrator.database.list_provider_attempts(project.project_id)), 0)

    def test_project_can_render_script_case_in_image_audio_mode(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            orchestrator = ProjectOrchestrator(settings=settings, database=Database(settings.database_path))

            project = orchestrator.create_from_script(
                CreateProjectFromScriptRequest(
                    title="国家电网一分钟科普",
                    full_script=(
                        "家人们，你们知道电是怎么从电厂安全稳定地到你家的吗？"
                        "这背后离不开国家电网。"
                        "国家电网就像电力的超级快递员，负责把电送到千家万户。"
                        "调度中心则像24小时运转的指挥室，时刻平衡负荷和频率。"
                    ),
                    mode="explain_mode",
                    target_duration_seconds=16,
                )
            )
            rendered = orchestrator.render_project(
                project.project_id,
                RenderProjectRequest(render_mode="image_audio"),
            )

            self.assertEqual(rendered.status, ProjectStatus.rendered)
            self.assertEqual(rendered.artifacts.voice.provider_name, "mock_tts")  # type: ignore[union-attr]
            self.assertTrue(
                all(item.provider_name == "static_image_video" for item in rendered.artifacts.shot_videos)
            )
            self.assertTrue(Path(rendered.artifacts.composition.video_path).exists())  # type: ignore[union-attr]

    def test_project_can_render_image_audio_with_reference_image(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            orchestrator = ProjectOrchestrator(settings=settings, database=Database(settings.database_path))
            reference_image = Path(temp_dir) / "reference.png"
            Image.new("RGB", (1280, 720), "#4C739F").save(reference_image)

            project = orchestrator.create_from_script(
                CreateProjectFromScriptRequest(
                    title="国家电网科普案例",
                    full_script=(
                        "国家电网负责把电从电厂稳定送到千家万户。"
                        "调度中心像大脑一样实时关注负荷和频率。"
                        "特高压承担远距离大容量输电。"
                        "配电网负责最后一公里送电到户。"
                    ),
                    mode="explain_mode",
                    target_duration_seconds=18,
                    aspect_ratio="16:9",
                )
            )
            rendered = orchestrator.render_project(
                project.project_id,
                RenderProjectRequest(
                    render_mode="image_audio",
                    aspect_ratio="16:9",
                    reference_image_path=str(reference_image),
                ),
            )

            self.assertEqual(rendered.status, ProjectStatus.rendered)
            self.assertGreater(len(rendered.artifacts.shot_images), 0)
            self.assertTrue(all(Path(item.image_path).exists() for item in rendered.artifacts.shot_images))
            self.assertTrue(
                all(item.provider_name == "static_image_video" for item in rendered.artifacts.shot_videos)
            )
            self.assertTrue(Path(rendered.artifacts.composition.video_path).exists())  # type: ignore[union-attr]

    def test_project_uses_default_reference_image_when_request_omits_it(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            default_reference_image = Path(temp_dir) / "default_reference.png"
            Image.new("RGB", (1280, 720), "#55789A").save(default_reference_image)
            settings.default_reference_image_path = str(default_reference_image)
            orchestrator = ProjectOrchestrator(settings=settings, database=Database(settings.database_path))

            project = orchestrator.create_from_script(
                CreateProjectFromScriptRequest(
                    title="默认人物图回退案例",
                    full_script=(
                        "国家电网通过主网和配网把电力送到城市和家庭。"
                        "调度中心持续监测负荷、频率和备用容量。"
                        "当新能源波动变大时，系统会联动储能和可调机组。"
                        "这类科普视频如果没有单独上传参考图，也应该自动套用默认人物形象。"
                    ),
                    mode="explain_mode",
                    target_duration_seconds=18,
                    aspect_ratio="16:9",
                )
            )
            rendered = orchestrator.render_project(
                project.project_id,
                RenderProjectRequest(
                    render_mode="image_audio",
                    aspect_ratio="16:9",
                ),
            )

            self.assertEqual(rendered.status, ProjectStatus.rendered)
            self.assertEqual(rendered.artifacts.resolved_reference_image_path, str(default_reference_image))
            self.assertGreater(len(rendered.artifacts.shot_images), 0)
            self.assertTrue(all(Path(item.image_path).exists() for item in rendered.artifacts.shot_images))

    def test_workflow_script_update_can_save_manual_storyboard_edits(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            orchestrator = ProjectOrchestrator(settings=settings, database=Database(settings.database_path))
            project = orchestrator.create_from_script(
                CreateProjectFromScriptRequest(
                    title="工作流编辑测试",
                    full_script=(
                        "国家电网负责把电从电厂稳定送到家庭。"
                        "调度中心持续监测负荷和频率。"
                        "特高压负责跨区域大容量输电。"
                        "配电网解决最后一公里问题。"
                    ),
                    mode="explain_mode",
                    target_duration_seconds=20,
                )
            )

            edited_storyboard = [
                shot.model_copy(
                    update={
                        "narration_text": f"人工修改镜头 {shot.shot_id}",
                        "subtitle_text": f"人工修改字幕 {shot.shot_id}",
                    }
                )
                for shot in project.storyboard
            ]
            updated = orchestrator.update_workflow_script(
                project.project_id,
                WorkflowScriptUpdateRequest(
                    title="工作流编辑测试（已修改）",
                    full_script="人工改写后的完整口播稿，强调调度中心、特高压和配电网之间的协同关系。",
                    summary="人工修改后的摘要",
                    mode="explain_mode",
                    target_duration_seconds=24,
                    aspect_ratio="9:16",
                    regenerate_storyboard=False,
                    storyboard=edited_storyboard,
                ),
            )

            self.assertEqual(updated.status, ProjectStatus.draft)
            self.assertEqual(updated.summary.title, "工作流编辑测试（已修改）")  # type: ignore[union-attr]
            self.assertEqual(updated.storyboard[0].narration_text, "人工修改镜头 1")
            self.assertEqual(updated.storyboard[0].subtitle_text, "人工修改字幕 1")
            self.assertEqual(updated.artifacts.shot_images, [])

    def test_rpa_project_falls_back_to_newsroom_preview_images_without_reference(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            settings.default_reference_image_path = ""
            orchestrator = ProjectOrchestrator(settings=settings, database=Database(settings.database_path))
            feed_path = Path(__file__).resolve().parents[1] / "data" / "input" / "rpa_raw_feed.json"

            project = orchestrator.create_from_rpa_feed(
                CreateProjectFromFeedRequest(
                    feed_path=str(feed_path),
                    aspect_ratio="16:9",
                    target_duration_seconds=30,
                    render_preview_bundle=True,
                )
            )
            rendered = orchestrator.render_project(
                project.project_id,
                RenderProjectRequest(
                    render_mode="image_audio",
                    aspect_ratio="16:9",
                ),
            )

            self.assertEqual(rendered.status, ProjectStatus.rendered)
            self.assertEqual(rendered.artifacts.resolved_reference_image_path, "")
            self.assertTrue(any(item.provider_name == "newsroom_preview" for item in rendered.artifacts.shot_images))
            self.assertTrue(Path(rendered.artifacts.composition.video_path).exists())  # type: ignore[union-attr]

    def test_workflow_image_stage_and_render_stage_can_reuse_generated_images(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            default_reference_image = Path(temp_dir) / "workflow_default_reference.png"
            Image.new("RGB", (1280, 720), "#395F8C").save(default_reference_image)
            settings.default_reference_image_path = str(default_reference_image)
            orchestrator = ProjectOrchestrator(settings=settings, database=Database(settings.database_path))
            project = orchestrator.create_from_script(
                CreateProjectFromScriptRequest(
                    title="工作流镜头图复用测试",
                    full_script=(
                        "国家电网负责把电能稳定送到城市和家庭。"
                        "调度中心像大脑一样协调整个系统。"
                        "特高压负责远距离大容量输电。"
                        "配电网负责把电精准送到用户身边。"
                    ),
                    mode="explain_mode",
                    target_duration_seconds=18,
                    aspect_ratio="16:9",
                )
            )

            staged = orchestrator.generate_workflow_images(
                project.project_id,
                WorkflowGenerateImagesRequest(
                    aspect_ratio="16:9",
                    reference_image_path=None,
                ),
            )
            image_paths_before_render = {item.shot_id: item.image_path for item in staged.artifacts.shot_images}
            rendered = orchestrator.render_workflow_project(
                project.project_id,
                RenderProjectRequest(
                    render_mode="image_audio",
                    aspect_ratio="16:9",
                    reuse_existing_shot_images=True,
                ),
            )

            self.assertEqual(rendered.status, ProjectStatus.rendered)
            self.assertGreater(len(rendered.artifacts.shot_images), 0)
            self.assertEqual(
                {item.shot_id: item.image_path for item in rendered.artifacts.shot_images},
                image_paths_before_render,
            )
            self.assertTrue(Path(rendered.artifacts.composition.video_path).exists())  # type: ignore[union-attr]

    def test_project_can_render_stage_two_video_with_reference_image(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            orchestrator = ProjectOrchestrator(settings=settings, database=Database(settings.database_path))
            reference_image = Path(temp_dir) / "reference.png"
            Image.new("RGB", (1280, 720), "#6D8CAF").save(reference_image)

            project = orchestrator.create_from_script(
                CreateProjectFromScriptRequest(
                    title="电网阶段二图生视频",
                    full_script=(
                        "国家电网负责把电从电厂稳定送到千家万户。"
                        "调度中心像大脑一样实时关注负荷和频率。"
                        "特高压承担远距离大容量输电。"
                        "配电网负责把电精准送到用户侧。"
                    ),
                    mode="explain_mode",
                    target_duration_seconds=18,
                    aspect_ratio="16:9",
                )
            )
            rendered = orchestrator.render_project(
                project.project_id,
                RenderProjectRequest(
                    render_mode="video_audio",
                    aspect_ratio="16:9",
                    reference_image_path=str(reference_image),
                ),
            )

            self.assertEqual(rendered.status, ProjectStatus.rendered)
            self.assertGreater(len(rendered.artifacts.shot_images), 0)
            self.assertTrue(all(Path(item.image_path).exists() for item in rendered.artifacts.shot_images))
            self.assertTrue(all(Path(item.video_path).exists() for item in rendered.artifacts.shot_videos))
            self.assertTrue(
                all(item.provider_name == "static_image_video" for item in rendered.artifacts.shot_videos)
            )
            self.assertTrue(all(item.source_video_path for item in rendered.artifacts.shot_images))
            self.assertTrue(Path(rendered.artifacts.composition.video_path).exists())  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
