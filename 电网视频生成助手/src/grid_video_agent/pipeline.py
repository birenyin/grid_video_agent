from __future__ import annotations

import json
from pathlib import Path

from .config import AgentConfig
from .ingest import dedupe_items, load_news_items, split_safe_and_risky
from .llm import maybe_generate_with_llm
from .models import GridNewsItem, PipelineReport, VideoPlan, VideoSegment


PRIORITY_TAGS = {
    "调度": 30,
    "保供": 25,
    "负荷": 20,
    "新能源": 20,
    "电力市场": 20,
    "现货交易": 20,
    "需求响应": 15,
    "运维": 12,
    "设备状态": 10,
    "特高压": 14,
    "新型电力系统": 16,
}


def score_news(item: GridNewsItem) -> int:
    score = 20
    score += item.reliability_score // 3
    score += item.hotness_score // 2
    score += min(len(item.summary) // 12, 20)
    if item.content_category == "policy":
        score += 8
    if item.content_category == "knowledge":
        score += 5
    for tag in item.tags:
        score += PRIORITY_TAGS.get(tag, 0)
    return min(score, 100)


def select_news(items: list[GridNewsItem], limit: int = 2) -> list[GridNewsItem]:
    ranked = sorted(items, key=score_news, reverse=True)
    return ranked[:limit]


def build_title(items: list[GridNewsItem]) -> str:
    lead = items[0]
    joined = f"{lead.title} {lead.summary} {' '.join(lead.tags)}"
    if lead.content_category == "policy":
        return "这条电力新规，电网人最该盯哪几点？"
    if lead.content_category == "knowledge":
        return "这个电网知识点，很多人讲不清楚"
    if "负荷" in joined:
        return "电网负荷再冲高，这对调度意味着什么？"
    if "交易" in joined or "市场" in joined:
        return "电力市场规则又变了，一分钟看懂影响"
    return "今天电网行业最值得关注的两件事"


def build_cover_text(items: list[GridNewsItem]) -> str:
    lead = items[0]
    if lead.content_category == "policy":
        return "电力新规\n重点看这里"
    if lead.content_category == "knowledge":
        return "电网知识\n一分钟讲明白"
    if "负荷" in f"{lead.title} {lead.summary}":
        return "负荷新高\n调度怎么扛？"
    return "电网速递\n一分钟看懂"


def build_intro_hook(items: list[GridNewsItem]) -> str:
    lead = items[0]
    if lead.content_category == "policy":
        return f"先说结论，{lead.title} 不只是发文，它会直接影响调度、交易或者新能源参与方式。"
    if lead.content_category == "knowledge":
        return f"很多人听过 {lead.title}，但真正讲清楚它对电网运行有什么影响，其实并不容易。"
    return f"先说结论，{lead.title}，这不是普通新闻，它会直接影响一线调度和市场判断。"


def build_takeaway(items: list[GridNewsItem]) -> str:
    lead = items[0]
    if lead.content_category == "policy":
        return "真正要盯的是规则变化会不会传导到申报、出清、保供和运行方式。"
    if lead.content_category == "knowledge":
        return "把概念讲清楚的意义，在于能更快看懂后续新闻和运行变化。"
    return "真正值得关注的不是新闻本身，而是它背后的负荷变化、保供压力和市场信号。"


def build_hashtags(items: list[GridNewsItem]) -> list[str]:
    tags = ["#电网", "#电力行业", "#调度"]
    for item in items:
        for tag in item.tags[:3]:
            hashtag = f"#{tag}"
            if hashtag not in tags:
                tags.append(hashtag)
    return tags[:8]


def build_segments(items: list[GridNewsItem]) -> list[VideoSegment]:
    segments: list[VideoSegment] = [
        VideoSegment(
            scene=1,
            visual="封面标题快速切入，叠加调度大屏、负荷曲线或政策文件标题截图。",
            narration=build_intro_hook(items),
            subtitle=build_intro_hook(items),
        )
    ]

    scene_no = 2
    for item in items:
        impact = infer_impact(item)
        narration = f"{item.title}。{item.summary} 这条信息最关键的影响是：{impact}"
        segments.append(
            VideoSegment(
                scene=scene_no,
                visual=(
                    f"展示来源 {item.source} 的网页截图，标出发布时间 {item.published_at}，"
                    f"再高亮关键词：{'、'.join(item.tags[:3]) or '电网、调度、市场'}。"
                ),
                narration=narration,
                subtitle=narration,
            )
        )
        scene_no += 1

    closing = build_closing(items[0])
    segments.append(
        VideoSegment(
            scene=scene_no,
            visual="结尾强调关注点，出现账号名称、下期预告和关注引导。",
            narration=closing,
            subtitle=closing,
        )
    )
    return segments


def build_closing(lead: GridNewsItem) -> str:
    if lead.content_category == "policy":
        return "看政策不要只看标题，要看它会不会改变调度边界、市场规则和新能源消纳路径。"
    if lead.content_category == "knowledge":
        return "把概念理解透，后面再看负荷、保供、市场和新能源新闻，判断会快很多。"
    return (
        "如果你关注电网调度、市场和新能源消纳，记住一个判断标准："
        "凡是影响负荷、备用、出清和设备状态的消息，都值得重点盯。"
    )


def infer_impact(item: GridNewsItem) -> str:
    joined = f"{item.title} {item.summary} {' '.join(item.tags)}"
    if item.content_category == "policy":
        return "相关岗位需要尽快确认规则变动是否会传导到申报、结算、调度约束和运行安排。"
    if item.content_category == "knowledge":
        return "它能帮助从业者更快理解后续新闻背后的运行逻辑，而不是只看表面表述。"
    if "负荷" in joined or "保供" in joined:
        return "调度侧需要更关注负荷预测、需求响应和跨区支援能力。"
    if "市场" in joined or "交易" in joined:
        return "市场主体的申报和报价策略需要重新校准。"
    if "运维" in joined or "设备" in joined:
        return "运维侧要把设备状态变化前置到迎峰度夏准备中。"
    return "行业从业者需要尽快判断它是否会传导到运行方式和经营决策。"


def build_video_plan(items: list[GridNewsItem]) -> VideoPlan:
    selected = select_news(items)
    return VideoPlan(
        title=build_title(selected),
        cover_text=build_cover_text(selected),
        intro_hook=build_intro_hook(selected),
        takeaway=build_takeaway(selected),
        hashtags=build_hashtags(selected),
        selected_news=[
            {
                "source": item.source,
                "title": item.title,
                "score": score_news(item),
                "url": item.url,
                "published_at": item.published_at,
                "reliability_score": item.reliability_score,
                "hotness_score": item.hotness_score,
                "content_category": item.content_category,
                "tags": item.tags,
            }
            for item in selected
        ],
        segments=build_segments(selected),
        generation_mode="rule",
    )


def export_plan(plan: VideoPlan, output_dir: Path, report: PipelineReport | None = None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "video_plan.json").write_text(
        json.dumps(plan.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "video_script.md").write_text(render_markdown(plan), encoding="utf-8")
    (output_dir / "subtitles.srt").write_text(render_srt(plan), encoding="utf-8")
    (output_dir / "selected_sources.md").write_text(render_source_digest(plan), encoding="utf-8")
    if report is not None:
        (output_dir / "run_report.json").write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def render_markdown(plan: VideoPlan) -> str:
    lines = [
        f"# {plan.title}",
        "",
        f"封面文案：{plan.cover_text}",
        "",
        f"核心结论：{plan.takeaway}",
        "",
        f"生成模式：{plan.generation_mode}",
        "",
        "## 分镜脚本",
        "",
    ]
    if plan.warnings:
        lines.extend(["## 风险提醒", ""])
        for warning in plan.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    for segment in plan.segments:
        lines.extend(
            [
                f"### 镜头 {segment.scene}",
                f"- 画面：{segment.visual}",
                f"- 口播：{segment.narration}",
                f"- 字幕：{segment.subtitle}",
                "",
            ]
        )
    lines.extend(["## 入选来源", ""])
    for item in plan.selected_news:
        lines.append(f"- {item['title']} | {item['source']} | {item['published_at']} | {item['url']}")
    lines.extend(["", " ".join(plan.hashtags)])
    return "\n".join(lines)


def render_source_digest(plan: VideoPlan) -> str:
    lines = ["# 入选来源", ""]
    for index, item in enumerate(plan.selected_news, start=1):
        lines.extend(
            [
                f"## 来源 {index}",
                f"- 标题：{item['title']}",
                f"- 来源：{item['source']}",
                f"- 发布时间：{item['published_at']}",
                f"- 类别：{item['content_category']}",
                f"- 标签：{', '.join(item['tags'])}",
                f"- 链接：{item['url']}",
                "",
            ]
        )
    return "\n".join(lines)


def run_pipeline(input_path: Path, output_dir: Path, config: AgentConfig) -> tuple[VideoPlan, PipelineReport]:
    items = load_news_items(input_path)
    return run_pipeline_from_items(items, output_dir, config, input_mode="file")


def run_pipeline_from_items(
    raw_items: list[GridNewsItem],
    output_dir: Path,
    config: AgentConfig,
    input_mode: str,
    warnings: list[str] | None = None,
) -> tuple[VideoPlan, PipelineReport]:
    if not raw_items:
        raise ValueError("No grid news items were found for the pipeline.")

    deduped_items, duplicate_count = dedupe_items(raw_items)
    safe_items, risky_items = split_safe_and_risky(deduped_items)
    candidate_items = safe_items or deduped_items

    llm_plan = maybe_generate_with_llm(candidate_items, config)
    plan = llm_plan or build_video_plan(candidate_items)
    plan.generation_mode = llm_plan.generation_mode if llm_plan else "rule"

    runtime_warnings = list(warnings or [])
    if risky_items:
        runtime_warnings.extend(
            [
                f"{item.title} 来源可靠性较低或包含敏感表述，建议人工复核。"
                for item in risky_items[:5]
            ]
        )
    plan.warnings.extend(runtime_warnings)

    report = PipelineReport(
        total_items=len(raw_items),
        selected_items=len(plan.selected_news),
        dropped_items=max(len(raw_items) - len(candidate_items), 0),
        duplicate_items=duplicate_count,
        risky_items=len(risky_items),
        output_files=[
            str(output_dir / "video_plan.json"),
            str(output_dir / "video_script.md"),
            str(output_dir / "subtitles.srt"),
            str(output_dir / "selected_sources.md"),
            str(output_dir / "run_report.json"),
        ],
        input_mode=input_mode,
        source_count=len({item.source for item in raw_items}),
        warnings=runtime_warnings,
    )
    export_plan(plan, output_dir, report)
    return plan, report


def render_srt(plan: VideoPlan) -> str:
    duration_seconds = 60
    segment_count = max(len(plan.segments), 1)
    per_segment = max(duration_seconds // segment_count, 6)
    entries: list[str] = []
    current_start = 0

    for index, segment in enumerate(plan.segments, start=1):
        start = format_srt_time(current_start)
        current_end = current_start + per_segment
        if index == len(plan.segments):
            current_end = duration_seconds
        end = format_srt_time(current_end)
        entries.append("\n".join([str(index), f"{start} --> {end}", segment.subtitle]))
        current_start = current_end

    return "\n\n".join(entries) + "\n"


def format_srt_time(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},000"
