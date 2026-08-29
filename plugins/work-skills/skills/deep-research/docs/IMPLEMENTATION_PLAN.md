# Deep Research Skill 实施计划

> ⚠️ **搜索层已迁移（v0.3.0）**：搜索与抓取改用 MCP 工具（`mcp__web-search-prime__web_search_prime` + `mcp__web-reader__webReader`），不再依赖 meta-search skill 或 Playwright。本文档记录迁移前的设计，搜索相关章节请以 [SKILL.md](../SKILL.md) 与 [SEARCH_MIGRATION.md](./SEARCH_MIGRATION.md) 为准。

> 将 LangChain 的 local-deep-researcher 移植为 Claude Code Skill

## 一、项目概述

### 目标
创建一个名为 `deep-research` 的 Claude Code skill，实现与 local-deep-researcher 相同的核心功能：**迭代式深度研究工作流**，通过多轮"搜索-总结-反思"循环生成带引用的综合性研究报告。

### 核心价值
- **全流程自动化**：从搜索到报告生成，全自动执行
- **增量式知识构建**：每轮循环基于已有信息补充，避免重复
- **规范引用格式**：自动生成带来源链接的研究报告
- **可配置深度**：用户可自定义研究循环次数

---

## 二、架构差异分析

### local-deep-researcher (LangGraph)

| 组件 | 实现 | 说明 |
|------|------|------|
| **工作流编排** | LangGraph StateGraph | 有状态图，自动管理状态流转 |
| **LLM** | Ollama/LMStudio (本地) | 本地部署的开源模型 |
| **状态管理** | Annotated[list, operator.add] | 自动累积状态 |
| **搜索引擎** | Tavily/Perplexity/DuckDuckGo | 需要API密钥或自建 |
| **结构化输出** | Tool Calling / JSON Mode | 双模式fallback |

### Claude Code Skill (目标架构)

| 组件 | 实现 | 说明 |
|------|------|------|
| **工作流编排** | Claude Code Agent SDK + Task 工具 | 通过 subagent 并行/串行编排 |
| **LLM** | Claude API (Opus/Sonnet) | 云端 API，高质量输出 |
| **状态管理** | 内存变量 + 文件持久化 | 手动管理状态传递 |
| **搜索引擎** | Volcengine 搜索 / Playwright | 已集成的 MCP 工具 |
| **结构化输出** | Claude 原生工具调用 | JSON 模式 |

---

## 三、核心架构设计

### 3.1 Skill 目录结构

```
deep-research/
├── SKILL.md                    # Skill 主文档（用户入口）
├── agents/
│   ├── research-node-query.md      # 查询生成节点
│   ├── research-node-search.md     # 搜索执行节点
│   ├── research-node-summary.md    # 来源总结节点
│   ├── research-node-reflect.md    # 反思节点
│   └── research-node-finalize.md   # 最终化节点
├── scripts/
│   ├── state_manager.py         # 状态管理工具
│   └── search_adapter.py        # 搜索引擎适配器
├── references/
│   └── prompts.py               # 提示词模板（供引用）
└── config.json                  # 默认配置
```

### 3.2 工作流编排设计

由于 Claude Code 不支持 LangGraph 风格的有状态图，采用 **主控脚本 + Subagent 节点** 模式：

```
┌─────────────────────────────────────────────────────────────┐
│                    Deep Research 主控流程                     │
│                    (在主会话中执行)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   初始化状态     │
                    │ (research_topic)│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  for i in loops  │◄─────────────────┐
                    │  (1 to max_loops)│                   │
                    └────────┬────────┘                   │
                             │                            │
              ┌──────────────┼──────────────┐             │
              ▼              ▼              ▼             │
        ┌──────────┐   ┌──────────┐   ┌──────────┐        │
        │生成查询  │   │执行搜索  │   │总结来源  │        │
        │(Subagent)│   │(Subagent)│   │(Subagent)│        │
        └─────┬────┘   └─────┬────┘   └─────┬────┘        │
              │              │              │              │
              └──────────────┼──────────────┘              │
                             ▼                             │
                      ┌──────────┐                        │
                      │  反思    │                        │
                      │(Subagent)│                        │
                      └─────┬────┘                        │
                            │                             │
                 ┌──────────┴──────────┐                  │
                 ▼                     ▼                  │
          有知识缺口？             达到最大次数             │
                 │                     │                  │
                 └─────────────────────┘                  │
                                       │                  │
                                       ▼                  │
                               ┌──────────┐               │
                               │ 最终化   │               │
                               │(Subagent)│               │
                               └──────────┘               │
                                       │                  │
                                       └──────────────────┘
```

