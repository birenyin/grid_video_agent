from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import httpx
from volcengine.visual.VisualService import VisualService

from app.core.config import Settings
from app.models.content import ImageGenerationResult, StoryboardShot
from app.providers.base import ImageGenerationProvider, ProviderContractError, ProviderNotConfiguredError
from app.utils.files import ensure_dir


class VolcengineImageProvider(ImageGenerationProvider):
    name = "volcengine_image"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if not settings.volcengine_ak or not settings.volcengine_sk:
            raise ProviderNotConfiguredError("VOLCENGINE_AK or VOLCENGINE_SK is missing for image generation.")

    def generate(
        self,
        shot: StoryboardShot,
        output_dir: Path,
        reference_image_path: Path,
    ) -> ImageGenerationResult:
        ensure_dir(output_dir)
        if not reference_image_path.exists():
            raise ProviderContractError(f"Reference image not found: {reference_image_path}")

        service = VisualService()
        service.set_ak(self.settings.volcengine_ak)
        service.set_sk(self.settings.volcengine_sk)

        submit_payload = self._build_submit_payload(shot, reference_image_path)
        submit_data = service.cv_sync2async_submit_task(submit_payload)
        self._raise_for_api_error("submit", submit_data)

        task_id = self._extract_task_id(submit_data)
        if not task_id:
            raise ProviderContractError("Volcengine image submit response did not contain a task id.")

        result_data: dict = {}
        image_url = ""
        image_b64 = ""
        for _ in range(self.settings.volcengine_image_max_polls):
            time.sleep(self.settings.volcengine_image_poll_seconds)
            result_data = service.cv_sync2async_get_result(self._build_query_payload(task_id))
            self._raise_for_api_error("query", result_data)
            task_status = self._extract_task_status(result_data)
            image_url = self._extract_image_url(result_data)
            image_b64 = self._extract_base64_image(result_data)
            if image_url or image_b64:
                break
            if task_status in {"expired", "not_found"}:
                raise ProviderContractError(f"Volcengine image task ended with status {task_status}.")

        if not image_url and not image_b64:
            raise ProviderContractError("Volcengine image query did not return an image.")

        image_path = output_dir / f"shot_{shot.shot_id:02d}.png"
        if image_url:
            with httpx.Client(timeout=120) as client:
                image_path.write_bytes(client.get(image_url, follow_redirects=True).content)
        else:
            image_path.write_bytes(base64.b64decode(image_b64))

        return ImageGenerationResult(
            provider_name=self.name,
            shot_id=shot.shot_id,
            image_path=str(image_path),
            public_image_url=image_url,
            raw_response={"submit": submit_data, "query": result_data},
        )

    def _build_submit_payload(self, shot: StoryboardShot, reference_image_path: Path) -> dict:
        width, height = self._canvas_size(shot.aspect_ratio)
        return {
            "req_key": self.settings.volcengine_image_req_key,
            "binary_data_base64": [base64.b64encode(reference_image_path.read_bytes()).decode("ascii")],
            "prompt": self._build_prompt(shot),
            "seed": -1,
            "use_rephraser": True,
            "width": width,
            "height": height,
        }

    def _build_query_payload(self, task_id: str) -> dict:
        return {
            "req_key": self.settings.volcengine_image_req_key,
            "task_id": task_id,
            "req_json": json.dumps({"return_url": True}, ensure_ascii=False),
        }

    def _build_prompt(self, shot: StoryboardShot) -> str:
        shot_theme = {
            "host": "参考图人物作为专业主播，面对镜头讲解",
            "explainer": "参考图人物作为电网讲解员，在场景中做专业说明",
            "broll": "参考图人物出现在电网相关场景中，作为讲解型人物或观察者",
            "data": "参考图人物站在数据大屏或调度界面前进行说明",
        }.get(shot.shot_type.value, "参考图人物出现在电网相关场景中")
        keywords = "、".join(shot.visual_keywords or ["调度中心大屏", "输电线路", "城市电网"])
        aspect_hint = "16:9 横屏" if shot.aspect_ratio == "16:9" else "9:16 竖屏"
        prompt = (
            "保持参考图中人物的面部特征、发型、服装风格和整体气质一致。"
            f"{shot_theme}。画面比例为{aspect_hint}。"
            f"场景元素聚焦：{keywords}。"
            "整体风格专业、真实、简洁、现代，偏蓝灰科技感，符合中国电网场景常识。"
            "不要出现任何中文、英文、数字字幕、标题条、logo、水印或可读屏幕文字。"
            "人物动作自然，设备细节可信，方便后期叠加独立字幕。"
        )
        if shot.safety_notes:
            prompt = f"{prompt} 补充约束：{shot.safety_notes}"
        return prompt

    def _canvas_size(self, aspect_ratio: str) -> tuple[int, int]:
        if aspect_ratio == "16:9":
            return 1664, 936
        return 936, 1664

    def _extract_task_id(self, payload: dict) -> str | None:
        value = payload.get("data", {}).get("task_id")
        return value if isinstance(value, str) and value else None

    def _extract_task_status(self, payload: dict) -> str | None:
        value = payload.get("data", {}).get("status")
        return value if isinstance(value, str) and value else None

    def _extract_image_url(self, payload: dict) -> str:
        image_urls = payload.get("data", {}).get("image_urls")
        if isinstance(image_urls, list) and image_urls:
            value = image_urls[0]
            if isinstance(value, str) and value:
                return value
        return ""

    def _extract_base64_image(self, payload: dict) -> str:
        image_data = payload.get("data", {}).get("binary_data_base64")
        if isinstance(image_data, list) and image_data:
            value = image_data[0]
            if isinstance(value, str) and value:
                return value
        return ""

    def _raise_for_api_error(self, stage: str, payload: dict) -> None:
        code = payload.get("code")
        if code in (10000, "10000"):
            return
        raise ProviderContractError(
            f"Volcengine image {stage} failed with code {code}: {payload.get('message', 'unknown error')}"
        )
