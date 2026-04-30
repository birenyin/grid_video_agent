from __future__ import annotations

import json
import re
import ssl
from dataclasses import asdict, dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib import error, parse, request

from .config import AgentConfig
from .ingest import (
    build_dedupe_key,
    infer_compliance_flags,
    infer_content_category,
    infer_hotness,
    infer_tags_from_text,
)
from .models import GridNewsItem
from .sources import WebSource, get_sources


NAVIGATION_NOISE = (
    "首页",
    "当前位置",
    "返回顶部",
    "上一篇",
    "下一篇",
    "相关阅读",
    "责任编辑",
    "打印",
    "关闭窗口",
    "版权所有",
    "网站地图",
    "相关链接",
    "热点推荐",
)

NON_EDITORIAL_KEYWORDS = (
    "新春走基层",
    "影像南网",
    "人物故事",
    "员工风采",
    "文艺",
    "摄影",
)

BLOCKED_URL_PARTS = (
    "javascript:",
    "mailto:",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    "weixin.qq.com",
    "mp.weixin.qq.com",
    "login",
    "mailto",
)

TOPIC_KEYWORDS = {
    "policy_regulation": ("政策", "通知", "办法", "规则", "监管", "交易规则", "现货"),
    "dispatch_operation": ("调度", "保供", "负荷", "频率", "运行", "迎峰度夏", "迎峰度冬"),
    "new_energy": ("新能源", "风电", "光伏", "消纳", "储能", "源网荷储"),
    "power_market": ("电力市场", "现货", "交易", "报价", "结算", "绿电", "辅助服务"),
    "distribution_service": ("配电", "供电", "居民", "民生", "充电", "最后一公里"),
    "equipment_maintenance": ("设备", "变电站", "线路", "巡检", "运维", "检修", "主变"),
}


@dataclass
class LinkCandidate:
    url: str
    text: str
    score: int


class AnchorExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href = ""
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = dict(attrs)
        self._current_href = attr_map.get("href") or ""
        self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._current_href:
            return
        text = " ".join(part.strip() for part in self._current_text if part.strip()).strip()
        self.links.append((self._current_href, text))
        self._current_href = ""
        self._current_text = []


