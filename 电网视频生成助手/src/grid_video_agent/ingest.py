from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from .models import GridNewsItem


RISKY_WORDS = [
    "突发事故",
    "大面积停电",
    "未经证实",
    "据传",
    "网传",
    "内部消息",
]

SOURCE_RELIABILITY = {
    "国家电网": 95,
    "南方电网": 95,
    "电力交易中心": 90,
    "能源局": 92,
    "发改委": 92,
    "官网": 88,
    "公众号": 75,
    "行业资讯": 68,
    "短视频": 55,
    "中国能源新闻网": 82,
}

FIELD_ALIASES = {
    "source": ["source", "来源", "平台"],
    "title": ["title", "标题"],
    "summary": ["summary", "摘要", "概述"],
    "published_at": ["published_at", "发布时间", "时间"],
    "url": ["url", "链接", "网址"],
    "tags": ["tags", "标签", "keywords"],
    "content": ["content", "正文", "内容"],
    "source_type": ["source_type", "来源类型"],
}

TAG_KEYWORDS = {
    "调度": ["调度", "运行方式", "电网调度"],
    "保供": ["保供", "迎峰度夏", "迎峰度冬", "保电"],
    "负荷": ["负荷", "用电量", "最大负荷"],
    "新能源": ["新能源", "风电", "光伏", "消纳"],
    "电力市场": ["电力市场", "市场化", "绿电交易"],
    "现货交易": ["现货", "出清", "报价", "交易规则"],
    "需求响应": ["需求响应", "削峰填谷"],
    "储能": ["储能", "电池储能"],
    "特高压": ["特高压", "换流站", "输电通道"],
    "运维": ["运维", "检修", "巡视", "设备治理"],
    "设备状态": ["设备状态", "变电站", "断路器", "主变", "线路"],
    "绿电": ["绿电", "绿证"],
    "充电": ["充电桩", "车网互动", "V2G"],
    "新型电力系统": ["新型电力系统", "源网荷储"],
}

POLICY_KEYWORDS = [
    "通知",
    "办法",
    "细则",
    "规则",
    "方案",
    "意见",
    "解读",
    "答记者问",
    "政策",
]

KNOWLEDGE_KEYWORDS = [
    "一图读懂",
    "一文读懂",
    "观察",
    "解析",
    "科普",
    "案例",
    "问答",
]


def load_news_items(input_path: Path) -> list[GridNewsItem]:
    files = discover_input_files(input_path)
    items: list[GridNewsItem] = []
    for file_path in files:
        items.extend(load_single_file(file_path))
    return items


def discover_input_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    files: list[Path] = []
    for suffix in ("*.json", "*.jsonl", "*.csv"):
        files.extend(sorted(input_path.rglob(suffix)))
    return files


