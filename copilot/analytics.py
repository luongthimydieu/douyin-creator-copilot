from __future__ import annotations

import csv
from datetime import datetime, timedelta
from statistics import median
from typing import Any

from .config import REPORTS_DIR
from .db import db

CSV_FIELDS = [
    "views",
    "likes",
    "comments",
    "shares",
    "favorites",
    "followers_delta",
    "avg_watch_sec",
    "completion_rate",
    "traffic_search",
    "traffic_recommend",
]

FLOAT_FIELDS = {"avg_watch_sec", "completion_rate"}


def _opt_int(value: Any) -> int | None:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return None
    return int(float(text))


def _opt_float(value: Any) -> float | None:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return None
    return float(text)


def import_csv(path: str, default_platform: str = "douyin") -> int:
    count = 0
    with open(path, "r", newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        with db() as conn:
            for line_no, row in enumerate(reader, start=2):
                slug = str(row.get("episode_slug") or "").strip()
                if not slug:
                    raise ValueError(f"line {line_no}: episode_slug is required")
                episode = conn.execute("SELECT * FROM episodes WHERE slug = ?", (slug,)).fetchone()
                if not episode:
                    raise ValueError(f"line {line_no}: unknown episode slug: {slug}")

                platform = str(row.get("platform") or default_platform).strip()
                post = conn.execute(
                    "SELECT id FROM posts WHERE episode_id = ? AND platform = ?",
                    (episode["id"], platform),
                ).fetchone()
                if post:
                    post_id = post["id"]
                else:
                    cur = conn.execute(
                        "INSERT INTO posts (episode_id, platform, title, published_at) VALUES (?, ?, ?, ?)",
                        (episode["id"], platform, episode["title"], row.get("published_at") or None),
                    )
                    post_id = cur.lastrowid

                captured_at = str(row.get("captured_at") or "").strip() or datetime.now().isoformat(
                    timespec="seconds"
                )
                values = [
                    _opt_float(row.get(field)) if field in FLOAT_FIELDS else _opt_int(row.get(field))
                    for field in CSV_FIELDS
                ]
                conn.execute(
                    """
                    INSERT INTO metric_snapshots (
                        post_id, captured_at, hours_since_publish, views, likes, comments,
                        shares, favorites, followers_delta, avg_watch_sec, completion_rate,
                        traffic_search, traffic_recommend
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        post_id,
                        captured_at,
                        _opt_float(row.get("hours_since_publish")),
                        *values,
                    ],
                )
                count += 1
    return count


def weekly_report(days: int = 7) -> dict:
    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    with db() as conn:
        rows = conn.execute(
            """
            SELECT p.platform, e.slug, e.title, s.*
            FROM metric_snapshots s
            JOIN posts p ON p.id = s.post_id
            JOIN episodes e ON e.id = p.episode_id
            WHERE s.captured_at >= ?
            ORDER BY s.captured_at ASC
            """,
            (cutoff,),
        ).fetchall()

    latest: dict[tuple[str, str], dict] = {}
    for row in rows:
        item = dict(row)
        key = (item["platform"], item["slug"])
        if key not in latest or item["captured_at"] > latest[key]["captured_at"]:
            latest[key] = item

    items = list(latest.values())
    report: dict[str, Any] = {
        "days": days,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "items": items,
        "platforms": {},
        "recommendations": [],
    }

    if not items:
        report["recommendations"] = ["最近没有数据：先用 metrics import 导入创作者中心的数据。"]
        report["path"] = None
        return report

    for platform in sorted({item["platform"] for item in items}):
        subset = [item for item in items if item["platform"] == platform]
        views = [item["views"] or 0 for item in subset]
        completions = [item["completion_rate"] for item in subset if item["completion_rate"] is not None]
        engagements = []
        for item in subset:
            total_views = item["views"] or 0
            interactions = sum(
                item.get(field) or 0 for field in ("likes", "comments", "shares", "favorites")
            )
            if total_views:
                engagements.append(interactions / total_views)
        report["platforms"][platform] = {
            "posts": len(subset),
            "median_views": median(views) if views else 0,
            "median_completion": median(completions) if completions else None,
            "median_engagement": median(engagements) if engagements else None,
            "followers_delta": sum(item.get("followers_delta") or 0 for item in subset),
            "top": sorted(subset, key=lambda item: item["views"] or 0, reverse=True)[:3],
        }

    all_views = [item["views"] or 0 for item in items]
    median_views = median(all_views) if all_views else 0
    top = max(items, key=lambda item: item["views"] or 0)
    top_views = top["views"] or 0

    if median_views and top_views >= median_views * 3:
        report["recommendations"].append(
            f"出现异常爆款（{top['title']}）：拆解它的题材、钩子、前 3 秒和结构，下一期复制。"
        )

    completions = [item["completion_rate"] for item in items if item["completion_rate"] is not None]
    if completions and median(completions) < 0.25:
        report["recommendations"].append("完播率中位数偏低：优先改前 3 秒钩子、缩短短镜、提高信息密度。")

    engagements = []
    for item in items:
        if item["views"]:
            interactions = sum(
                item.get(field) or 0 for field in ("likes", "comments", "shares", "favorites")
            )
            engagements.append(interactions / item["views"])
    if engagements and median(engagements) < 0.02:
        report["recommendations"].append("互动率偏低：结尾加一个开放问题，或在评论区置顶一个争议点。")

    followers = sum(item.get("followers_delta") or 0 for item in items)
    if followers <= 0:
        report["recommendations"].append("转粉偏弱：强化人设露出、系列感和“关注看下一集”的理由。")

    search_share = _traffic_share(items, "traffic_search")
    if search_share is not None and search_share >= 0.2:
        report["recommendations"].append(
            "搜索流量占比高：标题和简介继续埋关键词，把系列做成合集/播放列表。"
        )

    if not report["recommendations"]:
        report["recommendations"].append("数据样本还小：保持周更，至少积累 8-12 条再判断方向。")

    report["path"] = str(_write_markdown(report))
    return report


def _traffic_share(items: list[dict], field: str) -> float | None:
    total = sum((item.get("traffic_search") or 0) + (item.get("traffic_recommend") or 0) for item in items)
    if not total:
        return None
    return sum(item.get(field) or 0 for item in items) / total


def _write_markdown(report: dict):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"weekly-{datetime.now():%Y%m%d}.md"
    lines = [
        f"# 周报 {datetime.now():%Y-%m-%d}",
        "",
        f"统计窗口：最近 {report['days']} 天；样本 {len(report['items'])} 条。",
        "",
        "## 平台概览",
        "",
        "| 平台 | 条数 | 播放中位数 | 完播中位数 | 互动率中位数 | 涨粉 |",
        "|---|---|---|---|---|---|",
    ]
    for platform, stats in report["platforms"].items():
        completion = f"{stats['median_completion'] * 100:.1f}%" if stats["median_completion"] is not None else "-"
        engagement = f"{stats['median_engagement'] * 100:.1f}%" if stats["median_engagement"] is not None else "-"
        lines.append(
            f"| {platform} | {stats['posts']} | {stats['median_views']:.0f} | "
            f"{completion} | {engagement} | {stats['followers_delta']} |"
        )

    lines.extend(["", "## 本期数据", "", "| 平台 | 剧集 | 播放 | 点赞 | 评论 | 完播 |", "|---|---|---|---|---|---|"])
    for item in sorted(report["items"], key=lambda row: row["views"] or 0, reverse=True):
        completion = f"{item['completion_rate'] * 100:.0f}%" if item["completion_rate"] is not None else "-"
        lines.append(
            f"| {item['platform']} | {item['title']} | {item['views'] or 0} | "
            f"{item['likes'] or 0} | {item['comments'] or 0} | {completion} |"
        )

    lines.extend(["", "## 建议", ""])
    lines.extend(f"- {item}" for item in report["recommendations"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def format_console(report: dict) -> str:
    lines = [f"最近 {report['days']} 天，样本 {len(report['items'])} 条"]
    for platform, stats in report["platforms"].items():
        completion = f"{stats['median_completion'] * 100:.1f}%" if stats["median_completion"] is not None else "-"
        engagement = f"{stats['median_engagement'] * 100:.1f}%" if stats["median_engagement"] is not None else "-"
        lines.append(
            f"- {platform}: {stats['posts']} 条 | 播放中位数 {stats['median_views']:.0f} | "
            f"完播 {completion} | 互动 {engagement} | 涨粉 {stats['followers_delta']}"
        )
    lines.append("")
    lines.extend(f"- {item}" for item in report["recommendations"])
    if report.get("path"):
        lines.append("")
        lines.append(f"报告已写入: {report['path']}")
    return "\n".join(lines)
