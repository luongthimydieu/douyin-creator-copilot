# 示例文件

> 示例中的历史事实仅用于演示数据结构，发布前必须自行核对史料来源。

- `brief.example.json`：一个填好的单集 brief（敦煌供养人）。先用
  `python -m copilot episode new --slug ep-demo --title "敦煌壁画里的供养人" --series "人间旧档"`，
  再把内容复制到 `data/episodes/ep-demo/brief.json`。
- `metrics.example.csv`：播放数据导入模板。把 `episode_slug` 改成你的真实剧集 slug，
  `platform` 填 `douyin` 或 `bilibili`，其余按创作者中心/B站后台的数据填写。
