---
name: deepxiv
description: 使用 deepxiv CLI 工具搜索学术论文、渐进式阅读论文内容、发现近期热点论文。当用户想要搜索论文、查找论文、阅读论文、了解某个研究方向、跟踪学术热点、查找 trending 论文、获取论文摘要/章节/全文、搜索 arXiv 论文、查找生物医学文献、搜索 PMC 论文、使用 Semantic Scholar、或者提到"论文"、"paper"、"arXiv"、"学术"、"研究趋势"、"热点论文"时，使用此 skill。即使用户只是说"帮我找几篇关于 X 的论文"或"最近有什么热门论文"，也应触发此 skill。
---

# DeepXiv 论文搜索与阅读 Skill

通过 `deepxiv` CLI 工具，像真正的科研工作者一样高效地搜索、筛选和阅读学术论文。

核心理念：**不要一上来就盲读全文**，而是根据信息需求，按层渐进式访问论文内容。

## 语言要求

**所有返回给用户的说明性内容必须使用中文。** 具体规则：

- 论文标题、作者姓名、机构名、期刊名等专有名词保持原文（通常是英文）
- TLDR、关键词等论文自带的元数据字段保持原文
- 你对搜索结果的解释、筛选建议、摘要说明、趋势分析、推荐理由等**所有你自己生成的说明性文字**都用中文
- 对论文内容的概括和解读用中文
- 错误信息和状态提示用中文

## 前置条件

- 已安装 `deepxiv-sdk`：`pip install deepxiv-sdk`
- 首次使用时 CLI 会自动注册免费 token（每天 10,000 请求额度）

## 重要：Windows 编码问题

在 Windows 环境下，deepxiv CLI 输出包含 emoji 字符，会导致 GBK 编码错误。**所有 deepxiv 命令都必须加 `PYTHONIOENCODING=utf-8` 前缀**：

```bash
PYTHONIOENCODING=utf-8 deepxiv search "关键词"
PYTHONIOENCODING=utf-8 deepxiv paper 2409.05591 --brief
```

在 Bash 工具中执行时，始终使用这个前缀。如果仍然报编码错，可以加 `2>&1` 将 stderr 重定向。

## 工作流一：搜索 + 渐进式阅读

这是最常用的论文研究工作流。核心是"先搜、再筛、再精读"。

### 第 1 步：搜索论文

```bash
PYTHONIOENCODING=utf-8 deepxiv search "搜索关键词" --limit 10
```

常用参数：
- `--limit N`：返回结果数量（最大 100）
- `--date-from YYYY-MM-DD`：筛选起始日期
- `--format json` 或 `--json`：JSON 格式输出（便于解析）
- `--categories`：按 arXiv 分类筛选

### 第 2 步：快速筛选（brief）

对搜索结果中感兴趣的论文，先用 `--brief` 判断值不值得继续看：

```bash
PYTHONIOENCODING=utf-8 deepxiv paper <arxiv_id> --brief
```

`--brief` 返回：标题、TLDR、关键词、引用数、GitHub 链接。token 消耗极低。

**筛选建议**：
- 对搜索结果批量跑 `--brief`，快速过滤不相关的
- 优先关注引用数高、有 GitHub 仓库的论文
- 用中文向用户简要说明每篇论文的核心贡献和是否值得深入

### 第 3 步：了解结构（head）

对值得深入的论文，用 `--head` 掌握章节结构和 token 分布：

```bash
PYTHONIOENCODING=utf-8 deepxiv paper <arxiv_id> --head
```

`--head` 返回：完整元数据、章节列表、每个章节的预估 token 数。帮助你判断哪些章节最值得读。

### 第 4 步：精准精读（section）

只读最值钱的部分：

```bash
PYTHONIOENCODING=utf-8 deepxiv paper <arxiv_id> --section "Section Name"
```

常见的关键章节：`Introduction`、`Method`、`Experiments`、`Results`、`Conclusion`。

**章节选择策略**：
- 想了解方法原理 → 读 `Method` 或 `Approach`
- 想看实验效果 → 读 `Experiments` 或 `Results`
- 想快速了解全貌 → 读 `Introduction` + `Conclusion`
- 用中文向用户总结章节要点

### 第 5 步（可选）：完整论文

只在任务确实需要全文时才使用：

```bash
PYTHONIOENCODING=utf-8 deepxiv paper <arxiv_id>
```

