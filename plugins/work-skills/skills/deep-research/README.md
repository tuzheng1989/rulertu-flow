# Deep Research Skill

> 深度研究助手 - 基于 IterDRAG 方法论的迭代式研究工具

[![Version](https://img.shields.io/badge/version-0.2.0--beta-blue)](https://github.com)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com)

## 概述

Deep Research Skill 是一个 Claude Code skill，通过多轮"搜索-总结-反思"循环自动生成带引用的综合性研究报告。

### 核心特性

- **迭代式研究**: 多轮循环逐步完善内容
- **增量式总结**: 每轮基于已有信息补充，避免重复
- **规范引用**: 自动生成带来源链接的研究报告
- **可配置深度**: 自定义研究循环次数
- **MCP 工具搜索**: 通过 `mcp__web-search-prime__web_search_prime` 与 `mcp__web-reader__webReader` 完成搜索与抓取，无需 Playwright
- **会话恢复**: 支持中断后继续研究

## 工作流程

```
用户输入研究主题
        │
        ▼
┌───────────────────┐
│  SKILL.md 触发    │
└─────────┬─────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│          研究循环 (默认 3 轮)                  │
│  ┌───────────────────────────────────────┐  │
│  │ 1. 生成查询 → Subagent                │  │
│  │ 2. 网络搜索 → MCP (web-search-prime)  │  │
│  │ 3. 整合摘要 → Subagent                │  │
│  │ 4. 反思决策 → Subagent                │  │
│  └───────────────────────────────────────┘  │
│           ↓ 是否继续? ↓                       │
│     Yes ←───────────┐ No                    │
└─────────┬───────────┴───────────────────────┘
          │
          ▼
┌───────────────────┐
│  生成最终报告      │
│  (Markdown 格式)   │
└───────────────────┘
```

## 安装

### 1. 复制到 skill 目录

```bash
# 复制到项目 skill 目录
cp -r deep-research ~/.claude/skills/

# 或复制到全局 skill 目录
cp -r deep-research /path/to/skillResearch/skills/
```

### 2. 确认 MCP 工具可用

确保以下 MCP 工具已配置（本项目全局规则强制要求，禁止内置 WebSearch / WebFetch）：
- **mcp__web-search-prime__web_search_prime** - 网络搜索
- **mcp__web-reader__webReader** - 网页全文抓取

无需 Playwright，也不依赖 meta-search skill。

## 使用方法

### 基本用法

```
用户: 帮我深入研究"量子计算在密码学中的应用"
```

### 指定循环次数

```
用户: 研究一下"Rust 语言的所有权机制"，循环 5 次
```

### 命令行测试

```bash
# 进入脚本目录
cd deep-research/scripts

# 基本研究
python orchestrator.py "量子计算在密码学中的应用"

# 自定义循环次数
python orchestrator.py "Rust 所有权机制" --loops 5

# 恢复会话
python orchestrator.py --resume abc12345

# 列出所有会话
python orchestrator.py --list-sessions

# 清理所有会话
python state_manager.py clean
```

## 配置选项

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_loops` | 3 | 最大研究循环次数 |
| `search_location` | us | 搜索区域（`us` 英文资料 / `cn` 中文资料） |
| `content_size` | high | 搜索摘要详细度（`high` / `medium`） |
| `search_recency_filter` | noLimit | 时效过滤（`oneYear` / `oneMonth` / `oneWeek` 等） |

## 目录结构

```
deep-research/
├── SKILL.md                    # Skill 入口文档（触发条件）
├── README.md                   # 本文件
├── config.json                 # 配置文件
├── agents/                     # Subagent 任务定义
│   ├── research-node-query.md      # 查询生成节点
│   ├── research-node-summary.md    # 总结节点
│   ├── research-node-reflect.md    # 反思节点
│   └── research-node-finalize.md   # 最终化节点
├── scripts/                    # 核心脚本
│   ├── orchestrator.py             # 主控流程（使用 Claude CLI）
│   ├── state_manager.py            # 状态管理
│   └── test_state_manager.py       # 状态管理测试
└── docs/                       # 设计文档
    ├── IMPLEMENTATION_PLAN.md      # 实施计划
    ├── ARCHITECTURE.md             # 架构设计
    └── PROMPTS.md                  # 提示词参考
```

## 输出格式

研究报告以 Markdown 格式输出，包含：

```markdown
# 深度研究报告：{研究主题}

> 📅 生成时间: {timestamp}
> 🔁 研究轮次: {loop_count} 轮
> 📚 来源数量: {sources_count} 个

---

## 执行摘要
{200-300 字的概括}

---

## 详细研究
### 核心概念
### 主要特点
### 技术原理
### 应用场景
### 发展现状
### 挑战与局限

---

## 关键发现
1. 发现一
2. 发现二
3. 发现三

---

## 参考来源
1. **[标题]**(链接) - 说明
2. **[标题]**(链接) - 说明
...

---

## 附录
- 研究方法论
- 搜索策略
```

## 开发状态

### v0.3.0 (当前)

**已完成：**
- ✅ 基础架构设计（Subagent 模式）
- ✅ 状态管理系统（31/31 测试通过）
- ✅ 节点任务定义
- ✅ Claude CLI 集成
- ✅ 状态管理测试套件
- ✅ 搜索层迁移至 MCP 工具（web-search-prime + web-reader），移除 meta-search 与 Playwright 依赖

**待完成：**
- ⏳ 完整端到端测试
- ⏳ 提示词优化
- ⏳ 文档完善

### 路线图

- [x] v0.1.0-alpha: 原型版本
- [x] v0.2.0-beta: Subagent 模式 + meta-search 集成
- [x] v0.3.0: 搜索层迁移至 MCP 工具
- [ ] v0.4.0: 多语言支持
- [ ] v1.0.0: 稳定版本发布

## 参考资源

- [local-deep-researcher](https://github.com/langchain-ai/local-deep-researcher) - 原始项目
- [IterDRAG 论文](https://arxiv.org/abs/2401.16369) - 方法论基础
- [Claude Code 文档](https://docs.anthropic.com/claude-code) - Agent SDK
- [web-search-prime / web-reader MCP] - 网络搜索与网页抓取（本项目 MCP 工具，替代 meta-search）

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

---

*本 skill 由 Claude Code 创建*
*版本: 0.2.0-beta*
*生成时间: 2026-03-24*
