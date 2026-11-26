# Contributing

感谢你愿意改进这个项目。它是一个面向内容创作者的本地工具，不是自动发号或刷量系统。

## 开发环境

- Python 3.11+
- 无第三方运行时依赖
- Windows / macOS / Linux 均可

```bash
git clone https://github.com/luongthimydieu/douyin-creator-copilot.git
cd douyin-creator-copilot
python -m unittest discover -s tests -v
python -m copilot init
```

可选安装为命令行工具：

```bash
pip install -e .
copilot --help
```

## 代码结构

```text
copilot/cli.py        命令行入口
copilot/db.py         SQLite schema 与连接
copilot/storyboard.py brief 模板、校验、分镜骨架、提示词
copilot/cost.py       生成成本估算
copilot/metadata.py   抖音/B站元数据
copilot/analytics.py  CSV 导入与周报
copilot/platforms.py  平台限制与检查清单
config/               账号与价格配置
docs/                 定位、平台策略、playbook、命名、变现
```

## 添加视频模型

1. 在 `config/pricing.json` 的 `models` 中增加模型与每秒价格。
2. 在成本档位 `profiles` 中组合模型/分辨率/占比。
3. 如果要真正调用 API，在 `copilot/` 下新增 provider 模块，读取 `.env` 中的密钥，提供 `submit()` / `poll()` / `download()`。
4. 不要在代码里硬编码密钥；`.env` 已被忽略。

## 内容与合规

- 不提交抓取他人数据的脚本，不提交自动发布/群控/刷量代码。
- 示例里的历史事实仅用于演示结构，发布前必须自行核对来源。
- AI 生成内容必须按平台要求标识；音乐、字体、图片、影视素材必须有授权。
- 不提交真实账号的 Cookie、Token、手机号、身份证等隐私数据。

## Pull Request

- 先跑 `python -m unittest discover -s tests -v`。
- 保持 CLI 行为向后兼容；新增命令要有 `--help` 说明。
- 修改 schema 时，在 `copilot/db.py` 里加迁移说明，不要破坏已有 `data/copilot.db`。
- PR 描述里写清楚：改了什么、为什么、怎么验证。
- 提交即表示同意以 MIT License 发布你的贡献。

## 行为准则

讨论聚焦技术与内容本身；不人身攻击、不发布侵权或违规内容、不引导刷量或规避平台审核。
