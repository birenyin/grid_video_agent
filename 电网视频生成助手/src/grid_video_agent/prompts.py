SYSTEM_POSITIONING = """
你是一个电网行业短视频策划助手，需要把行业资讯改写成专业、清晰、适合抖音和视频号传播的讲解脚本。
要求：
1. 先讲结论，再讲影响。
2. 语言口语化，但不能失真。
3. 不夸大，不制造恐慌，不使用未经证实的信息。
4. 优先强调对调度、保供、运维、电力市场参与者的实际影响。
5. 对政策和知识类内容，要强调“这对电网人意味着什么”。
6. 输出必须保留来源信息，方便审核追溯。
""".strip()


def build_user_prompt(items, brand_name: str, audience: str) -> str:
    lines = [
        f"账号名称：{brand_name}",
        f"目标受众：{audience}",
        "请基于以下电网资讯，生成一个 60 秒左右的短视频策划 JSON。",
        "JSON 必须包含 title、cover_text、intro_hook、takeaway、hashtags、selected_news、segments、warnings。",
        "segments 至少 4 个镜头，每个镜头包含 scene、visual、narration、subtitle。",
        "selected_news 中请保留 source、title、url、published_at、content_category。",
        "如果有来源可靠性或表述风险，请放进 warnings。",
        "",
        "资讯列表：",
    ]
    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"{index}. 标题：{item.title}",
                f"来源：{item.source}",
                f"发布时间：{item.published_at}",
                f"类别：{item.content_category}",
                f"摘要：{item.summary}",
                f"标签：{', '.join(item.tags)}",
                f"可靠性：{item.reliability_score}",
                f"链接：{item.url}",
                "",
            ]
        )
    return "\n".join(lines)
