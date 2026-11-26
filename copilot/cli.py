from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from . import config
from .analytics import format_console, import_csv, weekly_report
from .cost import estimate, format_estimate
from .db import db, init_db
from .metadata import build as build_metadata
from .metadata import to_markdown as metadata_markdown
from .platforms import CHECKLISTS, PLATFORMS
from .storyboard import (
    brief_template,
    build_shots,
    fill_prompts,
    to_markdown as storyboard_markdown,
    validate_brief,
)


def _print_json(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _episode(conn, slug: str) -> dict:
    row = conn.execute("SELECT * FROM episodes WHERE slug = ?", (slug,)).fetchone()
    if not row:
        raise SystemExit(f"episode not found: {slug}")
    return dict(row)


def _brief_path(slug: str):
    return config.episode_dir(slug) / "brief.json"


def _load_brief(slug: str) -> dict:
    path = _brief_path(slug)
    if not path.exists():
        raise SystemExit(f"brief not found: {path}")
    return config.load_json(path)


def cmd_init(args) -> None:
    init_db()
    config.ensure_dirs()
    print(f"initialized: {config.DB_PATH}")


def cmd_account(args) -> None:
    _print_json(config.account())


def cmd_topic_add(args) -> None:
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO topics (title, series, angle, source, heat, fit) VALUES (?, ?, ?, ?, ?, ?)",
            (args.title, args.series or "", args.angle or "", args.source or "", args.heat, args.fit),
        )
    print(f"topic #{cur.lastrowid} added: {args.title}")


def cmd_topic_list(args) -> None:
    with db() as conn:
        rows = conn.execute("SELECT * FROM topics ORDER BY id DESC").fetchall()
    if not rows:
        print("no topics")
        return
    for row in rows:
        print(
            f"#{row['id']:<3} [{row['status']}] {row['title']} | 系列: {row['series'] or '-'} "
            f"| 热度 {row['heat']} | 契合 {row['fit']} | 来源: {row['source'] or '-'}"
        )


def cmd_episode_new(args) -> None:
    slug = args.slug or f"ep-{datetime.now():%Y%m%d-%H%M%S}"
    with db() as conn:
        if conn.execute("SELECT 1 FROM episodes WHERE slug = ?", (slug,)).fetchone():
            raise SystemExit(f"episode already exists: {slug}")
        cur = conn.execute(
            """
            INSERT INTO episodes (slug, title, series, hook, target_duration_sec, status)
            VALUES (?, ?, ?, ?, ?, 'idea')
            """,
            (slug, args.title, args.series or "", args.hook or "", args.duration),
        )
        episode = dict(conn.execute("SELECT * FROM episodes WHERE id = ?", (cur.lastrowid,)).fetchone())

    folder = config.episode_dir(slug)
    folder.mkdir(parents=True, exist_ok=True)
    brief = brief_template(episode, config.account())
    config.write_json(folder / "brief.json", brief)
    print(f"episode created: {slug}")
    print(f"brief: {folder / 'brief.json'}")


def cmd_episode_list(args) -> None:
    with db() as conn:
        rows = conn.execute("SELECT * FROM episodes ORDER BY id DESC").fetchall()
    if not rows:
        print("no episodes")
        return
    for row in rows:
        print(
            f"{row['slug']} | {row['title']} | {row['series'] or '-'} | "
            f"{row['target_duration_sec']}s | {row['status']}"
        )


def cmd_episode_show(args) -> None:
    with db() as conn:
        episode = _episode(conn, args.slug)
    brief_file = _brief_path(args.slug)
    episode["brief_exists"] = brief_file.exists()
    _print_json(episode)


def cmd_brief_show(args) -> None:
    brief = _load_brief(args.slug)
    _print_json(brief)
    issues = validate_brief(brief)
    print("\n校验:")
    if issues:
        for issue in issues:
            print(f"- {issue}")
    else:
        print("- OK")


def cmd_brief_validate(args) -> None:
    issues = validate_brief(_load_brief(args.slug))
    if not issues:
        print("OK")
        return
    for issue in issues:
        print(f"- {issue}")
    raise SystemExit(1)


