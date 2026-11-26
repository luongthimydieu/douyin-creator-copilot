from __future__ import annotations

from typing import Any


def brief_template(episode: dict, account: dict) -> dict:
    return {
        "title": episode.get("title", ""),
        "series": episode.get("series") or (account.get("series") or ["人间旧档"])[0],
        "hook": episode.get("hook") or "",
        "thesis": "",
        "audience": account.get("audience", ""),
        "emotional_arc": {"start": "", "turn": "", "end": ""},
        "key_facts": [
            {"fact": "", "source": ""},
            {"fact": "", "source": ""},
            {"fact": "", "source": ""},
        ],
        "beats": [
            {"name": "钩子", "ratio": 0.06, "goal": "3 秒内制造悬念/反常识"},
            {"name": "建场", "ratio": 0.12, "goal": "交代时间、地点、人物与问题"},
            {"name": "第一幕", "ratio": 0.24, "goal": "建立处境与冲突"},
            {"name": "第二幕", "ratio": 0.30, "goal": "转折与代价"},
            {"name": "第三幕", "ratio": 0.18, "goal": "选择与结果"},
            {"name": "收束", "ratio": 0.10, "goal": "情感升华 + 开放问题"},
        ],
        "scenes": [{"name": "", "visual": "", "character": ""}],
        "style": "电影感历史复原，克制、温暖、颗粒感，避免过度饱和",
        "aspect_ratio": "9:16",
        "tags": [],
        "cover_text": "",
        "summary": "",
        "sources": [],
    }


def validate_brief(brief: dict) -> list[str]:
    issues: list[str] = []

    if not str(brief.get("hook", "")).strip():
        issues.append("hook 为空：前 3 秒没有钩子")
    if not str(brief.get("thesis", "")).strip():
        issues.append("thesis 为空：这一期到底想说什么")
    if not str(brief.get("summary", "")).strip():
        issues.append("WARN: summary 为空：简介/元数据会缺少内容摘要")

    facts = [f for f in brief.get("key_facts", []) if str(f.get("fact", "")).strip()]
    if len(facts) < 3:
        issues.append(f"key_facts 只有 {len(facts)} 条：历史类建议至少 3 条有来源的事实")

    missing_sources = [
        str(i + 1)
        for i, fact in enumerate(brief.get("key_facts", []))
        if str(fact.get("fact", "")).strip() and not str(fact.get("source", "")).strip()
    ]
    if missing_sources:
        issues.append(f"key_facts 第 {', '.join(missing_sources)} 条缺少来源")

    beats = brief.get("beats", [])
    if beats:
        ratios = sum(float(beat.get("ratio", 0) or 0) for beat in beats)
        if abs(ratios - 1.0) > 0.02:
            issues.append(f"beats ratio 合计 {ratios:.2f}，应为 1.0")

    if not brief.get("scenes"):
        issues.append("WARN: scenes 为空：分镜会缺少场景/角色设定")

    return issues


def build_shots(duration_sec: float, brief: dict, shot_sec: float = 6.0) -> list[dict]:
    if duration_sec <= 0:
        raise ValueError("duration_sec must be > 0")
    if shot_sec <= 0:
        raise ValueError("shot_sec must be > 0")

    if brief.get("shots"):
        shots = []
        for index, shot in enumerate(brief["shots"], start=1):
            shots.append(
                {
                    "seq": index,
                    "beat": shot.get("beat", ""),
                    "duration_sec": round(float(shot.get("duration_sec", shot_sec)), 1),
                    "goal": shot.get("goal", ""),
                    "description": shot.get("description", ""),
                    "prompt": shot.get("prompt", ""),
                    "model": shot.get("model", ""),
                    "status": shot.get("status", "todo"),
                }
            )
        return shots

    beats = brief.get("beats") or [{"name": "全片", "ratio": 1.0, "goal": ""}]
    shots: list[dict] = []
    seq = 1

    for beat in beats:
        if beat.get("seconds"):
            beat_sec = float(beat["seconds"])
        else:
            beat_sec = duration_sec * float(beat.get("ratio", 0) or 0)
        if beat_sec <= 0:
            continue

        count = max(1, round(beat_sec / shot_sec))
        per_shot = round(beat_sec / count, 1)
        for _ in range(count):
            shots.append(
                {
                    "seq": seq,
                    "beat": beat.get("name", ""),
                    "duration_sec": per_shot,
                    "goal": beat.get("goal", ""),
                    "description": "",
                    "prompt": "",
                    "model": "",
                    "status": "todo",
                }
            )
            seq += 1

    return shots


def prompt_for(
    description: str,
    style: str,
    camera: str = "",
    character: str = "",
    duration: float = 6.0,
    aspect: str = "9:16",
) -> str:
    parts = [style.strip(), description.strip()]
    if character.strip():
        parts.append(f"consistent character: {character.strip()}")
    if camera.strip():
        parts.append(f"camera: {camera.strip()}")
    parts.append(f"{duration:g}s, {aspect}, cinematic lighting, natural motion, no text, no watermark")
    return ", ".join(part for part in parts if part)


def fill_prompts(shots: list[dict], brief: dict) -> list[dict]:
    style = str(brief.get("style", "")).strip()
    aspect = str(brief.get("aspect_ratio", "9:16")).strip()
    for shot in shots:
        if shot.get("description") and not shot.get("prompt"):
            shot["prompt"] = prompt_for(
                shot["description"],
                style,
                duration=float(shot.get("duration_sec", 6)),
                aspect=aspect,
            )
    return shots


def to_markdown(episode: dict, brief: dict, shots: list[dict], issues: list[str] | None = None) -> str:
    lines = [
        f"# {episode.get('title', '')}",
        "",
        f"- 系列：{episode.get('series') or brief.get('series') or ''}",
        f"- 时长：{episode.get('target_duration_sec', '')}s",
        f"- 钩子：{brief.get('hook', '')}",
        f"- 主题：{brief.get('thesis', '')}",
        f"- 风格：{brief.get('style', '')}",
        "",
        "## 分镜",
        "",
        "| # | 节拍 | 时长 | 目标 | 画面描述 | 提示词 | 状态 |",
        "|---|---|---|---|---|---|---|",
    ]
    for shot in shots:
        desc = str(shot.get("description", "")).replace("|", "\\|")
        prompt = str(shot.get("prompt", "")).replace("|", "\\|")
        lines.append(
            f"| {shot.get('seq')} | {shot.get('beat', '')} | {shot.get('duration_sec')}s | "
            f"{shot.get('goal', '')} | {desc} | {prompt} | {shot.get('status', 'todo')} |"
        )

    if issues:
        lines.extend(["", "## 校验", ""])
        lines.extend(f"- {issue}" for issue in issues)

    lines.extend(
        [
            "",
            "## 制作提醒",
            "",
            "- 每个镜头 5-8 秒，按节拍填“画面描述”，提示词可自动生成。",
            "- 历史事实必须回到 key_facts 和来源；不确定的宁可删掉。",
            "- 先 720p 草稿，选中的关键镜头再出 1080p。",
        ]
    )
    return "\n".join(lines) + "\n"
