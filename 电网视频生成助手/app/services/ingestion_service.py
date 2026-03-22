from __future__ import annotations

import re
from html import unescape

import httpx

from app.models.content import ContentInput


class IngestionService:
    KEYWORDS = (
        "电网",
        "调度",
        "负荷",
        "保供",
        "新能源",
        "储能",
        "现货",
        "交易",
        "特高压",
        "变电站",
        "输电线路",
    )
    NAVIGATION_NOISE = (
        "当前位置",
        "上一篇",
        "下一篇",
        "相关阅读",
        "打印",
        "关闭窗口",
        "返回顶部",
        "版权",
        "网站地图",
    )

    def ingest_content(self, content_input: ContentInput) -> ContentInput:
        normalized_text = self._normalize_whitespace(content_input.raw_text)
        normalized_title = self._normalize_whitespace(content_input.title or "") or None
        keywords = self._extract_keywords(normalized_text)
        return content_input.model_copy(
            update={
                "raw_text": normalized_text,
                "title": normalized_title,
                "keywords": keywords,
            }
        )

    def fetch_url_content(self, source_url: str, timeout_seconds: float = 20.0) -> tuple[str | None, str]:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = client.get(source_url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type and response.text:
            body = self._normalize_whitespace(response.text)
            if len(body) < 40:
                raise ValueError("The fetched URL did not contain enough readable text.")
            return None, body

        html = response.text
        title = self._extract_html_title(html)
        body = self._extract_main_text(html)
        if len(body) < 80:
            raise ValueError("The fetched page did not contain enough article text to build a project.")
        return title, body

    def _normalize_whitespace(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _extract_keywords(self, text: str) -> list[str]:
        keywords: list[str] = []
        for keyword in self.KEYWORDS:
            if keyword in text and keyword not in keywords:
                keywords.append(keyword)
        return keywords[:8]

    def _extract_html_title(self, html: str) -> str | None:
        for pattern in (
            r"<h1[^>]*>(.*?)</h1>",
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
            r"<title[^>]*>(.*?)</title>",
        ):
            match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            title = self._strip_tags(match.group(1))
            title = self._normalize_whitespace(title)
            if title:
                return title[:120]
        return None

    def _extract_main_text(self, html: str) -> str:
        text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<noscript[\s\S]*?</noscript>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<!--[\s\S]*?-->", " ", text)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "\n", text)
        text = unescape(text)

        lines: list[str] = []
        seen: set[str] = set()
        total_chars = 0
        for raw_line in text.splitlines():
            line = self._normalize_whitespace(raw_line)
            if len(line) < 12:
                continue
            if any(noise in line for noise in self.NAVIGATION_NOISE):
                continue
            if line in seen:
                continue
            seen.add(line)
            lines.append(line)
            total_chars += len(line)
            if len(lines) >= 60 or total_chars >= 3000:
                break

        return "\n".join(lines)

    def _strip_tags(self, text: str) -> str:
        return unescape(re.sub(r"<[^>]+>", "", text))
