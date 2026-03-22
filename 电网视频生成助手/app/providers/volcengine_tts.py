from __future__ import annotations

import base64
import time
import uuid
import wave
from pathlib import Path

import httpx

from app.core.config import Settings
from app.models.content import ScriptDraft, StoryboardShot, TTSResult, VoiceSynthesisOptions
from app.providers.base import ProviderContractError, ProviderNotConfiguredError, TTSProvider
from app.utils.files import ensure_dir


class VolcengineTTSProvider(TTSProvider):
    name = "volcengine_tts"
    VOICE_ALIAS_MAP = {
        "professional_cn_male": "zh_male_m191_uranus_bigtts",
        "professional_cn_female": "zh_female_xiaohe_uranus_bigtts",
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.access_token = settings.volcengine_tts_token
        self.access_key = settings.volcengine_tts_access_key or settings.volcengine_tts_token
        if not settings.volcengine_tts_appid:
            raise ProviderNotConfiguredError("VOLCENGINE_TTS_APPID is missing.")
        if not self.access_token and not self.access_key:
            raise ProviderNotConfiguredError(
                "Configure VOLCENGINE_TTS_TOKEN for the online API or VOLCENGINE_TTS_ACCESS_KEY for the async API."
            )

    def synthesize(
        self,
        script: ScriptDraft,
        shots: list[StoryboardShot],
        output_dir: Path,
        options: VoiceSynthesisOptions,
    ) -> TTSResult:
        ensure_dir(output_dir)
        if self.settings.volcengine_tts_cluster and self.access_token:
            return self._synthesize_online(script, shots, output_dir, options)
        return self._synthesize_async(script, shots, output_dir, options)

    def _synthesize_online(
        self,
        script: ScriptDraft,
        shots: list[StoryboardShot],
        output_dir: Path,
        options: VoiceSynthesisOptions,
    ) -> TTSResult:
        request_id = uuid.uuid4().hex
        payload = self._build_online_payload(script.full_script, options, request_id)
        headers = self._build_online_headers()

        with httpx.Client(timeout=120) as client:
            response = client.post(self.settings.volcengine_tts_online_url, headers=headers, json=payload)
            response_payload = self._read_json_response("online_tts", response)
            self._raise_for_online_api_error(response_payload)
            audio_b64 = self._extract_base64_audio(response_payload)
            if not audio_b64:
                raise ProviderContractError("Volcengine online TTS did not return audio data.")

        audio_path = output_dir / f"voice_track.{options.format.lower()}"
        audio_path.write_bytes(base64.b64decode(audio_b64))
        duration_seconds = self._measure_duration_seconds(audio_path, float(sum(shot.shot_duration for shot in shots)))
        return TTSResult(
            provider_name=self.name,
            audio_path=str(audio_path),
            duration_seconds=duration_seconds,
            voice_name=options.voice,
            raw_response={"online": response_payload},
        )

    def _synthesize_async(
        self,
        script: ScriptDraft,
        shots: list[StoryboardShot],
        output_dir: Path,
        options: VoiceSynthesisOptions,
    ) -> TTSResult:
        if not self.access_key:
            raise ProviderNotConfiguredError("VOLCENGINE_TTS_ACCESS_KEY is missing for the async TTS API.")

        request_id = uuid.uuid4().hex
        payload = self._build_async_payload(script.full_script, options, request_id)
        headers = self._build_async_headers(request_id)

        with httpx.Client(timeout=120) as client:
            submit_response = client.post(self.settings.volcengine_tts_submit_url, headers=headers, json=payload)
            submit_data = self._read_json_response("submit", submit_response)
            self._raise_for_async_api_error("submit", submit_data)

            task_id = self._extract_task_id(submit_data)
            if not task_id:
                raise ProviderContractError("Volcengine async TTS submit response did not contain a task id.")

            audio_url = ""
            query_data: dict = {}
            for _ in range(self.settings.volcengine_tts_max_polls):
                time.sleep(self.settings.volcengine_tts_poll_seconds)
                query_response = client.post(
                    self.settings.volcengine_tts_query_url,
                    headers=headers,
                    json={"task_id": task_id},
                )
                query_data = self._read_json_response("query", query_response)
                self._raise_for_async_api_error("query", query_data)
                task_status = self._extract_task_status(query_data)
                audio_url = self._extract_audio_url(query_data)
                if audio_url and task_status not in {3, "3", "failed", "FAIL", "failure"}:
                    break
                if task_status in {3, "3", "failed", "FAIL", "failure"}:
                    raise ProviderContractError(
                        f"Volcengine async TTS task failed with status {task_status}: {self._extract_message(query_data)}"
                    )

            if not audio_url:
                raise ProviderContractError("Volcengine async TTS query did not return an audio URL.")

            audio_path = output_dir / f"voice_track.{options.format.lower()}"
            audio_path.write_bytes(client.get(audio_url, follow_redirects=True).content)
        duration_seconds = self._measure_duration_seconds(audio_path, float(sum(shot.shot_duration for shot in shots)))

        return TTSResult(
            provider_name=self.name,
            audio_path=str(audio_path),
            duration_seconds=duration_seconds,
            voice_name=options.voice,
            raw_response={"submit": submit_data, "query": query_data},
        )

    def _build_online_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer; {self.access_token}",
            "Content-Type": "application/json",
        }

    def _build_online_payload(self, text: str, options: VoiceSynthesisOptions, request_id: str) -> dict:
        voice_type = self._resolve_voice(options.voice)
        audio: dict[str, object] = {
            "voice_type": voice_type,
            "encoding": options.format,
            "compression_rate": 1,
            "rate": self.settings.volcengine_tts_sample_rate,
            "speed_ratio": options.speed,
            "volume_ratio": 1.0,
            "pitch_ratio": options.pitch,
            "language": "cn",
        }
        if options.emotion:
            audio["emotion"] = options.emotion
        return {
            "app": {
                "appid": self.settings.volcengine_tts_appid,
                "token": self.access_token,
                "cluster": self.settings.volcengine_tts_cluster,
            },
            "user": {"uid": self.settings.volcengine_tts_user_id},
            "audio": audio,
            "request": {
                "reqid": request_id,
                "text": text,
                "text_type": "plain",
                "operation": "query",
                "with_frontend": 1,
                "frontend_type": "unitTson",
            },
        }

    def _build_async_headers(self, request_id: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Api-App-Id": self.settings.volcengine_tts_appid,
            "X-Api-Access-Key": self.access_key,
            "X-Api-Request-Id": request_id,
            "X-Api-Resource-Id": self.settings.volcengine_tts_resource_id,
        }

    def _build_async_payload(self, text: str, options: VoiceSynthesisOptions, unique_id: str) -> dict:
        voice_type = self._resolve_voice(options.voice)
        audio_params: dict[str, object] = {
            "format": options.format,
            "sample_rate": self.settings.volcengine_tts_sample_rate,
        }
        speech_rate = self._to_speech_rate(options.speed)
        if speech_rate != 0:
            audio_params["speech_rate"] = speech_rate
        if options.emotion:
            audio_params["emotion"] = options.emotion
        req_params: dict[str, object] = {
            "text": text,
            "speaker": voice_type,
            "audio_params": audio_params,
        }
        if options.voice_clone_id:
            req_params["voice_clone_id"] = options.voice_clone_id
        return {
            "user": {"uid": self.settings.volcengine_tts_user_id},
            "unique_id": unique_id,
            "req_params": req_params,
        }

    def _to_speech_rate(self, speed: float) -> int:
        if abs(speed - 1.0) < 0.001:
            return 0
        scaled = int(round((speed - 1.0) * 100))
        return max(-50, min(100, scaled))

    def _resolve_voice(self, voice: str | None) -> str:
        if not voice:
            return self.settings.volcengine_tts_voice
        return self.VOICE_ALIAS_MAP.get(voice, voice)

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

    def _extract_audio_url(self, payload: dict) -> str:
        for key_path in (
            ("audio_url",),
            ("data", "audio_url"),
            ("data", "result", "audio_url"),
            ("data", "audio", "url"),
            ("data", "url"),
            ("result", "audio_url"),
            ("output", "audio_url"),
        ):
            value = payload
            for key in key_path:
                if not isinstance(value, dict) or key not in value:
                    value = None
                    break
                value = value[key]
            if isinstance(value, str) and value:
                return value
        return ""

    def _extract_base64_audio(self, payload: dict) -> str:
        for key_path in (("data",), ("audio", "data"), ("result", "data")):
            value = payload
            for key in key_path:
                if not isinstance(value, dict) or key not in value:
                    value = None
                    break
                value = value[key]
            if isinstance(value, str) and value:
                return value
        return ""

    def _extract_task_status(self, payload: dict) -> int | str | None:
        for key_path in (
            ("task_status",),
            ("data", "task_status"),
            ("result", "task_status"),
            ("status",),
        ):
            value = payload
            for key in key_path:
                if not isinstance(value, dict) or key not in value:
                    value = None
                    break
                value = value[key]
            if value is not None:
                return value
        return None

    def _raise_for_online_api_error(self, payload: dict) -> None:
        code = payload.get("code")
        if code not in (None, 3000, "3000", 0, "0"):
            raise ProviderContractError(
                f"Volcengine online TTS failed with code {code}: {self._extract_message(payload)}"
            )

    def _raise_for_async_api_error(self, stage: str, payload: dict) -> None:
        code = payload.get("code")
        if code in (None, 0, "0", 20000000, "20000000"):
            return
        raise ProviderContractError(
            f"Volcengine async TTS {stage} failed with code {code}: {self._extract_message(payload)}"
        )

    def _read_json_response(self, stage: str, response: httpx.Response) -> dict:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if response.is_error:
            message = self._extract_message(payload) if payload else response.text[:500]
            raise ProviderContractError(
                f"Volcengine TTS {stage} HTTP {response.status_code}: {message or 'unknown error'}"
            )
        return payload

    def _extract_message(self, payload: dict) -> str:
        for key in ("message", "msg", "error"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("message", "msg", "error"):
                value = data.get(key)
                if isinstance(value, str) and value:
                    return value
        return "unknown error"

    def _measure_duration_seconds(self, audio_path: Path, fallback: float) -> float:
        if audio_path.suffix.lower() != ".wav":
            return fallback
        with wave.open(str(audio_path), "rb") as wav_file:
            frame_rate = wav_file.getframerate()
            if frame_rate <= 0:
                return fallback
            return wav_file.getnframes() / frame_rate