---

## 四、核心组件实现方案

### 4.1 状态管理 (state_manager.py)

```python
"""
研究状态管理
- 保存/加载中间状态
- 追踪循环次数
- 累积搜索结果和来源
"""

@dataclass
class ResearchState:
    research_topic: str
    search_query: str = ""
    running_summary: str = ""
    sources: List[str] = field(default_factory=list)
    search_results: List[Dict] = field(default_factory=list)
    loop_count: int = 0

    def save(self, path: str):
        """保存状态到文件"""
        pass

    @classmethod
    def load(cls, path: str) -> "ResearchState":
        """从文件加载状态"""
        pass
```

### 4.2 搜索引擎适配器 (search_adapter.py)

```python
"""
统一搜索接口，适配多种搜索引擎
优先级：Volcengine > Playwright (必应) > DuckDuckGo
"""

class SearchAdapter:
    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        执行搜索并返回格式化结果

        Returns:
            List[SearchResult]: {
                "title": str,
                "url": str,
                "snippet": str
            }
        """
        pass
```

### 4.3 节点实现 (agents/)

每个节点是一个独立的 subagent 定义，包含：

#### research-node-query.md
```
任务：生成搜索查询

输入：
- research_topic: 研究主题
- running_summary: 当前摘要
- loop_count: 当前循环次数

输出：
- search_query: 优化后的搜索查询

提示词策略：
- 首轮：生成广泛覆盖主题的查询
- 后续：基于反思节点识别的知识缺口生成定向查询
```

#### research-node-search.md
```
任务：执行网络搜索

输入：
- search_query: 搜索查询

输出：
- search_results: 搜索结果列表
- sources: 来源链接列表

执行方式：
1. 使用 Volcengine MCP 搜索（优先）
2. 或使用 Playwright 访问必应搜索
3. 提取标题、链接、摘要
```

#### research-node-summary.md
```
任务：总结来源

输入：
- running_summary: 已有摘要
- search_results: 新搜索结果

输出：
- running_summary: 更新后的摘要

策略：
- 首次：创建初始摘要
- 后续：增量扩展，有机融合新信息
```

#### research-node-reflect.md
```
任务：反思并识别知识缺口

输入：
- research_topic: 原始研究主题
- running_summary: 当前摘要
- loop_count: 当前循环次数
- max_loops: 最大循环次数

输出：
- knowledge_gaps: 识别的知识缺口
- follow_up_query: 后续搜索查询
- should_continue: 是否继续研究
```

#### research-node-finalize.md
```
任务：最终化报告

输入：
- running_summary: 完整摘要
- sources: 所有来源链接

输出：
- final_report: Markdown 格式的最终报告

格式：
## 深度研究报告：{主题}

{摘要内容}

### 参考来源
- [标题](链接)
- ...
```

---

## 五、分步实施计划

### 阶段 1：基础架构 (1-2天)

| 任务 | 描述 | 优先级 |
|------|------|--------|
| 创建目录结构 | 按 3.1 规划创建目录 | P0 |
| 编写 SKILL.md | skill 入口文档，触发条件和使用说明 | P0 |
| 创建 state_manager.py | 状态保存/加载逻辑 | P0 |
| 创建 search_adapter.py | 搜索引擎统一接口 | P0 |

### 阶段 2：节点实现 (2-3天)

