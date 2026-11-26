# Douyin Creator Copilot（故纸余温）

[![CI](https://github.com/luongthimydieu/douyin-creator-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/luongthimydieu/douyin-creator-copilot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

> 抖音 + B 站「历史中的人性与情感」内容运营系统：从选题、brief、分镜、成本，到双平台元数据、发布清单、数据周报。
>
> 一个可复用的开源骨架，**不是自动发号、自动抓取或刷量工具**。

## 状态

v0.1.0 MVP。核心链路已跑通并有单元测试：

- 选题库 / 剧集 / 分镜管理（SQLite）
- brief 模板 + 历史事实与来源校验
- 按目标时长和节拍生成分镜骨架、视频提示词
- 生成成本估算（Seedance / 可灵 / 海螺 / Vidu，价格可配置）
- 抖音 / B站标题、封面字、话题、简介、发布检查清单
- 播放数据 CSV 导入 + 周报（中位数、完播、互动、涨粉、建议）
- 实验台账 / 打法手册
- GitHub Actions CI（Python 3.11 / 3.12 / 3.13）

**尚未包含**：真实的视频模型 API 调用、自动发布、平台数据抓取。个人主体没有官方发布 API，发布应由人工完成；数据先用创作者中心/B站后台导出 CSV。这些边界写在 [ROADMAP.md](ROADMAP.md)。

## 它是什么 / 不是什么

**是**：一个本地优先的内容运营工作台，帮你把「选题 → 脚本 → 分镜 → 成本 → 双平台发布物料 → 数据复盘」串成可重复的流程。

**不是**：自动养号、自动发布、自动爬评论、群控、刷量工具。项目明确不包含这些能力，也不接受相关 PR。

## 快速开始

```bash
git clone https://github.com/luongthimydieu/douyin-creator-copilot.git
cd douyin-creator-copilot

python -m copilot init
python -m copilot account

# 1. 建选题
python -m copilot topic add --title "敦煌壁画里的供养人" --series "人间旧档" \
  --angle "一个普通女子的一生" --source "抖音热点宝" --heat 78 --fit 92

# 2. 建剧集（自动生成 data/episodes/<slug>/brief.json）
python -m copilot episode new --title "敦煌壁画里的供养人" --series "人间旧档" --duration 180

# 3. 填 brief 后校验
python -m copilot brief show <slug>
python -m copilot brief validate <slug>

# 4. 生成分镜骨架 + 提示词
python -m copilot storyboard build <slug>

# 5. 估算成本
python -m copilot cost --episode <slug> --profile standard

# 6. 生成双平台元数据与发布清单
python -m copilot metadata <slug>
python -m copilot publish checklist <slug>

# 7. 导入数据、看周报
python -m copilot metrics import --file data/metrics.csv
python -m copilot report weekly
```

可选安装为命令行工具：

```bash
pip install -e .
copilot --help
```

要求 Python 3.11+；核心功能只使用标准库。

## 数据 CSV

```text
platform,episode_slug,published_at,captured_at,hours_since_publish,views,likes,comments,shares,favorites,followers_delta,avg_watch_sec,completion_rate,traffic_search,traffic_recommend
douyin,ep-20261126-120000,2026-11-25T19:00:00,2026-11-26T19:00:00,24,1200,45,8,3,20,12,35.5,0.22,180,900
bilibili,ep-20261126-120000,2026-11-25T20:00:00,2026-11-26T20:00:00,24,800,30,5,2,15,6,42.0,0.31,60,700
```

`platform` 取 `douyin` / `bilibili`；`episode_slug` 必须已存在于本地库。模板见 [examples/metrics.example.csv](examples/metrics.example.csv)。

## 项目结构

```text
config/           账号定位、模型价格与成本档位
docs/             定位、平台策略、内容 playbook、账号命名、变现路线
examples/         填好的 brief 示例、数据 CSV 模板
copilot/          CLI + 数据层 + 内容/分析模块
data/             运行后生成：copilot.db、episodes/、reports/（默认不入库）
tests/            核心逻辑单元测试
```

## 配置

- `config/account.json`：账号名、定位、受众、内容支柱、系列。克隆后改成你自己的账号即可。
- `config/pricing.json`：模型每秒价格、成本档位（试水/标准/精品）。价格会变，下单前以官方为准。
- `COPILOT_HOME`：可选环境变量，把数据目录指向另一个 workspace；默认使用当前项目目录。

## 路线图

见 [ROADMAP.md](ROADMAP.md)。下一步是视频模型适配器（Seedance / 可灵 / 海螺 / Vidu）、评论分析与轻量 Web 工作台。

## 参与贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。欢迎 issue / PR，但不接受自动发布、抓取他人数据、刷量、绕过风控类改动。

## 免责声明

- 本项目与抖音、B站、火山方舟、可灵、海螺、Vidu 等平台/服务无隶属关系。
- 使用本项目时请遵守各平台规则、AIGC 标识要求和著作权法；AI 生成内容必须按平台要求标识。
- 历史类内容必须自行核对史料来源；示例中的事实仅用于演示结构，不构成可发布内容。
- 本项目不提供账号登录、自动发布、数据抓取能力；因使用方式产生的账号或法律风险由使用者自行承担。

## License

[MIT](LICENSE) © 2026 WangZhiwen