或获取结构化 JSON：

```bash
PYTHONIOENCODING=utf-8 deepxiv paper <arxiv_id> --json
```

## 工作流二：热点发现

了解"现在什么最值得看"，而不只是"找得到"。

### 获取近期热门论文

```bash
PYTHONIOENCODING=utf-8 deepxiv trending --days 7 --limit 30
```

参数：
- `--days N`：回溯天数（推荐 7 或 30）
- `--limit N`：返回数量
- `--json`：JSON 格式输出

**处理流程**：
1. 获取 trending 列表
2. 用中文总结热门趋势和主题聚类
3. 按用户关注的领域筛选相关论文
4. 对相关论文跑 `--brief` 提供简要中文说明
5. 对用户特别感兴趣的论文进一步跑 `--head` 或 `--section`

### 查看单篇论文的热度

```bash
PYTHONIOENCODING=utf-8 deepxiv paper <arxiv_id> --popularity
```

返回传播指标：views、tweets、likes、replies。用中文解读这些数据。

## 其他功能

### Web 搜索

```bash
PYTHONIOENCODING=utf-8 deepxiv wsearch "搜索词"
PYTHONIOENCODING=utf-8 deepxiv wsearch "搜索词" --json
```

注意：每次 `wsearch` 消耗 20 limit。适合搜索特定研究者或非标准关键词。

### Semantic Scholar 元数据

```bash
PYTHONIOENCODING=utf-8 deepxiv sc <semantic_scholar_id>
PYTHONIOENCODING=utf-8 deepxiv sc <semantic_scholar_id> --json
```

当已有 Semantic Scholar ID 时使用。

### 生物医学论文（PMC）

```bash
PYTHONIOENCODING=utf-8 deepxiv pmc PMC544940 --head   # 概览
PYTHONIOENCODING=utf-8 deepxiv pmc PMC544940          # 全文
```

## 常用命令速查

| 场景 | 命令 |
|------|------|
| 搜索论文 | `PYTHONIOENCODING=utf-8 deepxiv search "关键词" --limit 10` |
| 快速判断 | `PYTHONIOENCODING=utf-8 deepxiv paper <id> --brief` |
| 查看结构 | `PYTHONIOENCODING=utf-8 deepxiv paper <id> --head` |
| 读某章节 | `PYTHONIOENCODING=utf-8 deepxiv paper <id> --section "名称"` |
| 完整论文 | `PYTHONIOENCODING=utf-8 deepxiv paper <id>` |
| 近期热点 | `PYTHONIOENCODING=utf-8 deepxiv trending --days 7 --limit 30` |
| 热度指标 | `PYTHONIOENCODING=utf-8 deepxiv paper <id> --popularity` |
| Web 搜索 | `PYTHONIOENCODING=utf-8 deepxiv wsearch "关键词"` |
| 论文预览 | `PYTHONIOENCODING=utf-8 deepxiv paper <id> --preview` |

## 输出规范

使用此 skill 时，向用户返回的信息应遵循以下格式：

### 搜索结果呈现

用中文列表形式呈现，例如：

> **搜索到 5 篇相关论文：**
>
> 1. **[论文标题原文]** (arXiv: XXXX.XXXXX)
>    - 这篇论文提出了 [用中文概括核心贡献]
>    - 引用数：XX | 有 GitHub 仓库
>    - 推荐理由：[用中文简要说明为什么值得看]
>
> 2. ...

### 论文摘要呈现

> **论文摘要：[论文标题原文]**
>
> - **核心贡献**：[用中文总结]
> - **方法概述**：[用中文总结]
> - **关键发现**：[用中文总结]
> - **适用场景**：[用中文说明]

### 热点趋势呈现

> **近期论文热点趋势（过去 7 天）：**
>
> 🔥 **主题一**：[用中文概括主题]
> - [论文标题原文] — [用中文说明为什么热门]
>
> 📈 **主题二**：[用中文概括主题]
> - ...

## 错误处理

- 如果命令返回认证错误，提示用户：需要配置 token，运行 `deepxiv config --token YOUR_TOKEN`
- 如果达到日限额（429），提示用户额度已用完，明天再试或访问 https://data.rag.ac.cn/register 申请更高限额
- 如果论文未找到（404），检查 arXiv ID 格式是否正确，或尝试搜索确认
