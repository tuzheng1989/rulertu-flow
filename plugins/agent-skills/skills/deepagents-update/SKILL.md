---
name: deepagents-update
description: 更新 DeepAgents 技能文档和 Python 包到最新版本。当用户说"更新 deepagents"、"update deepagents"、"检查 deepagents 更新"、"同步 deepagents 文档"时触发。也适用于用户想确认技能文档是否与官方最新一致的场景。
---

# DeepAgents Update — 技能与包同步工具

将本地的 DeepAgents 技能文档（`../deepagents/`，即本插件内与本技能平级的 deepagents 技能目录）和 Python 包同步到 LangChain 官方最新版本。

## 为什么需要这个技能

LangChain DeepAgents 文档更新频繁（每隔几周就有新页面、新组件），手动追踪差异既耗时又容易遗漏。本技能通过对比官方文档索引与本地文件，自动发现差距并补全，确保技能始终覆盖最新的 API 和能力。

## 工作流程

按顺序执行以下步骤。每步完成后向用户报告进度。

### 步骤 1：升级 Python 包

运行脚本自动记录版本变化并升级：

```bash
python SKILL_PATH/scripts/upgrade_packages.py --output /tmp/version_report.json
```

脚本会记录每个包的升级前后版本号，输出 JSON。向用户报告版本变化。

### 步骤 2：获取官方文档索引

运行脚本自动提取 DeepAgents 相关 URL：

```bash
python SKILL_PATH/scripts/extract_deepagents_urls.py --output /tmp/deepagents_urls.json
```

脚本会下载 `llms.txt` 并过滤出所有 `deepagents/` 前缀的 URL，输出 JSON 数组到指定文件。

**fallback**：如果脚本因网络问题失败（会打印提示），改用 webReader MCP 获取 `https://docs.langchain.com/llms.txt`，然后手动过滤 `deepagents/` 前缀的 URL。

### 步骤 3：对比差异

运行脚本对比官方页面与本地文件：

```bash
python SKILL_PATH/scripts/compare_docs.py \
  --urls /tmp/deepagents_urls.json \
  --refs SKILL_PATH/references/ \
  --output /tmp/doc_diff.json
```

脚本自动完成 URL→文件名映射和三向对比，输出 JSON 包含 `new_pages`、`existing_pages`、`removed_pages` 三份清单。

其中 `SKILL_PATH` 默认为 `../deepagents/`（相对本技能目录）。

### 步骤 4：检查核心页面结构变化

获取官方 harness 页面：

```
https://docs.langchain.com/oss/python/deepagents/harness
```

对比本地 `references/harness.md`，检查是否有：

- 新的组件分类（如从 3 类变为 4 类）
- 新的子组件（如 Prompt Caching）
- 章节重组或重命名

如果发现结构变化，按官方最新组织方式重写 `references/harness.md`。保留所有已有的交叉引用（`[[xxx.md]]` 格式）。

### 步骤 5：采集新增/变更页面

对每个新增或变更的页面：

1. 使用 webReader 获取页面内容
2. 从 JSON 响应中提取 `content` 字段
3. 清理内容：移除 metadata、stylesheet、external、favicon 等非文档数据
4. 添加头部信息：
   ```markdown
   # [页面标题] - Deep Agents

   Source: https://docs.langchain.com/oss/python/deepagents/[页面路径]

   [文档内容]
   ```
5. 保存到 `SKILL_PATH/references/` 对应路径

**并行采集**：使用多个并行 agent（每批 6-8 个页面）加速采集，避免逐个串行等待。

**子目录处理**：
- `code/*` 页面 → `references/code/` 目录
- `frontend/*` 页面 → `references/frontend/` 目录
- 其他页面 → `references/` 根目录

### 步骤 6：更新 SKILL.md

更新 `SKILL_PATH/SKILL.md` 的文档索引部分：

1. 读取当前 SKILL.md
2. 在文档索引表中添加新页面的条目
3. 确保所有新页面都有正确的 `[[references/xxx.md]]` 链接
4. 如果步骤 4 发现结构变化，同步更新 SKILL.md 中的架构说明
5. 更新 description 字段以反映新增的关键能力

### 步骤 7：输出变更报告

向用户输出结构化报告：

```
## DeepAgents 更新报告

### Python 包
| 包 | 旧版本 | 新版本 |
|---|--------|--------|
| deepagents | x.y.z | a.b.c |
| langchain | ... | ... |
| langgraph | ... | ... |

### 文档结构变更
- [列出 harness.md 的结构变化]

### 新增页面（N 个）
- [页面名] — 一句话说明
- ...

### 已有页面（M 个，未变更）
- [列表]

### 已移除页面（如有）
- [列表]（仅报告，未删除）
```

## 关键注意事项

- **不要删除已有页面**：即使官方移除了某个页面，本地保留无害
- **不要覆盖已有页面**：除非步骤 4 检测到结构变化才重写 harness.md；其他已有页面保持不变
- **保留交叉引用格式**：文件内的 `[[xxx.md]]` 链接格式是技能的渐进式加载机制，必须保留
- **并行但不过载**：每批最多 8 个并行 webReader 请求，避免被限流
- **超时处理**：如果某个页面获取超时或失败，跳过并在报告中标注，不阻塞整体流程
