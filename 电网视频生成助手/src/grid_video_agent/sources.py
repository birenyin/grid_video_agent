from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebSource:
    name: str
    list_url: str
    publisher: str
    source_type: str
    reliability_score: int
    allowed_domains: tuple[str, ...]
    article_url_keywords: tuple[str, ...]
    include_keywords: tuple[str, ...]
    exclude_keywords: tuple[str, ...]
    default_category: str = "news"
    max_links: int = 6


DEFAULT_GRID_KEYWORDS = (
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
    "充电",
    "新型电力系统",
)

DEFAULT_EXCLUDE_KEYWORDS = (
    "登录",
    "注册",
    "招聘",
    "营业厅",
    "招标",
    "采购",
    "English",
    "邮箱",
    "邮箱登录",
    "专题专栏",
)


SOURCE_SETS = {
    "official": [
        WebSource(
            name="国家能源局",
            list_url="https://www.nea.gov.cn/",
            publisher="国家能源局",
            source_type="institution",
            reliability_score=95,
            allowed_domains=("nea.gov.cn",),
            article_url_keywords=("/20", "/c.html"),
            include_keywords=DEFAULT_GRID_KEYWORDS,
            exclude_keywords=DEFAULT_EXCLUDE_KEYWORDS,
        ),
        WebSource(
            name="南方电网",
            list_url="https://www.csg.cn/",
            publisher="中国南方电网",
            source_type="official",
            reliability_score=93,
            allowed_domains=("csg.cn",),
            article_url_keywords=("/xwzx/",),
            include_keywords=DEFAULT_GRID_KEYWORDS,
            exclude_keywords=DEFAULT_EXCLUDE_KEYWORDS + ("供应链", "党建专题", "新春走基层", "影像南网", "人物故事"),
        ),
        WebSource(
            name="国家电网华北分部",
            list_url="https://www.nc.sgcc.com.cn/",
            publisher="国家电网华北分部",
            source_type="official",
            reliability_score=92,
            allowed_domains=("nc.sgcc.com.cn", "sgcc.com.cn"),
            article_url_keywords=("/zxzx/gsxw/", "/2026/", "/2025/"),
            include_keywords=DEFAULT_GRID_KEYWORDS,
            exclude_keywords=DEFAULT_EXCLUDE_KEYWORDS,
        ),
    ],
    "mixed": [
        WebSource(
            name="国家能源局",
            list_url="https://www.nea.gov.cn/",
            publisher="国家能源局",
            source_type="institution",
            reliability_score=95,
            allowed_domains=("nea.gov.cn",),
            article_url_keywords=("/20", "/c.html"),
            include_keywords=DEFAULT_GRID_KEYWORDS,
            exclude_keywords=DEFAULT_EXCLUDE_KEYWORDS,
        ),
        WebSource(
            name="南方电网",
            list_url="https://www.csg.cn/",
            publisher="中国南方电网",
            source_type="official",
            reliability_score=93,
            allowed_domains=("csg.cn",),
            article_url_keywords=("/xwzx/",),
            include_keywords=DEFAULT_GRID_KEYWORDS,
            exclude_keywords=DEFAULT_EXCLUDE_KEYWORDS + ("供应链", "党建专题", "新春走基层", "影像南网", "人物故事"),
        ),
        WebSource(
            name="国家电网华北分部",
            list_url="https://www.nc.sgcc.com.cn/",
            publisher="国家电网华北分部",
            source_type="official",
            reliability_score=92,
            allowed_domains=("nc.sgcc.com.cn", "sgcc.com.cn"),
            article_url_keywords=("/zxzx/gsxw/", "/2026/", "/2025/"),
            include_keywords=DEFAULT_GRID_KEYWORDS,
            exclude_keywords=DEFAULT_EXCLUDE_KEYWORDS,
        ),
        WebSource(
            name="中国能源新闻网",
            list_url="https://www.cpnn.com.cn/",
            publisher="中国能源新闻网",
            source_type="media",
            reliability_score=82,
            allowed_domains=("cpnn.com.cn",),
            article_url_keywords=("/qiye/dianwangPD2023/", "/news/", "/dl/", "/zggl/"),
            include_keywords=DEFAULT_GRID_KEYWORDS,
            exclude_keywords=DEFAULT_EXCLUDE_KEYWORDS + ("广告", "投稿"),
        ),
    ],
}


def get_sources(source_set: str) -> list[WebSource]:
    return list(SOURCE_SETS.get(source_set, SOURCE_SETS["mixed"]))
