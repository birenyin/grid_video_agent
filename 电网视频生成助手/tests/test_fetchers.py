from __future__ import annotations

import unittest
from pathlib import Path

from src.grid_video_agent.fetchers import extract_candidate_links, parse_article_html
from src.grid_video_agent.models import VideoPlan, VideoSegment
from src.grid_video_agent.sources import WebSource
from src.grid_video_agent.video_renderer import render_preview_bundle
from tests.helpers import workspace_tempdir


class FetcherParsingTests(unittest.TestCase):
    def test_extract_candidate_links_prefers_article_links(self) -> None:
        html = """
        <html><body>
          <a href="/about">公司概况</a>
          <a href="/xwzx/2026/202603/t20260318_100001.html">南方电网推进新能源并网与电网保供</a>
          <a href="https://mp.weixin.qq.com/s/test">公众号跳转</a>
        </body></html>
        """
        source = WebSource(
            name="南方电网",
            list_url="https://www.csg.cn/",
            publisher="中国南方电网",
            source_type="official",
            reliability_score=93,
            allowed_domains=("csg.cn",),
            article_url_keywords=("/xwzx/",),
            include_keywords=("电网", "新能源", "保供"),
            exclude_keywords=("公司概况",),
        )
        links = extract_candidate_links(html, source.list_url, source)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].url, "https://www.csg.cn/xwzx/2026/202603/t20260318_100001.html")

    def test_parse_article_html_extracts_item(self) -> None:
        html = """
        <html>
          <head><title>国家能源局发布电力市场规则解读</title></head>
          <body>
            <h1>国家能源局发布电力市场规则解读</h1>
            <div>发布时间：2026-03-21 09:30</div>
            <p>为进一步做好电力市场建设工作，文件围绕现货交易和新能源消纳做出安排。</p>
            <p>业内普遍关注规则调整对调度衔接和市场出清的影响。</p>
          </body>
        </html>
        """
        source = WebSource(
            name="国家能源局",
            list_url="https://www.nea.gov.cn/",
            publisher="国家能源局",
            source_type="institution",
            reliability_score=95,
            allowed_domains=("nea.gov.cn",),
            article_url_keywords=("/20", "/c.html"),
            include_keywords=("电力", "电网", "市场"),
            exclude_keywords=(),
        )
        item = parse_article_html(html, "https://www.nea.gov.cn/20260321/example/c.html", source)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.source, "国家能源局")
        self.assertEqual(item.content_category, "policy")
        self.assertIn("电力市场", item.tags)
        self.assertEqual(item.published_at, "2026-03-21 09:30:00")


class PreviewRenderTests(unittest.TestCase):
    def test_render_preview_bundle_creates_assets(self) -> None:
        plan = VideoPlan(
            title="电网负荷再冲高，这对调度意味着什么？",
            cover_text="负荷新高\n调度怎么扛？",
            intro_hook="先说结论，这会影响调度判断。",
            takeaway="真正要看的是负荷变化、保供压力和市场信号。",
            hashtags=["#电网", "#调度"],
            selected_news=[],
            segments=[
                VideoSegment(scene=1, visual="调度大屏", narration="先说结论。", subtitle="先说结论。"),
                VideoSegment(scene=2, visual="新闻截图", narration="第二段说明。", subtitle="第二段说明。"),
            ],
        )
        with workspace_tempdir() as output_dir:
            render_preview_bundle(plan, output_dir)
            self.assertTrue((output_dir / "cover.png").exists())
            self.assertTrue((output_dir / "preview.gif").exists())
            self.assertTrue((output_dir / "preview_frames" / "scene_01.png").exists())


if __name__ == "__main__":
    unittest.main()