def fetch_latest_grid_items(
    config: AgentConfig,
    output_dir: Path,
    source_set: str | None = None,
    per_source_limit: int | None = None,
    total_limit: int | None = None,
) -> tuple[list[GridNewsItem], list[str]]:
    active_sources = get_sources(source_set or config.source_set)
    notes: list[str] = []
    items: list[GridNewsItem] = []

    for source in active_sources:
        try:
            items.extend(
                fetch_source_items(
                    source,
                    limit=per_source_limit or config.per_source_limit,
                    timeout_seconds=config.fetch_timeout_seconds,
                    user_agent=config.user_agent,
                )
            )
        except Exception as exc:
            notes.append(f"{source.name} 抓取失败：{exc}")

    if total_limit or config.total_fetch_limit:
        items = sorted(items, key=lambda item: item.hotness_score, reverse=True)[
            : total_limit or config.total_fetch_limit
        ]

    focused_items, focus_notes = filter_items_by_topics(items, config.focus_topics)
    if focused_items:
        items = focused_items
    notes.extend(focus_notes)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "fetched_feed.json").write_text(
        json.dumps([asdict(item) for item in items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return items, notes


def filter_items_by_topics(items: list[GridNewsItem], focus_topics: tuple[str, ...] | list[str]) -> tuple[list[GridNewsItem], list[str]]:
    topics = [topic for topic in focus_topics if topic in TOPIC_KEYWORDS]
    if not topics:
        return items, []

    matched: list[GridNewsItem] = []
    for item in items:
        haystack = " ".join(
            [
                item.title,
                item.summary,
                item.content,
                " ".join(item.tags),
                item.content_category,
            ]
        )
        if any(keyword in haystack for topic in topics for keyword in TOPIC_KEYWORDS[topic]):
            matched.append(item)

    if matched:
        return matched, [f"Focused crawl kept {len(matched)} items for topics: {', '.join(topics)}."]
    return items, [f"No fetched items matched topics: {', '.join(topics)}. Fell back to all fetched items."]


def fetch_source_items(
    source: WebSource,
    limit: int,
    timeout_seconds: int,
    user_agent: str,
) -> list[GridNewsItem]:
    list_html = fetch_text(source.list_url, timeout_seconds, user_agent)
    link_candidates = extract_candidate_links(list_html, source.list_url, source)

    items: list[GridNewsItem] = []
    for candidate in link_candidates:
        try:
            article_html = fetch_text(candidate.url, timeout_seconds, user_agent)
            item = parse_article_html(article_html, candidate.url, source)
        except Exception:
            continue
        if item is None:
            continue
        items.append(item)
        if len(items) >= limit:
            break
    return items


def fetch_text(url: str, timeout_seconds: int, user_agent: str) -> str:
    req = request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            content_type = response.headers.get_content_charset() or "utf-8"
            body = response.read()
    except error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, ssl.SSLCertVerificationError):
            insecure_context = ssl._create_unverified_context()
            with request.urlopen(req, timeout=timeout_seconds, context=insecure_context) as response:
                content_type = response.headers.get_content_charset() or "utf-8"
                body = response.read()
        else:
            raise
    return body.decode(content_type, errors="ignore")


def extract_candidate_links(html: str, base_url: str, source: WebSource) -> list[LinkCandidate]:
    parser = AnchorExtractor()
    parser.feed(html)

    candidates: list[LinkCandidate] = []
    seen_urls: set[str] = set()

    for href, text in parser.links:
        url = parse.urljoin(base_url, href.strip())
        score = score_link(url, text, source)
        if score < 0 or url in seen_urls:
            continue
        seen_urls.add(url)
        candidates.append(LinkCandidate(url=url, text=text, score=score))

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[: source.max_links * 3]


def score_link(url: str, text: str, source: WebSource) -> int:
    parsed = parse.urlparse(url)
    lowered_url = url.lower()
    lowered_text = text.lower()

    if parsed.scheme not in {"http", "https"}:
        return -1
    if any(blocked in lowered_url for blocked in BLOCKED_URL_PARTS):
        return -1
    if source.allowed_domains and not any(parsed.netloc.endswith(domain) for domain in source.allowed_domains):
        return -1
    if any(keyword.lower() in lowered_url or keyword.lower() in lowered_text for keyword in source.exclude_keywords):
        return -1
    if len(text.strip()) < 6:
        return -1

    score = 0
    if any(keyword in url for keyword in source.article_url_keywords):
        score += 6
    for keyword in source.include_keywords:
        if keyword.lower() in lowered_url or keyword.lower() in lowered_text:
            score += 2
    if re.search(r"/20\d{2}/", url):
        score += 3
    if re.search(r"20\d{2}", text):
        score += 1
    if any(noise in text for noise in NAVIGATION_NOISE):
        score -= 4
    return score


def parse_article_html(html: str, url: str, source: WebSource) -> GridNewsItem | None:
    title = extract_title(html)
    if not title:
        return None

    plain_text = html_to_text(html)
    lines = clean_text_lines(plain_text)
    published_at = extract_publish_time(html, lines, url)
    content_lines = pick_content_lines(lines, title)
    if not content_lines:
        return None

    content = "\n".join(content_lines[:12])
    if not is_grid_relevant(title, content):
        return None

    summary = build_summary(content_lines)
    full_text = f"{title}\n{summary}\n{content}"
    tags = infer_tags_from_text(full_text)
    content_category = infer_content_category(full_text) or source.default_category

    return GridNewsItem(
        source=source.publisher,
        title=title,
        summary=summary,
        published_at=published_at,
        url=url,
        tags=tags,
        content=content,
        source_type=source.source_type,
        content_category=content_category,
        reliability_score=source.reliability_score,
        hotness_score=infer_hotness(title, summary, tags),
        dedupe_key=build_dedupe_key(title, summary, source.publisher),
        compliance_flags=infer_compliance_flags(title, summary, content),
    )


def extract_title(html: str) -> str:
    for pattern in (
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+name=["\']Title["\'][^>]+content=["\'](.*?)["\']',
        r"<h1[^>]*>(.*?)</h1>",
        r"<title[^>]*>(.*?)</title>",
    ):
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            title = strip_tags(match.group(1))
            title = normalize_space(title)
            if title:
                title = re.sub(r"---?国家能源局$", "", title).strip()
                title = re.sub(r"--?中国能源新闻网$", "", title).strip()
                title = re.sub(r"\s*-\s*(公司要闻|影像南网|新闻中心).*$", "", title).strip()
                title = re.sub(r"\s*-\s*中国南方电网$", "", title).strip()
                return title
    return ""


def extract_publish_time(html: str, lines: list[str], url: str) -> str:
    for pattern in (
        r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})(?:日)?(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?",
        r"(20\d{6})",
    ):
        match = re.search(pattern, html)
        if match:
            groups = match.groups()
            if len(groups) == 6 and groups[0]:
                year, month, day, hour, minute, second = groups
                if hour and minute:
                    return f"{int(year):04d}-{int(month):02d}-{int(day):02d} {int(hour):02d}:{int(minute):02d}:{int(second or 0):02d}"
                return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            if len(groups) == 1 and groups[0]:
                stamp = groups[0]
                return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"

    for line in lines[:12]:
        match = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})(?:日)?", line)
        if match:
            year, month, day = match.groups()
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    url_match = re.search(r"/(20\d{2})/(0?\d{1,2})/", url)
    if url_match:
        year, month = url_match.groups()
        return f"{int(year):04d}-{int(month):02d}-01"
    return "未知时间"


def html_to_text(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"<[^>]+>", "\n", text)
    return unescape(text)


def clean_text_lines(text: str) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = normalize_space(raw_line)
        if len(line) < 8:
            continue
        if line in seen:
            continue
        if any(noise in line for noise in NAVIGATION_NOISE):
            continue
        if re.fullmatch(r"[\d:./-]+", line):
            continue
        seen.add(line)
        lines.append(line)
    return lines


def pick_content_lines(lines: list[str], title: str) -> list[str]:
    content_lines: list[str] = []
    skipping = True

    for line in lines:
        if title in line:
            skipping = False
            continue
        if any(stop_word in line for stop_word in ("责任编辑", "相关阅读", "下一篇", "上一篇", "版权声明")):
            break
        if skipping and re.search(r"20\d{2}[-/.年]", line):
            skipping = False
            continue
        if skipping:
            continue
        if len(line) < 12:
            continue
        content_lines.append(line)

    if content_lines:
        return content_lines
    return [line for line in lines if line != title][:8]


def build_summary(content_lines: list[str]) -> str:
    summary = " ".join(content_lines[:2])
    summary = summary[:180].strip()
    return summary or "暂无摘要"


def is_grid_relevant(title: str, content: str) -> bool:
    text = f"{title}\n{content}"
    if any(keyword in text for keyword in NON_EDITORIAL_KEYWORDS):
        return False
    keyword_hits = sum(
        1
        for keyword in (
            "电网",
            "电力",
            "调度",
            "保供",
            "负荷",
            "新能源",
            "市场",
            "现货",
            "储能",
            "特高压",
            "供电",
        )
        if keyword in text
    )
    return keyword_hits >= 1


def strip_tags(text: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", text))


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
