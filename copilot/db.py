from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import DB_PATH, ensure_dirs

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    series TEXT,
    angle TEXT,
    source TEXT,
    heat INTEGER NOT NULL DEFAULT 0,
    fit INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'backlog',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    series TEXT,
    topic_id INTEGER,
    hook TEXT,
    thesis TEXT,
    status TEXT NOT NULL DEFAULT 'idea',
    target_duration_sec INTEGER NOT NULL DEFAULT 180,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);

CREATE TABLE IF NOT EXISTS shots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL,
    seq INTEGER NOT NULL,
    beat TEXT,
    duration_sec REAL NOT NULL DEFAULT 6,
    description TEXT,
    prompt TEXT,
    model TEXT,
    status TEXT NOT NULL DEFAULT 'todo',
    asset_path TEXT,
    UNIQUE (episode_id, seq),
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL,
    platform TEXT NOT NULL,
    url TEXT,
    title TEXT,
    published_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (episode_id, platform),
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metric_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    captured_at TEXT NOT NULL,
    hours_since_publish REAL,
    views INTEGER,
    likes INTEGER,
    comments INTEGER,
    shares INTEGER,
    favorites INTEGER,
    followers_delta INTEGER,
    avg_watch_sec REAL,
    completion_rate REAL,
    traffic_search INTEGER,
    traffic_recommend INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    platform TEXT,
    author TEXT,
    text TEXT,
    likes INTEGER DEFAULT 0,
    created_at TEXT,
    sentiment TEXT,
    topic TEXT,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER,
    hypothesis TEXT NOT NULL,
    variable TEXT,
    variant TEXT,
    metric TEXT,
    result TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS playbook (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    insight TEXT NOT NULL,
    evidence TEXT,
    confidence INTEGER NOT NULL DEFAULT 50,
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_shots_episode ON shots(episode_id, seq);
CREATE INDEX IF NOT EXISTS idx_posts_episode ON posts(episode_id, platform);
CREATE INDEX IF NOT EXISTS idx_metrics_post_time ON metric_snapshots(post_id, captured_at);
"""


def connect() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
