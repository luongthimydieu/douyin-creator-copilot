from __future__ import annotations

from .platforms import PLATFORMS


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        item = (item or "").strip()
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build(account: dict, episode: dict, brief: dict) -> dict:
    title = str(episode.get("title", "")).strip()
    hook = str(episode.get("hook") or brief.get("hook") or "").strip()
    series = str(episode.get("series") or brief.get("series") or account.get("name", "")).strip()
    summary = str(brief.get("summary") or brief.get("thesis") or "").strip()
    sources = [str(source).strip() for source in brief.get("sources", []) if str(source).strip()]
    base_tags = [str(tag).strip() for tag in brief.get("tags", []) if str(tag).strip()]
    cover = str(brief.get("cover_text") or title).strip()

    aigc = "本视频画面由 AI 生成，已按平台要求标识；史料与引用见简介。"
    fact_note = "参考资料：" + "；".join(sources) if sources else ""
    description = "\n".join(part for part in (summary, aigc, fact_note) if part)

    douyin_cfg = PLATFORMS["douyin"]
    bilibili_cfg = PLATFORMS["bilibili"]

    douyin_title = _clip(f"{hook}｜{title}" if hook else title, douyin_cfg["max_title"])
    bili_title = _clip(
        f"【{series}】{title}｜{hook}" if hook else f"【{series}】{title}",
        bilibili_cfg["max_title"],
    )

    douyin_tags = _unique(
        [f"#{tag}" for tag in base_tags + ["历史", "历史故事", "人文", "AI创作浪潮计划"]]
    )[: douyin_cfg["max_tags"]]
    bili_tags = _unique(base_tags + ["历史", "人文", "历史故事", "AI生成", "故事"])[: bilibili_cfg["max_tags"]]

    return {
        "douyin": {
            "platform": "douyin",
            "label": douyin_cfg["label"],
            "title": douyin_title,
            "cover_text": _clip(cover, 12),
            "tags": douyin_tags,
            "description": description,
            "aspect_ratio": douyin_cfg["aspect"],
            "partition": "",
        },
        "bilibili": {
            "platform": "bilibili",
            "label": bilibili_cfg["label"],
            "title": bili_title,
            "cover_text": _clip(cover, 16),
            "tags": bili_tags,
            "description": description,
            "aspect_ratio": bilibili_cfg["aspect"],
            "partition": bilibili_cfg["partition"],
        },
    }


def to_markdown(metadata: dict, episode: dict) -> str:
    lines = [f"# 发布元数据：{episode.get('title', '')}", ""]
    for key in ("douyin", "bilibili"):
        item = metadata[key]
        lines.extend(
            [
                f"## {item['label']}",
                "",
                f"- 标题：{item['title']}",
                f"- 封面字：{item['cover_text']}",
                f"- 标签：{' '.join(item['tags']) if item['platform'] == 'douyin' else ' / '.join(item['tags'])}",
                f"- 画幅：{item['aspect_ratio']}",
                f"- 分区：{item['partition'] or '无'}",
                "",
                "简介：",
                "",
                item["description"],
                "",
            ]
        )
    return "\n".join(lines)