def load_single_file(file_path: Path) -> list[GridNewsItem]:
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        records = raw if isinstance(raw, list) else raw.get("items", [])
        return [normalize_record(record) for record in records if isinstance(record, dict)]
    if suffix == ".jsonl":
        records = [
            json.loads(line)
            for line in file_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return [normalize_record(record) for record in records if isinstance(record, dict)]
    if suffix == ".csv":
        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return [normalize_record(dict(row)) for row in reader]
    raise ValueError(f"Unsupported input file: {file_path}")


def normalize_record(record: dict) -> GridNewsItem:
    normalized = {field: extract_field(record, aliases) for field, aliases in FIELD_ALIASES.items()}
    tags = normalized["tags"]
    if isinstance(tags, str):
        tags = [part.strip() for part in tags.replace("，", ",").split(",") if part.strip()]
    elif not isinstance(tags, list):
        tags = []

    source = str(normalized["source"] or "未知来源")
    title = str(normalized["title"] or "").strip()
    summary = str(normalized["summary"] or normalized["content"] or "").strip()
    content = str(normalized["content"] or summary).strip()
    published_at = str(normalized["published_at"] or "").strip()
    url = str(normalized["url"] or "").strip()
    source_type = infer_source_type(str(normalized["source_type"] or source))
    reliability_score = infer_reliability(source)

    if not tags:
        tags = infer_tags_from_text(f"{title}\n{summary}\n{content}")

    content_category = infer_content_category(f"{title}\n{summary}\n{content}")
    hotness_score = infer_hotness(title, summary, tags)
    compliance_flags = infer_compliance_flags(title, summary, content)
    dedupe_key = build_dedupe_key(title, summary, source)

    return GridNewsItem(
        source=source,
        title=title or "未命名资讯",
        summary=summary or "暂无摘要",
        published_at=published_at or "未知时间",
        url=url,
        tags=tags,
        content=content,
        source_type=source_type,
        content_category=content_category,
        reliability_score=reliability_score,
        hotness_score=hotness_score,
        dedupe_key=dedupe_key,
        compliance_flags=compliance_flags,
    )


def extract_field(record: dict, aliases: list[str]) -> object:
    for alias in aliases:
        if alias in record and record[alias] not in (None, ""):
            return record[alias]
    return ""


def infer_source_type(source: str) -> str:
    lowered = source.lower()
    if "官网" in source or "国家电网" in source or "南方电网" in source:
        return "official"
    if "公众号" in source:
        return "social"
    if "抖音" in source or "视频号" in source or "短视频" in source:
        return "video"
    if "交易中心" in source or "能源局" in source or "发改委" in source:
        return "institution"
    if lowered:
        return "media"
    return "unknown"


def infer_reliability(source: str) -> int:
    for key, score in SOURCE_RELIABILITY.items():
        if key in source:
            return score
    return 65


def infer_hotness(title: str, summary: str, tags: list[str]) -> int:
    score = 40 + min(len(summary) // 20, 20)
    joined = f"{title} {summary} {' '.join(tags)}"
    for keyword in ["负荷", "保供", "调度", "新能源", "交易", "现货", "迎峰度夏", "新型电力系统"]:
        if keyword in joined:
            score += 8
    return min(score, 100)


def infer_compliance_flags(title: str, summary: str, content: str) -> list[str]:
    text = f"{title} {summary} {content}"
    flags: list[str] = []
    for word in RISKY_WORDS:
        if word in {"据传", "网传"}:
            pattern = rf"(^|[，。；：“”‘’、\s]){word}($|[，。；：“”‘’、\s])"
            if re.search(pattern, text):
                flags.append(word)
            continue
        if word in text:
            flags.append(word)
    return flags


def infer_tags_from_text(text: str) -> list[str]:
    tags: list[str] = []
    for tag, keywords in TAG_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    return tags[:6]


def infer_content_category(text: str) -> str:
    if any(keyword in text for keyword in POLICY_KEYWORDS):
        return "policy"
    if any(keyword in text for keyword in KNOWLEDGE_KEYWORDS):
        return "knowledge"
    return "news"


def build_dedupe_key(title: str, summary: str, source: str) -> str:
    seed = f"{source}|{title[:40]}|{summary[:80]}"
    return hashlib.md5(seed.encode("utf-8")).hexdigest()


def dedupe_items(items: list[GridNewsItem]) -> tuple[list[GridNewsItem], int]:
    unique: list[GridNewsItem] = []
    seen_keys: set[str] = set()
    seen_titles: set[str] = set()
    duplicate_count = 0

    for item in items:
        title_key = item.title.strip()
        if item.dedupe_key in seen_keys or title_key in seen_titles:
            duplicate_count += 1
            continue
        seen_keys.add(item.dedupe_key)
        seen_titles.add(title_key)
        unique.append(item)
    return unique, duplicate_count


def split_safe_and_risky(items: list[GridNewsItem]) -> tuple[list[GridNewsItem], list[GridNewsItem]]:
    safe, risky = [], []
    for item in items:
        if item.reliability_score < 60 or item.compliance_flags:
            risky.append(item)
        else:
            safe.append(item)
    return safe, risky
