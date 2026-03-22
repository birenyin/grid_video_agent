from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.deps import get_orchestrator
from app.core.database import Database
from app.main import create_app
from app.services.project_service import ProjectOrchestrator
from tests.helpers import build_test_settings, workspace_tempdir


class ProjectWorkflowRouteTests(unittest.TestCase):
    def test_workflow_routes_can_update_script_generate_images_and_render(self) -> None:
        with workspace_tempdir() as temp_dir:
            settings = build_test_settings(Path(temp_dir))
            orchestrator = ProjectOrchestrator(settings=settings, database=Database(settings.database_path))
            app = create_app()
            app.dependency_overrides[get_orchestrator] = lambda: orchestrator
            client = TestClient(app)

            create_response = client.post(
                "/projects/create_from_script",
                json={
                    "title": "工作流路由测试",
                    "full_script": "国家电网负责把电稳定送到城市和家庭。调度中心实时平衡负荷和频率。特高压负责远距离输电。配电网完成最后一公里。",
                    "mode": "explain_mode",
                    "target_duration_seconds": 24,
                    "aspect_ratio": "16:9",
                },
            )
            self.assertEqual(create_response.status_code, 200)
            project_id = create_response.json()["project_id"]
            storyboard = create_response.json()["storyboard"]
            storyboard[0]["narration_text"] = "路由层人工修改后的镜头一"

            update_response = client.put(
                f"/projects/{project_id}/workflow/script",
                json={
                    "title": "工作流路由测试（修改）",
                    "full_script": "人工修改后的脚本，保留四段结构，方便三步工作流继续往下执行。",
                    "summary": "人工修改后的摘要",
                    "mode": "explain_mode",
                    "target_duration_seconds": 24,
                    "aspect_ratio": "16:9",
                    "regenerate_storyboard": False,
                    "storyboard": storyboard,
                },
            )
            self.assertEqual(update_response.status_code, 200)
            self.assertEqual(
                update_response.json()["project"]["storyboard"][0]["narration_text"],
                "路由层人工修改后的镜头一",
            )

            image_response = client.post(
                f"/projects/{project_id}/workflow/images",
                json={
                    "aspect_ratio": "16:9",
                    "reference_image_path": None,
                    "shot_reference_overrides": {},
                    "shot_ids": [],
                },
            )
            self.assertEqual(image_response.status_code, 200)
            self.assertGreater(len(image_response.json()["project"]["artifacts"]["shot_images"]), 0)

            render_response = client.post(
                f"/projects/{project_id}/workflow/render",
                json={
                    "preferred_voice": "professional_cn_male",
                    "publish_mode": "draft",
                    "render_mode": "image_audio",
                    "aspect_ratio": "16:9",
                    "reference_image_path": None,
                    "reuse_existing_shot_images": True,
                },
            )
            self.assertEqual(render_response.status_code, 200)
            self.assertEqual(render_response.json()["status"], "rendered")


if __name__ == "__main__":
    unittest.main()
