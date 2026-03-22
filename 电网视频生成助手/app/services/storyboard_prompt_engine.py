from __future__ import annotations

import re

from app.models.content import ContentMode, ShotType, StoryboardShot


class StoryboardPromptEngine:
    def split_storyboard(
        self,
        title: str,
        content_summary: str,
        full_script: str,
        mode: ContentMode,
        target_duration_seconds: int,
        aspect_ratio: str = "9:16",
    ) -> list[StoryboardShot]:
        sentences = self._split_sentences(full_script)
        if len(sentences) < 4:
            sentences.extend(self._build_padding_sentences(title, content_summary, mode))

        shot_count = max(8, min(18, len(sentences)))
        sentence_pool = sentences[:shot_count]
        durations = self._allocate_durations(len(sentence_pool), target_duration_seconds)

        shots: list[StoryboardShot] = []
        for index, (sentence, duration) in enumerate(zip(sentence_pool, durations), start=1):
            shot_type = self._infer_shot_type(index, sentence, mode)
            visual_keywords = self._build_visual_keywords(sentence, mode)
            needs_real_material = any(
                keyword in sentence for keyword in ("会议", "发布会", "政策原文", "现场画面", "新闻现场")
            )
            movement = self._camera_movement_for_shot_type(shot_type)
            visual_prompt_cn = self.build_video_generation_prompt(
                shot_id=index,
                narration_text=sentence,
                shot_type=shot_type,
                visual_keywords=visual_keywords,
                mode=mode,
                aspect_ratio=aspect_ratio,
            )
            visual_prompt_en = self._build_english_prompt(
                shot_type=shot_type,
                visual_keywords=visual_keywords,
                needs_real_material=needs_real_material,
                aspect_ratio=aspect_ratio,
            )
            shots.append(
                StoryboardShot(
                    shot_id=index,
                    shot_duration=duration,
                    aspect_ratio=aspect_ratio,
                    narration_text=sentence,
                    subtitle_text=sentence,
                    visual_prompt_cn=visual_prompt_cn,
                    visual_prompt_en=visual_prompt_en,
                    shot_type=shot_type,
                    camera_movement=movement,
                    visual_keywords=visual_keywords,
                    safety_notes="避免灾难化、事故化、夸张化呈现，保持中国电网场景可信与专业。",
                    needs_real_material=needs_real_material,
                )
            )
        return shots

    def build_video_generation_prompt(
        self,
        shot_id: int,
        narration_text: str,
        shot_type: ShotType,
        visual_keywords: list[str],
        mode: ContentMode,
        aspect_ratio: str = "9:16",
    ) -> str:
        shot_theme = {
            ShotType.host: "AI主播或讲解员正面讲解",
            ShotType.explainer: "工程师或讲解员结合场景口播说明",
            ShotType.broll: "电网运行、城市供电与设备运转 B-roll",
            ShotType.data: "数据卡片、调度大屏与负荷图表",
        }[shot_type]
        mode_hint = "科普讲解" if mode == ContentMode.explain_mode else "行业速递"
        aspect_hint = "16:9 横屏" if aspect_ratio == "16:9" else "9:16 竖屏"
        keywords = "、".join(visual_keywords) if visual_keywords else "调度中心大屏、输电线路、城市夜景电网"
        return (
            f"镜头 {shot_id}，{mode_hint}风格，{shot_theme}。"
            f"围绕“{narration_text}”生成 {aspect_hint} 的短视频画面。"
            f"重点元素包括：{keywords}。"
            "画面要专业、真实、简洁、现代，偏蓝灰科技风，镜头平稳推进或轻微平移，"
            "方便后期叠加中文字幕，不出现灾难化画面、错误制服标识和夸张特效。"
            "画面中不要出现任何中文、英文、数字字幕、标题条、logo、水印或可读屏幕文字。"
        )

    def _split_sentences(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        major_parts = re.split(r"[。！？!?；;]\s*", normalized)
        segments: list[str] = []
        for part in major_parts:
            cleaned = part.strip(" ，,：:")
            if not cleaned:
                continue
            if len(cleaned) <= 34:
                segments.append(cleaned)
                continue

            sub_parts = re.split(r"[，,：:]\s*", cleaned)
            buffer = ""
            for sub in sub_parts:
                sub = sub.strip()
                if not sub:
                    continue
                candidate = f"{buffer}，{sub}" if buffer else sub
                if len(candidate) <= 30:
                    buffer = candidate
                else:
                    if buffer:
                        segments.append(buffer)
                    buffer = sub
            if buffer:
                segments.append(buffer)
        return [segment for segment in segments if segment]

    def _build_padding_sentences(self, title: str, summary: str, mode: ContentMode) -> list[str]:
        base = [
            "这条内容的重要性，不只在于概念解释，更在于它背后的电网运行逻辑。",
            "如果你关注调度、运维或新能源消纳，这里面至少有一个关键点值得留意。",
            f"结合{title or '这条内容'}来看，更值得关注的是它会如何影响负荷、保供和系统协同。",
            "做电网科普视频时，要先讲清概念，再解释它和实际生活的关系。",
        ]
        if mode == ContentMode.explain_mode:
            base[0] = f"很多人听过这个概念，但要把“{title or summary[:12]}”讲明白并不容易。"
        return base

    def _allocate_durations(self, shot_count: int, target_duration_seconds: int) -> list[int]:
        min_total = shot_count * 3
        max_total = shot_count * 6
        target = max(min_total, min(max_total, target_duration_seconds))
        base = max(3, min(6, round(target / shot_count)))
        durations = [base for _ in range(shot_count)]
        current = sum(durations)

        while current < target:
            changed = False
            for index in range(shot_count):
                if durations[index] < 6 and current < target:
                    durations[index] += 1
                    current += 1
                    changed = True
            if not changed:
                break

        while current > target:
            changed = False
            for index in range(shot_count):
                if durations[index] > 3 and current > target:
                    durations[index] -= 1
                    current -= 1
                    changed = True
            if not changed:
                break
        return durations

    def _infer_shot_type(self, index: int, sentence: str, mode: ContentMode) -> ShotType:
        if index == 1:
            return ShotType.host
        if any(keyword in sentence for keyword in ("数据", "曲线", "比例", "增长", "下降", "系统", "负荷", "频率")):
            return ShotType.data
        if mode == ContentMode.explain_mode:
            return ShotType.explainer if index % 2 == 0 else ShotType.broll
        return ShotType.broll if index % 2 == 0 else ShotType.explainer

    def _camera_movement_for_shot_type(self, shot_type: ShotType) -> str:
        return {
            ShotType.host: "轻微推进",
            ShotType.explainer: "稳镜头或缓慢平移",
            ShotType.broll: "缓慢横移",
            ShotType.data: "定镜头加轻微缩放",
        }[shot_type]

    def _build_visual_keywords(self, sentence: str, mode: ContentMode) -> list[str]:
        keywords: list[str] = []
        candidates = (
            ("调度", "调度中心大屏"),
            ("控制", "电网控制室"),
            ("特高压", "特高压输电通道"),
            ("输电", "输电线路"),
            ("配电", "城市配电网络"),
            ("变电", "变电站"),
            ("家庭", "居民家庭用电场景"),
            ("快递", "物流类比信息卡片"),
            ("调度中心", "调度指挥大厅"),
            ("EMS", "EMS_SCADA系统界面"),
            ("SCADA", "EMS_SCADA系统界面"),
            ("风光", "新能源发电场站"),
            ("抽蓄", "抽水蓄能电站"),
            ("负荷", "负荷曲线"),
            ("频率", "频率监测图表"),
            ("协同", "源网荷储协同图解"),
            ("工厂", "工业负荷场景"),
            ("家门口", "居民家门口送电类比"),
            ("评论区", "主播收尾互动镜头"),
        )
        for trigger, keyword in candidates:
            if trigger in sentence:
                keywords.append(keyword)
        if mode == ContentMode.news_mode and "图表信息卡片" not in keywords:
            keywords.append("图表信息卡片")
        if not keywords:
            keywords = ["调度中心大屏", "输电线路", "城市夜景电网"]
        return list(dict.fromkeys(keywords))[:5]

    def _build_english_prompt(
        self,
        shot_type: ShotType,
        visual_keywords: list[str],
        needs_real_material: bool,
        aspect_ratio: str,
    ) -> str:
        keywords = ", ".join(visual_keywords or ["grid dispatch center", "power transmission lines"])
        realism = "use real-material style references" if needs_real_material else "high realism"
        shot_label = shot_type.value.replace("_", " ")
        return (
            f"{aspect_ratio} short-video shot, {shot_label}, {realism}, "
            f"Chinese power-grid context, clean corporate visual style, "
            f"keywords: {keywords}, stable camera, suitable for subtitle overlay, "
            "no visible text, no captions, no logo, no watermark, no readable screen UI."
        )