| 任务 | 描述 | 优先级 |
|------|------|--------|
| research-node-query | 查询生成节点提示词 | P0 |
| research-node-search | 搜索执行节点逻辑 | P0 |
| research-node-summary | 总结节点提示词 | P0 |
| research-node-reflect | 反思节点提示词 | P0 |
| research-node-finalize | 最终化节点逻辑 | P0 |

### 阶段 3：主控流程 (1-2天)

| 任务 | 描述 | 优先级 |
|------|------|--------|
| 编写主控脚本 | 编排各节点的工作流 | P0 |
| 集成状态管理 | 状态在节点间传递 | P0 |
| 实现循环控制 | 达到 max_loops 或无缺口时结束 | P0 |

### 阶段 4：测试与优化 (1-2天)

| 任务 | 描述 | 优先级 |
|------|------|--------|
| 端到端测试 | 完整工作流测试 | P0 |
| 错误处理 | 搜索失败、超时等异常 | P1 |
| 性能优化 | 减少不必要的 LLM 调用 | P2 |
| 文档完善 | 使用说明、示例 | P1 |

---

## 六、关键技术决策

### 6.1 搜索引擎选择

**决策**：优先使用 Volcengine MCP，备选 Playwright + 必应

| 搜索引擎 | 优势 | 劣势 |
|---------|------|------|
| **Volcengine MCP** | 已集成，API 简单 | 需要确认可用性 |
| **Playwright + 必应** | 稳定可靠，智能摘要 | 稍慢 |
| **DuckDuckGo** | 免费，无需密钥 | 质量一般 |

### 6.2 状态管理策略

**决策**：文件持久化 + 内存传递

- 每轮循环后保存状态到临时文件
- 支持中断后恢复
- 同时在内存中维护当前状态

### 6.3 并行 vs 串行

**决策**：串行执行（与原项目一致）

- 理由：后续循环依赖前续结果
- 优化：单轮内的搜索可以使用多查询并行

### 6.4 输出格式

**决策**：Markdown 格式（带引用链接）

```markdown
## 深度研究报告：{研究主题}

### 研究摘要

{累积的摘要内容，自动分段和结构化}

### 参考来源

1. [标题 1](链接1) - 摘要说明
2. [标题 2](链接2) - 摘要说明
...

---

*本报告由 deep-research skill 自动生成*
*研究循环：{实际循环次数}/{配置的最大循环次数}*
```

---

## 七、风险评估与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **搜索引擎不可用** | 高 | 实现多引擎 fallback |
| **LLM 调用超时** | 中 | 实现重试机制，降低超时时间 |
| **上下文限制** | 中 | 增量总结，避免全量处理 |
| **状态文件损坏** | 低 | 定期备份，异常检测 |

---

## 八、成功标准

### 功能标准
- [ ] 能够执行完整的研究循环（默认 3 轮）
- [ ] 每轮循环生成定向搜索查询
- [ ] 搜索结果被正确累积和去重
- [ ] 最终报告包含完整的引用链接

### 质量标准
- [ ] 研究摘要结构清晰，分段合理
- [ ] 来源链接有效可访问
- [ ] 无明显的重复内容

### 性能标准
- [ ] 单轮循环耗时 < 2 分钟
- [ ] 完整报告生成 < 10 分钟（3 轮）

---

## 九、后续扩展方向

1. **多语言支持**：中英文研究模式切换
2. **自定义搜索引擎**：用户配置偏好引擎
3. **研究模板**：针对不同领域的预设模板（学术、市场、技术）
4. **导出格式**：支持 PDF、Word、JSON 等格式
5. **可视化**：研究过程的时间线或知识图谱

---

## 十、参考资源

- [local-deep-researcher 源码](https://github.com/langchain-ai/local-deep-researcher)
- [Claude Code Agent SDK 文档](https://docs.anthropic.com/en/docs/claude-code/agent-sdk)
- [Volcengine MCP 文档](https://github.com/Volcengine/volcengine-mcp-server)
- [Playwright MCP 文档](https://github.com/modelcontextprotocol/servers/tree/main/src/playwright)

---

*文档版本：1.0*
*创建日期：2026-03-24*
