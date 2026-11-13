> 本文件为 social_en 通道契约文档（原 sn-search-social-en skill，2026-11-13 收编进 deep-research）。

# sn-search-social-en - 英文社交平台搜索

搜索 Reddit、Twitter/X、YouTube 三个英文社交平台。

## 依赖

运行脚本前先安装本通道的 Python 依赖（技能根目录下 `deep-research/scripts/channels/social_en/requirements.txt`）：

```bash
python -m pip install -r deep-research/scripts/channels/social_en/requirements.txt
```

如果项目使用 `uv` 环境：

```bash
uv pip install -r deep-research/scripts/channels/social_en/requirements.txt
```

## 可用脚本

| 脚本 | 平台 | 用途 | API key |
|------|------|------|---------|
| `reddit_search.py` | Reddit | 帖子和讨论搜索 | 无需 |
| `twitter_search.py` | Twitter/X | 推文搜索 | 需 `TIKHUB_TOKEN` |
| `youtube_search.py` | YouTube | 视频搜索 | 需 `YOUTUBE_API_KEY` |

## 参数说明

### reddit_search.py

```bash
python scripts/reddit_search.py <query> [选项]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `query` | 搜索关键词（必填） | — |
| `--limit`, `-n` | 返回结果数量 | 10 |
| `--subreddit`, `-r` | 限定子版块（如 `python`, `machinelearning`） | — |
| `--sort` | 排序方式：`relevance`, `hot`, `top`, `new`, `comments` | relevance |
| `--time`, `-t` | 时间范围：`hour`, `day`, `week`, `month`, `year`, `all` | all |

```bash
python scripts/reddit_search.py "machine learning projects" --limit 5
python scripts/reddit_search.py "async python" --subreddit python --sort top --time month --limit 5
```

### twitter_search.py

```bash
python scripts/twitter_search.py <query> [选项]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `query` | 搜索关键词（必填） | — |
| `--limit`, `-n` | 返回结果数量 | 10 |
| `--token` | TikHub Token（也可通过 `TIKHUB_TOKEN` 环境变量设置，必填） | — |

```bash
python scripts/twitter_search.py "AI agents" --limit 10
python scripts/twitter_search.py "LLM" --token your_tikhub_token --limit 5
```

### youtube_search.py

```bash
python scripts/youtube_search.py <query> [选项]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `query` | 搜索关键词（必填） | — |
| `--limit`, `-n` | 返回结果数量 | 10 |
| `--api-key` | YouTube API Key（也可通过 `YOUTUBE_API_KEY` 环境变量设置，必填） | — |
| `--order` | 排序方式：`relevance`, `date`, `viewCount`, `rating` | relevance |

```bash
python scripts/youtube_search.py "transformer explained" --limit 5
python scripts/youtube_search.py "python tutorial" --order viewCount --limit 10
```

## 输出格式

标准 JSON：`{"success": true, "query": "...", "provider": "reddit|twitter|youtube", "items": [...], "error": null}`
