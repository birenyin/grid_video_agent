from __future__ import annotations

import base64
import re
import time
from pathlib import Path

import httpx
import imageio.v2 as imageio
from volcengine.visual.VisualService import VisualService

from app.core.config import Settings
from app.models.content import StoryboardShot, VideoGenerationResult
from app.providers.base import ProviderContractError, ProviderNotConfiguredError, VideoGenerationProvider
from app.utils.files import ensure_dir
from app.utils.volcengine import build_signed_headers, format_task_url, is_seedance_operator_url


class VolcengineVideoProvider(VideoGenerationProvider):
    name = "volcengine_video"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if not settings.volcengine_video_submit_url or not settings.volcengine_video_query_url:
            raise ProviderNotConfiguredError(
                "VOLCENGINE_VIDEO_SUBMIT_URL or VOLCENGINE_VIDEO_QUERY_URL is not configured."
            )

    def text_to_video(self, shot: StoryboardShot, output_dir: Path) -> VideoGenerationResult:
        req_key = self._resolve_openapi_req_key(is_image_to_video=False)
        if self._prefer_operator_endpoint():
            return self._submit_and_poll_operator(
                shot,
                output_dir,
                self._build_operator_submit_payload(shot, image_reference=None),
            )
        if self.settings.volcengine_ak and self.settings.volcengine_sk:
            return self._submit_and_poll_openapi(
                shot,
                output_dir,
                req_key=req_key,
                image_path=None,
                image_urls=None,
            )
        return self._submit_and_poll_operator(
            shot,
            output_dir,
            self._build_operator_submit_payload(shot, image_reference=None),
        )

    def image_to_video(self, shot: StoryboardShot, image_path: Path, output_dir: Path) -> VideoGenerationResult:
        req_key = self._resolve_openapi_req_key(is_image_to_video=True)
        if self._prefer_operator_endpoint():
            return self._submit_and_poll_operator(
                shot,
                output_dir,
                self._build_operator_submit_payload(shot, image_reference=self._build_operator_image_reference(image_path)),
            )
        if self.settings.volcengine_ak and self.settings.volcengine_sk:
            return self._submit_and_poll_openapi(
                shot,
                output_dir,
                req_key=req_key,
                image_path=image_path,
                image_urls=None,
            )
        return self._submit_and_poll_operator(
            shot,
            output_dir,
            self._build_operator_submit_payload(shot, image_reference=self._build_operator_image_reference(image_path)),
        )

    def image_url_to_video(self, shot: StoryboardShot, image_url: str, output_dir: Path) -> VideoGenerationResult:
        req_key = self._resolve_openapi_req_key(is_image_to_video=True)
        if self._prefer_operator_endpoint():
            return self._submit_and_poll_operator(
                shot,
                output_dir,
                self._build_operator_submit_payload(shot, image_reference=image_url),
            )
        if self.settings.volcengine_ak and self.settings.volcengine_sk:
            return self._submit_and_poll_openapi(
                shot,
                output_dir,
                req_key=req_key,
                image_path=None,
                image_urls=[image_url],
            )
        with httpx.Client(timeout=120) as client:
            temp_image_path = output_dir / f"shot_{shot.shot_id:02d}_source.png"
            ensure_dir(output_dir)
            temp_image_path.write_bytes(client.get(image_url, follow_redirects=True).content)
        return self.image_to_video(shot, temp_image_path, output_dir)

    def _submit_and_poll_openapi(
        self,
        shot: StoryboardShot,
        output_dir: Path,
        *,
        req_key: str,
        image_path: Path | None,
        image_urls: list[str] | None,
    ) -> VideoGenerationResult:
        ensure_dir(output_dir)
        service = VisualService()
        service.set_ak(self.settings.volcengine_ak)
        service.set_sk(self.settings.volcengine_sk)
        submit_payload = self._build_openapi_submit_payload(
            shot,
            req_key=req_key,
            image_path=image_path,
            image_urls=image_urls,
        )
        submit_data = service.cv_sync2async_submit_task(submit_payload)
        self._raise_for_api_error("submit", submit_data)

        task_id = self._extract_task_id(submit_data)
        if not task_id:
            raise ProviderContractError("Volcengine video submit response did not contain a task id.")

        result_data: dict = {}
        download_url = ""
        for _ in range(self.settings.volcengine_video_max_polls):
            time.sleep(self.settings.volcengine_video_poll_seconds)
            result_data = service.cv_sync2async_get_result(self._build_openapi_query_payload(task_id, req_key=req_key))
            self._raise_for_api_error("query", result_data)
            task_status = self._extract_task_status(result_data)
            download_url = self._extract_download_url(result_data)
            if download_url:
                break
            if task_status in {"failed", "FAILURE", "error"}:
                raise ProviderContractError(
                    f"Volcengine video task failed with status {task_status}: {self._extract_message(result_data)}"
                )

        if not download_url:
            raise ProviderContractError("Volcengine video query did not return a downloadable video URL.")

        video_path = output_dir / f"shot_{shot.shot_id:02d}.mp4"
        poster_path = output_dir / f"shot_{shot.shot_id:02d}.png"
        with httpx.Client(timeout=120) as client:
            video_path.write_bytes(client.get(download_url, follow_redirects=True).content)
        self._ensure_poster_from_video(video_path, poster_path)
        return VideoGenerationResult(
            provider_name=self.name,
            shot_id=shot.shot_id,
            video_path=str(video_path),
            poster_path=str(poster_path),
            task_id=task_id,
            raw_response={"submit": submit_data, "query": result_data, "req_key": req_key},
        )

    def _submit_and_poll_operator(self, shot: StoryboardShot, output_dir: Path, payload: dict) -> VideoGenerationResult:
        ensure_dir(output_dir)
        with httpx.Client(timeout=120) as client:
            submit_response = self._request_json(
                client=client,
                method=self.settings.volcengine_video_submit_method,
                url=self.settings.volcengine_video_submit_url,
                payload=payload,
            )
            submit_data = self._read_json_response("submit", submit_response)
            self._raise_for_api_error("submit", submit_data)
            task_id = self._extract_task_id(submit_data)
            if not task_id:
                raise ProviderContractError("Volcengine video submit response did not contain a task id.")

            result_data: dict = {}
            download_url = ""
            poster_url = ""
            for _ in range(self.settings.volcengine_video_max_polls):
                time.sleep(self.settings.volcengine_video_poll_seconds)
                query_url = format_task_url(self.settings.volcengine_video_query_url, task_id)
                query_payload = None
                if "{task_id}" not in self.settings.volcengine_video_query_url and "{id}" not in self.settings.volcengine_video_query_url:
                    query_payload = {"task_id": task_id}
                query_response = self._request_json(
                    client=client,
                    method=self.settings.volcengine_video_query_method,
                    url=query_url,
                    payload=query_payload,
                )
                result_data = self._read_json_response("query", query_response)
                self._raise_for_api_error("query", result_data)
                task_status = self._extract_task_status(result_data)
                download_url = self._extract_download_url(result_data)
                poster_url = self._extract_poster_url(result_data)
                if download_url:
                    break
                if task_status in {"failed", "FAILURE", "error", "cancelled", "expired"}:
                    raise ProviderContractError(
                        f"Volcengine video task failed with status {task_status}: {self._extract_message(result_data)}"
                    )

            if not download_url:
                raise ProviderContractError("Volcengine video query did not return a downloadable video URL.")

            video_path = output_dir / f"shot_{shot.shot_id:02d}.mp4"
            poster_path = output_dir / f"shot_{shot.shot_id:02d}.png"
            video_path.write_bytes(client.get(download_url, follow_redirects=True).content)
            if poster_url:
                poster_path.write_bytes(client.get(poster_url, follow_redirects=True).content)
            else:
                self._ensure_poster_from_video(video_path, poster_path)

        return VideoGenerationResult(
            provider_name=self.name,
            shot_id=shot.shot_id,
            video_path=str(video_path),
            poster_path=str(poster_path),
            task_id=task_id,
            raw_response={"submit": submit_data, "query": result_data},
        )

    def _request_json(
        self,
        *,
        client: httpx.Client,
        method: str,
        url: str,
        payload: dict | None,
    ) -> httpx.Response:
        headers = self._build_operator_headers(method=method, url=url, payload=payload)
        request_args: dict[str, object] = {"headers": headers}
        if method.upper() != "GET" and payload is not None:
            request_args["json"] = payload
        elif payload:
            request_args["params"] = payload
        return client.request(method.upper(), url, **request_args)

    def _build_operator_headers(self, *, method: str, url: str, payload: dict | None) -> dict[str, str]:
        base_headers = {"Content-Type": "application/json"}
        if self.settings.volcengine_video_api_key:
            base_headers["Authorization"] = f"Bearer {self.settings.volcengine_video_api_key}"
            return base_headers
        if is_seedance_operator_url(url):
            raise ProviderNotConfiguredError(
                "The configured Seedance operator endpoint requires VOLCENGINE_VIDEO_API_KEY. "
                "AK/SK credentials are kept for the OpenAPI endpoint."
            )
        if self.settings.volcengine_ak and self.settings.volcengine_sk:
            return build_signed_headers(
                method=method,
                url=url,
                headers=base_headers,
                body=payload,
                ak=self.settings.volcengine_ak,
                sk=self.settings.volcengine_sk,
                service=self.settings.volcengine_video_service,
                region=self.settings.volcengine_video_region,
            )
        raise ProviderNotConfiguredError(
            "Volcengine video auth is not configured. Provide VOLCENGINE_VIDEO_API_KEY for the operator endpoint or AK/SK for OpenAPI."
        )

    def _build_openapi_submit_payload(
        self,
        shot: StoryboardShot,
        *,
        req_key: str,
        image_path: Path | None,
        image_urls: list[str] | None,
    ) -> dict:
        payload = {
            "req_key": req_key,
            "prompt": self._build_prompt(shot),
            "seed": -1,
            "frames": self._shot_duration_to_frames(shot.shot_duration),
        }
        if image_path is not None:
            payload["binary_data_base64"] = [base64.b64encode(image_path.read_bytes()).decode("ascii")]
            return payload
        if image_urls:
            payload["image_urls"] = image_urls
            return payload
        payload["aspect_ratio"] = shot.aspect_ratio or self.settings.volcengine_video_aspect_ratio
        return payload

    def _build_openapi_query_payload(self, task_id: str, *, req_key: str) -> dict:
        return {
            "req_key": req_key,
            "task_id": task_id,
        }

    def _build_operator_submit_payload(self, shot: StoryboardShot, image_reference: str | None) -> dict:
        prompt = self._build_prompt(shot)
        content: list[dict[str, str]] = [{"type": "text", "text": prompt}]
        if image_reference:
            content.insert(0, {"type": "image_url", "image_url": image_reference})
        return {
            "model": self.settings.volcengine_video_model,
            "content": content,
            "duration": shot.shot_duration,
            "resolution": shot.aspect_ratio or self.settings.volcengine_video_aspect_ratio,
            "watermark": False,
            "metadata": {
                "shot_id": shot.shot_id,
                "camera_movement": shot.camera_movement,
                "needs_real_material": shot.needs_real_material,
                "subtitle_text": shot.subtitle_text,
            },
            "callback_url": self.settings.volcengine_video_callback_url or None,
        }

    def _prefer_operator_endpoint(self) -> bool:
        if self.settings.volcengine_ak and self.settings.volcengine_sk and not self.settings.volcengine_video_use_operator:
            return False
        return bool(
            self.settings.volcengine_video_api_key
            and self.settings.volcengine_video_submit_url
            and self.settings.volcengine_video_query_url
        )

    def _build_operator_image_reference(self, image_path: Path) -> str:
        if image_path.exists():
            mime_type = self._guess_image_mime_type(image_path)
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            return f"data:{mime_type};base64,{encoded}"
        return str(image_path)

    def _guess_image_mime_type(self, image_path: Path) -> str:
        suffix = image_path.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if suffix == ".webp":
            return "image/webp"
        return "image/png"

    def _build_prompt(self, shot: StoryboardShot) -> str:
        prompt = shot.visual_prompt_cn
        if shot.safety_notes:
            return f"{prompt}\n补充约束：{shot.safety_notes}"
        if shot.safety_notes:
            prompt = f"{prompt}\n补充约束：{shot.safety_notes}"
        return prompt

    def _shot_duration_to_frames(self, duration_seconds: int) -> int:
        # Jimeng 3.0 Pro examples use 24fps-plus-1 frame counts such as 121 frames.
        return max(49, duration_seconds * 24 + 1)

    def _resolve_openapi_req_key(self, *, is_image_to_video: bool) -> str:
        if is_image_to_video:
            return self.settings.volcengine_video_image_req_key or self.settings.volcengine_video_req_key
        return self.settings.volcengine_video_text_req_key or self.settings.volcengine_video_req_key

    def _extract_task_id(self, payload: dict) -> str | None:
        for key_path in (
            ("task_id",),
            ("data", "task_id"),
            ("data", "id"),
            ("result", "task_id"),
            ("id",),
        ):
            value = payload
            for key in key_path:
                if not isinstance(value, dict) or key not in value:
                    value = None
                    break
                value = value[key]
            if isinstance(value, str) and value:
                return value
        return None

    def _extract_download_url(self, payload: dict) -> str:
        for key_path in (
            ("video_url",),
            ("data", "video_url"),
            ("data", "content", "video_url"),
            ("data", "result", "video_url"),
            ("data", "url"),
            ("result", "video_url"),
            ("output", "video_url"),
            ("data", "outputs", 0, "url"),
        ):
            value = payload
            for key in key_path:
                if isinstance(key, int):
                    if not isinstance(value, list) or len(value) <= key:
                        value = None
                        break
                    value = value[key]
                else:
                    if not isinstance(value, dict) or key not in value:
                        value = None
                        break
                    value = value[key]
            if isinstance(value, str) and value:
                return value
        return ""

    def _extract_poster_url(self, payload: dict) -> str:
        for key_path in (
            ("poster_url",),
            ("data", "poster_url"),
            ("data", "content", "last_frame_url"),
            ("data", "result", "poster_url"),
            ("output", "poster_url"),
        ):
            value = payload
            for key in key_path:
                if isinstance(key, int):
                    if not isinstance(value, list) or len(value) <= key:
                        value = None
                        break
                    value = value[key]
                else:
                    if not isinstance(value, dict) or key not in value:
                        value = None
                        break
                    value = value[key]
            if isinstance(value, str) and value:
                return value
        return ""

    def _extract_task_status(self, payload: dict) -> str | None:
        for key_path in (("status",), ("data", "status"), ("result", "status"), ("data", "task_status")):
            value = payload
            for key in key_path:
                if not isinstance(value, dict) or key not in value:
                    value = None
                    break
                value = value[key]
            if isinstance(value, str) and value:
                return value
        return None

    def _raise_for_api_error(self, stage: str, payload: dict) -> None:
        code = payload.get("code")
        if code not in (None, 0, "0", 10000, "10000", 20000000, "20000000"):
            raise ProviderContractError(
                f"Volcengine video {stage} failed with code {code}: {self._extract_message(payload)}"
            )
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message:
                raise ProviderContractError(f"Volcengine video {stage} failed: {message}")

    def _read_json_response(self, stage: str, response: httpx.Response) -> dict:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if response.is_error:
            message = self._extract_message(payload) if payload else response.text[:500]
            if response.status_code == 401 and self._looks_like_key_id(self.settings.volcengine_video_api_key):
                message = (
                    f"{message}. The configured VOLCENGINE_VIDEO_API_KEY looks like a key identifier/UUID "
                    "instead of the operator secret key."
                )
            raise ProviderContractError(
                f"Volcengine video {stage} HTTP {response.status_code}: {message or 'unknown error'}"
            )
        return payload

    def _extract_message(self, payload: dict) -> str:
        for key in ("message", "msg"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        error = payload.get("error")
        if isinstance(error, dict):
            value = error.get("message")
            if isinstance(value, str) and value:
                return value
        return "unknown error"

    def _ensure_poster_from_video(self, video_path: Path, poster_path: Path) -> None:
        reader = imageio.get_reader(video_path)
        try:
            frame = reader.get_data(0)
        finally:
            reader.close()
        imageio.imwrite(poster_path, frame)

    def _looks_like_key_id(self, value: str) -> bool:
        return bool(re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value.strip()))