def cmd_storyboard_build(args) -> None:
    with db() as conn:
        episode = _episode(conn, args.slug)
    folder = config.episode_dir(args.slug)
    brief = config.load_json(_brief_path(args.slug)) if _brief_path(args.slug).exists() else brief_template(episode, config.account())
    duration = float(args.duration or episode["target_duration_sec"] or 180)
    shots = fill_prompts(build_shots(duration, brief, args.shot_sec), brief)
    issues = validate_brief(brief)

    with db() as conn:
        conn.execute("DELETE FROM shots WHERE episode_id = ?", (episode["id"],))
        for shot in shots:
            conn.execute(
                """
                INSERT INTO shots (episode_id, seq, beat, duration_sec, description, prompt, model, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    episode["id"],
                    shot["seq"],
                    shot["beat"],
                    shot["duration_sec"],
                    shot["description"],
                    shot["prompt"],
                    shot["model"],
                    shot["status"],
                ),
            )

    config.write_json(folder / "storyboard.json", {"episode": episode, "brief": brief, "shots": shots})
    (folder / "storyboard.md").write_text(
        storyboard_markdown(episode, brief, shots, issues), encoding="utf-8"
    )
    total = sum(float(shot["duration_sec"]) for shot in shots)
    print(f"storyboard built: {len(shots)} shots, {total:.1f}s")
    print(f"file: {folder / 'storyboard.md'}")


def cmd_shots_list(args) -> None:
    with db() as conn:
        episode = _episode(conn, args.slug)
        rows = conn.execute(
            "SELECT * FROM shots WHERE episode_id = ? ORDER BY seq", (episode["id"],)
        ).fetchall()
    if not rows:
        print("no shots; run storyboard build first")
        return
    for row in rows:
        print(
            f"{row['seq']:>2} | {row['beat'] or '-':<6} | {row['duration_sec']:>4.1f}s | "
            f"{row['status']:<6} | {row['description'] or '(待填)'}"
        )


def cmd_cost(args) -> None:
    duration = args.duration
    if args.episode:
        with db() as conn:
            episode = _episode(conn, args.episode)
        duration = float(episode["target_duration_sec"] or duration or 180)
    if not duration:
        raise SystemExit("--duration or --episode is required")
    result = estimate(float(duration), args.profile, config.pricing(), args.overhead)
    print(format_estimate(result))


def cmd_metadata(args) -> None:
    with db() as conn:
        episode = _episode(conn, args.slug)
    brief = _load_brief(args.slug) if _brief_path(args.slug).exists() else {}
    metadata = build_metadata(config.account(), episode, brief)
    folder = config.episode_dir(args.slug)
    config.write_json(folder / "metadata.json", metadata)
    text = metadata_markdown(metadata, episode)
    (folder / "metadata.md").write_text(text, encoding="utf-8")
    print(text)


def cmd_publish_checklist(args) -> None:
    with db() as conn:
        episode = _episode(conn, args.slug)
    folder = config.episode_dir(args.slug)
    metadata_path = folder / "metadata.json"
    if metadata_path.exists():
        metadata = config.load_json(metadata_path)
    else:
        brief = _load_brief(args.slug) if _brief_path(args.slug).exists() else {}
        metadata = build_metadata(config.account(), episode, brief)
        config.write_json(metadata_path, metadata)

    lines = [f"# 发布检查清单：{episode['title']}", ""]
    for key in ("douyin", "bilibili"):
        item = metadata[key]
        lines.extend(
            [
                f"## {item['label']}",
                "",
                f"- 标题：{item['title']}",
                f"- 封面字：{item['cover_text']}",
                f"- 标签：{' '.join(item['tags']) if key == 'douyin' else ' / '.join(item['tags'])}",
                f"- 画幅：{item['aspect_ratio']}",
                "",
                "检查项：",
                "",
            ]
        )
        lines.extend(f"- [ ] {check}" for check in CHECKLISTS[key])
        lines.append("")

    lines.extend(
        [
            "## 数据记录",
            "",
            "- [ ] 发布后 1 小时记录播放/点赞/评论",
            "- [ ] 24 小时记录完播率、涨粉、流量来源",
            "- [ ] 7 天记录长尾数据",
            "- [ ] 把数据填入 CSV，执行 `python -m copilot metrics import --file data/metrics.csv`",
        ]
    )
    path = folder / "publish_checklist.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"checklist written: {path}")


def cmd_metrics_import(args) -> None:
    count = import_csv(args.file, args.platform)
    print(f"imported {count} rows from {args.file}")


def cmd_report_weekly(args) -> None:
    print(format_console(weekly_report(args.days)))


def cmd_experiment_add(args) -> None:
    episode_id = None
    if args.episode:
        with db() as conn:
            episode_id = _episode(conn, args.episode)["id"]
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO experiments (episode_id, hypothesis, variable, variant, metric, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (episode_id, args.hypothesis, args.variable or "", args.variant or "", args.metric or "", args.status),
        )
    print(f"experiment #{cur.lastrowid} added")


def cmd_experiment_list(args) -> None:
    with db() as conn:
        rows = conn.execute("SELECT * FROM experiments ORDER BY id DESC").fetchall()
    if not rows:
        print("no experiments")
        return
    for row in rows:
        print(f"#{row['id']} [{row['status']}] {row['hypothesis']} | {row['variable']}={row['variant']} | 指标: {row['metric']}")


def cmd_playbook_add(args) -> None:
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO playbook (category, insight, evidence, confidence) VALUES (?, ?, ?, ?)",
            (args.category or "", args.insight, args.evidence or "", args.confidence),
        )
    print(f"playbook #{cur.lastrowid} added")


def cmd_playbook_list(args) -> None:
    with db() as conn:
        rows = conn.execute("SELECT * FROM playbook ORDER BY confidence DESC, id DESC").fetchall()
    if not rows:
        print("playbook is empty")
        return
    for row in rows:
        print(f"#{row['id']} [{row['category'] or '-'}] 置信度 {row['confidence']} | {row['insight']}")
        if row["evidence"]:
            print(f"    证据: {row['evidence']}")


def cmd_status(args) -> None:
    with db() as conn:
        queries = {
            "episodes": "SELECT COUNT(*) FROM episodes",
            "topics": "SELECT COUNT(*) FROM topics",
            "shots": "SELECT COUNT(*) FROM shots",
            "posts": "SELECT COUNT(*) FROM posts",
            "snapshots": "SELECT COUNT(*) FROM metric_snapshots",
            "experiments": "SELECT COUNT(*) FROM experiments",
            "playbook": "SELECT COUNT(*) FROM playbook",
        }
        for label, sql in queries.items():
            count = conn.execute(sql).fetchone()[0]
            print(f"{label:<12}{count}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="copilot",
        description="故纸余温 · 抖音/B站历史情感内容运营系统",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="初始化数据库和目录")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("account", help="查看账号定位配置")
    p.set_defaults(func=cmd_account)

    p = sub.add_parser("status", help="查看数据概览")
    p.set_defaults(func=cmd_status)

    # topic
    topic = sub.add_parser("topic", help="选题库")
    topic_sub = topic.add_subparsers(dest="topic_command", required=True)
    p = topic_sub.add_parser("add", help="新增选题")
    p.add_argument("--title", required=True)
    p.add_argument("--series", default="")
    p.add_argument("--angle", default="")
    p.add_argument("--source", default="")
    p.add_argument("--heat", type=int, default=0)
    p.add_argument("--fit", type=int, default=0)
    p.set_defaults(func=cmd_topic_add)
    p = topic_sub.add_parser("list", help="列出选题")
    p.set_defaults(func=cmd_topic_list)

    # episode
    episode = sub.add_parser("episode", help="剧集管理")
    episode_sub = episode.add_subparsers(dest="episode_command", required=True)
    p = episode_sub.add_parser("new", help="新建剧集")
    p.add_argument("--title", required=True)
    p.add_argument("--series", default="")
    p.add_argument("--hook", default="")
    p.add_argument("--duration", type=int, default=180)
    p.add_argument("--slug", default="")
    p.set_defaults(func=cmd_episode_new)
    p = episode_sub.add_parser("list", help="列出剧集")
    p.set_defaults(func=cmd_episode_list)
    p = episode_sub.add_parser("show", help="查看剧集")
    p.add_argument("slug")
    p.set_defaults(func=cmd_episode_show)

    # brief
    brief = sub.add_parser("brief", help="制作 brief")
    brief_sub = brief.add_subparsers(dest="brief_command", required=True)
    p = brief_sub.add_parser("show", help="查看 brief 和校验结果")
    p.add_argument("slug")
    p.set_defaults(func=cmd_brief_show)
    p = brief_sub.add_parser("validate", help="校验 brief")
    p.add_argument("slug")
    p.set_defaults(func=cmd_brief_validate)

    # storyboard
    storyboard = sub.add_parser("storyboard", help="分镜")
    storyboard_sub = storyboard.add_subparsers(dest="storyboard_command", required=True)
    p = storyboard_sub.add_parser("build", help="生成分镜骨架")
    p.add_argument("slug")
    p.add_argument("--duration", type=float, default=None)
    p.add_argument("--shot-sec", type=float, default=6.0)
    p.set_defaults(func=cmd_storyboard_build)

    # shots
    shots = sub.add_parser("shots", help="分镜列表")
    shots_sub = shots.add_subparsers(dest="shots_command", required=True)
    p = shots_sub.add_parser("list", help="列出分镜")
    p.add_argument("slug")
    p.set_defaults(func=cmd_shots_list)

    # cost
    p = sub.add_parser("cost", help="生成成本估算")
    p.add_argument("--episode", default="")
    p.add_argument("--duration", type=float, default=None)
    p.add_argument("--profile", default="standard", choices=["trial", "standard", "premium"])
    p.add_argument("--overhead", type=float, default=0.05)
    p.set_defaults(func=cmd_cost)

    # metadata
    p = sub.add_parser("metadata", help="生成抖音/B站元数据")
    p.add_argument("slug")
    p.set_defaults(func=cmd_metadata)

    # publish
    publish = sub.add_parser("publish", help="发布检查")
    publish_sub = publish.add_subparsers(dest="publish_command", required=True)
    p = publish_sub.add_parser("checklist", help="生成发布检查清单")
    p.add_argument("slug")
    p.set_defaults(func=cmd_publish_checklist)

    # metrics
    metrics = sub.add_parser("metrics", help="数据导入")
    metrics_sub = metrics.add_subparsers(dest="metrics_command", required=True)
    p = metrics_sub.add_parser("import", help="导入 CSV")
    p.add_argument("--file", required=True)
    p.add_argument("--platform", default="douyin")
    p.set_defaults(func=cmd_metrics_import)

    # report
    report = sub.add_parser("report", help="周报")
    report_sub = report.add_subparsers(dest="report_command", required=True)
    p = report_sub.add_parser("weekly", help="生成周报")
    p.add_argument("--days", type=int, default=7)
    p.set_defaults(func=cmd_report_weekly)

    # experiment
    experiment = sub.add_parser("experiment", help="实验台账")
    experiment_sub = experiment.add_subparsers(dest="experiment_command", required=True)
    p = experiment_sub.add_parser("add", help="新增实验")
    p.add_argument("--hypothesis", required=True)
    p.add_argument("--variable", default="")
    p.add_argument("--variant", default="")
    p.add_argument("--metric", default="")
    p.add_argument("--episode", default="")
    p.add_argument("--status", default="running")
    p.set_defaults(func=cmd_experiment_add)
    p = experiment_sub.add_parser("list", help="列出实验")
    p.set_defaults(func=cmd_experiment_list)

    # playbook
    playbook = sub.add_parser("playbook", help="打法手册")
    playbook_sub = playbook.add_subparsers(dest="playbook_command", required=True)
    p = playbook_sub.add_parser("add", help="新增打法")
    p.add_argument("--category", default="")
    p.add_argument("--insight", required=True)
    p.add_argument("--evidence", default="")
    p.add_argument("--confidence", type=int, default=50)
    p.set_defaults(func=cmd_playbook_add)
    p = playbook_sub.add_parser("list", help="列出打法")
    p.set_defaults(func=cmd_playbook_list)

    return parser


def main(argv=None) -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if not func:
        parser.print_help()
        return
    try:
        func(args)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1)
