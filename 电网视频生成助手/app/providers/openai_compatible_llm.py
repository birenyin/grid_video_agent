from __future__ import annotations

import json

import httpx

from app.core.config import Settings
from app.models.content import ContentInput, ContentSummary, ScriptDraft
from app.providers.base import LLMProvider, ProviderContractError, ProviderNotConfiguredError


class OpenAICompatibleLLMProvider(LLMProvider):
    name = "openai_llm"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if not settings.llm_api_key:
            raise ProviderNotConfiguredError("LLM_API_KEY is not configured.")

    def summarize_content(self, content: ContentInput) -> ContentSummary:
        prompt = (
            "请把下面内容总结为适合中文电网短视频选题的结构化 JSON，字段必须包含 "
            "title、summary、bullet_points、key_facts、warnings、publish_angle。"
            f"\n\n内容：{content.raw_text}"
        )
        return ContentSummary.model_validate(self._chat_json(prompt))

    def generate_script(self, content: ContentInput, summary: ContentSummary) -> ScriptDraft:
        prompt = (
            "请基于下面摘要生成适合 30~90 秒中文电网视频的结构化 JSON，字段必须包含 "
            "title、intro_hook、full_script、closing、review_notes。"
            f"\n\n摘要：{summary.model_dump_json()}"
        )
        return ScriptDraft.model_validate(self._chat_json(prompt))

    def _chat_json(self, prompt: str) -> dict:
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": "你是专业的中文电网短视频策划助手，只输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self.settings.llm_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderContractError(f"Unexpected LLM response: {data}") from exc
