from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.grid_video_agent.config import AgentConfig
from src.grid_video_agent.ingest import dedupe_items, infer_compliance_flags, load_news_items, split_safe_and_risky
from src.grid_video_agent.pipeline import run_pipeline
from tests.helpers import workspace_tempdir


class PipelineTests(unittest.TestCase):
    def test_rpa_feed_is_normalized(self) -> None:
        items = load_news_items(Path("data/input/rpa_raw_feed.json"))
        self.assertEqual(len(items), 4)
        self.assertEqual(items[0].source, "国家电网官网")
        self.assertIn("调度", items[0].tags)

    def test_dedupe_and_risk_split(self) -> None:
        items = load_news_items(Path("data/input/rpa_raw_feed.json"))
        unique_items, duplicate_count = dedupe_items(items)
        safe_items, risky_items = split_safe_and_risky(unique_items)
        self.assertEqual(duplicate_count, 1)
        self.assertEqual(len(risky_items), 1)
        self.assertGreaterEqual(len(safe_items), 2)

    def test_compliance_flags_avoid_false_positive_in_common_phrase(self) -> None:
        flags = infer_compliance_flags(
            "新能源通信专线投运",
            "根据传统通信方式的不足，本次采用电力专线改造。",
            "项目验证了跨省调控可行性。",
        )
        self.assertNotIn("据传", flags)

    def test_pipeline_writes_outputs(self) -> None:
        with workspace_tempdir() as output_dir:
            plan, report = run_pipeline(
                Path("data/input/rpa_raw_feed.json"),
                output_dir,
                AgentConfig(model_mode="rule"),
            )
            self.assertTrue((output_dir / "video_plan.json").exists())
            self.assertTrue((output_dir / "video_script.md").exists())
            self.assertTrue((output_dir / "subtitles.srt").exists())
            self.assertTrue((output_dir / "selected_sources.md").exists())
            self.assertTrue((output_dir / "run_report.json").exists())
            self.assertGreaterEqual(report.total_items, 4)
            self.assertTrue(plan.selected_news)
            report_data = json.loads((output_dir / "run_report.json").read_text(encoding="utf-8"))
            self.assertIn("duplicate_items", report_data)


if __name__ == "__main__":
    unittest.main()
