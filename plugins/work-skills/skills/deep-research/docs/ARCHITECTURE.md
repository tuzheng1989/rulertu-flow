# Deep Research Skill - 架构设计文档

> ⚠️ **搜索层已迁移（v0.3.0）**：搜索与抓取改用 MCP 工具（`mcp__web-search-prime__web_search_prime` + `mcp__web-reader__webReader`），不再依赖 meta-search skill 或 Playwright。本文档记录迁移前的设计，搜索相关章节请以 [SKILL.md](../SKILL.md) 与 [SEARCH_MIGRATION.md](./SEARCH_MIGRATION.md) 为准。

## 一、系统架构概览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         用户请求研究主题                              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Deep Research Skill                          │
│                        (SKILL.md 入口)                              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────┐           ┌─────────────────────┐
        │   主控流程         │           │   状态管理器         │
        │  (Main Orchestrator)│         │  (State Manager)    │
        └─────────┬─────────┘           └─────────────────────┘
                  │
        ┌─────────┴─────────────────────────────────┐
        │                                           │
        ▼                                           ▼
┌───────────────────┐                   ┌─────────────────────┐
│  Research Loop    │                   │  搜索引擎适配器      │
│  (迭代研究循环)    │◄──────────────────│  (Search Adapter)   │
└─────────┬─────────┘                   └─────────────────────┘
          │
          │
    ┌─────┼─────┬─────┬─────┬─────┐
    ▼     ▼     ▼     ▼     ▼     ▼
┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
│ Query││Search││Summary││Reflect││Finalize│
│ Node ││ Node ││ Node ││ Node ││  Node │
└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘
    │     │     │     │     │     │
    └─────┴─────┴─────┴─────┴─────┘
                  │
                  ▼
        ┌───────────────────┐
        │   最终研究报告     │
        │  (Markdown 输出)  │
        └───────────────────┘
```

### 1.2 数据流图

```
用户输入研究主题
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  初始化阶段                                                   │
│  - 创建 ResearchState                                         │
│  - 加载配置 (max_loops, 搜索引擎等)                            │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  研究循环 (for i in 1..max_loops)                             │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Query Node: 生成搜索查询                                │ │
│  │ 输入: research_topic, running_summary (if exists)       │ │
│  │ 输出: search_query                                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                          ▼                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Search Node: 执行搜索                                  │ │
│  │ 输入: search_query                                     │ │
│  │ 输出: search_results, sources                          │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                          ▼                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Summary Node: 整合来源                                  │ │
│  │ 输入: running_summary, search_results                   │ │
│  │ 输出: running_summary (updated)                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                          ▼                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Reflect Node: 反思与决策                               │ │
│  │ 输入: research_topic, running_summary, loop_count       │ │
│  │ 输出: knowledge_gaps, should_continue                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                    │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ should_continue? │
                  └────────┬─────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
           Yes                         No
              │                         │
              ▼                         ▼
         继续循环                  ┌─────────────────┐
                                   │  Finalize Node  │
                                   │  生成最终报告    │
                                   └─────────────────┘
                                           │
                                           ▼
                                    ┌─────────────────┐
                                    │  输出 Markdown   │
                                    └─────────────────┘
```

---

## 二、核心组件详细设计

### 2.1 ResearchState (状态管理)

```python
@dataclass
class ResearchState:
    """研究状态数据类"""

    # === 基础信息 ===
    research_topic: str              # 研究主题
    max_loops: int = 3               # 最大循环次数
    loop_count: int = 0              # 当前循环次数

    # === 查询与搜索 ===
    search_query: str = ""           # 当前搜索查询
    search_results: List[Dict] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)

    # === 摘要与反思 ===
    running_summary: str = ""        # 累积摘要
    knowledge_gaps: List[str] = field(default_factory=list)

    # === 元数据 ===
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ResearchState":
        """从字典反序列化"""
        return cls(**data)

    def save(self, filepath: str):
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "ResearchState":
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def add_sources(self, new_sources: List[str]):
        """添加新来源，自动去重"""
        existing = set(self.sources)
        for source in new_sources:
            if source not in existing:
                self.sources.append(source)
                existing.add(source)

    def should_continue(self) -> bool:
        """判断是否应该继续研究"""
        return self.loop_count < self.max_loops
```

### 2.2 SearchAdapter (搜索引擎适配器)

```python
class SearchAdapter:
    """搜索引擎适配器，支持多引擎 fallback"""

    def __init__(self, preferred_engine: str = "volcengine"):
        self.preferred_engine = preferred_engine

    async def search(
        self,
        query: str,
        max_results: int = 10
    ) -> List[SearchResult]:
        """
        执行搜索，支持引擎 fallback

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            List[SearchResult]: 搜索结果列表
        """
        engines = self._get_engine_priority()

        for engine in engines:
            try:
                results = await self._search_with_engine(
                    engine, query, max_results
                )
                if results:
                    return results
            except Exception as e:
                logger.warning(f"{engine} 搜索失败: {e}")
                continue

        raise RuntimeError("所有搜索引擎均失败")

    def _get_engine_priority(self) -> List[str]:
        """获取引擎优先级列表"""
        if self.preferred_engine == "volcengine":
            return ["volcengine", "playwright_bing", "duckduckgo"]
        elif self.preferred_engine == "bing":
            return ["playwright_bing", "volcengine", "duckduckgo"]
        else:
            return ["duckduckgo", "playwright_bing", "volcengine"]

    async def _search_with_engine(
        self,
        engine: str,
        query: str,
        max_results: int
    ) -> List[SearchResult]:
        """使用指定引擎执行搜索"""
        if engine == "volcengine":
            return await self._search_volcengine(query, max_results)
        elif engine == "playwright_bing":
            return await self._search_playwright_bing(query, max_results)
        elif engine == "duckduckgo":
            return await self._search_duckduckgo(query, max_results)
        else:
            raise ValueError(f"未知引擎: {engine}")

    async def _search_volcengine(
        self,
        query: str,
        max_results: int
    ) -> List[SearchResult]:
        """使用 Volcengine MCP 搜索"""
        # 调用 mcp__volcengine-webserarch__volcengine_web_search
        pass

    async def _search_playwright_bing(
        self,
        query: str,
        max_results: int
    ) -> List[SearchResult]:
        """使用 Playwright + 必应搜索"""
        # 调用 Playwright MCP 工具
        pass

    async def _search_duckduckgo(
        self,
        query: str,
        max_results: int
    ) -> List[SearchResult]:
        """使用 DuckDuckGo 搜索"""
        # 使用 duckduckgo-search 库或 API
        pass
```

### 2.3 节点提示词设计

#### Query Node Prompt

```markdown
你是一个研究查询生成专家。你的任务是根据研究主题和当前研究进展，生成优化的搜索查询。

## 输入信息

- **研究主题**: {research_topic}
- **当前摘要**: {running_summary}
- **循环次数**: {loop_count} / {max_loops}

## 任务要求

### 首轮循环 (loop_count == 1)
生成一个广泛覆盖研究主题的查询，帮助建立基础理解。

### 后续循环 (loop_count > 1)
基于当前摘要和识别的知识缺口，生成针对性的后续查询。

## 输出格式

直接输出优化后的搜索查询，不要包含任何解释或额外内容。

## 示例

研究主题: "量子计算在密码学中的应用"

首轮输出: "quantum computing cryptography applications"
后续输出: "quantum resistant algorithms post-quantum cryptography"
```

#### Summary Node Prompt

```markdown
你是一个研究摘要专家。你的任务是将新的搜索结果整合到现有的研究摘要中。

## 输入信息

- **研究主题**: {research_topic}
- **现有摘要**: {running_summary}
- **新搜索结果**: {search_results}

## 任务要求

### 如果是首轮 (没有现有摘要)
创建一个结构化的初始摘要，覆盖搜索结果的核心内容。

### 如果是后续轮次
1. 保留现有摘要的核心结构
2. 将新信息有机融入相关段落
3. 避免重复内容
4. 保持连贯性和逻辑性

## 输出格式

```markdown
## 研究摘要

### 核心概念
[核心概念和定义]

### 主要发现
[主要发现和观点]

### 技术细节
[技术层面的详细信息]

### 应用场景
[实际应用和案例]

### 挑战与局限
[当前面临的挑战]
```

## 注意事项

- 保持客观中立的语气
- 使用清晰的结构和分段
- 为重要观点标注来源（使用 [n] 引用格式）
```

#### Reflect Node Prompt

```markdown
你是一个研究反思专家。你的任务是分析当前研究摘要，识别知识缺口，并决定是否需要进一步研究。

## 输入信息

- **研究主题**: {research_topic}
- **当前摘要**: {running_summary}
- **循环次数**: {loop_count} / {max_loops}

## 任务要求

1. **评估完整性**: 当前摘要是否充分覆盖了研究主题的核心维度？
2. **识别缺口**: 哪些重要方面尚未充分探索？
3. **生成后续查询**: 如果需要继续研究，生成针对性的后续查询
4. **决策**: 基于缺口情况和研究深度，决定是否继续

## 输出格式

```json
{
  "completeness_score": <1-10 分数>,
  "knowledge_gaps": ["缺口1", "缺口2", ...],
  "follow_up_query": "后续搜索查询（如果需要）",
  "should_continue": true/false,
  "reasoning": "决策理由"
}
```

## 评估维度

- 核心概念和定义
- 技术原理和机制
- 应用场景和案例
- 最新进展和趋势
- 挑战和局限性
- 对比和 alternatives
```

#### Finalize Node Prompt

```markdown
你是一个研究报告生成专家。你的任务是将研究摘要和来源整理成一份规范的专业报告。

## 输入信息

- **研究主题**: {research_topic}
- **完整摘要**: {running_summary}
- **所有来源**: {sources}
- **总循环次数**: {loop_count}

## 任务要求

1. **结构化报告**: 使用清晰的标题和分段
2. **格式化来源**: 将来源列表格式化为规范的引用
3. **添加元数据**: 包含研究日期、循环次数等信息

## 输出格式

```markdown
# 深度研究报告：{research_topic}

> 生成时间: {timestamp}
> 研究循环: {loop_count} 轮

---

{structured_summary}

---

## 参考来源

{numbered_sources}

---

*本报告由 Deep Research Skill 自动生成*
```

## 来源格式化规则

- 按出现顺序编号
- 格式: `[n] [标题](链接) - 简短说明`
- 去重并按相关性排序
```

---

## 三、主控流程设计

### 3.1 主控伪代码

```python
async def deep_research_main(
    research_topic: str,
    max_loops: int = 3,
    preferred_engine: str = "volcengine"
) -> str:
    """
    深度研究主控流程

    Args:
        research_topic: 研究主题
        max_loops: 最大研究循环次数
        preferred_engine: 首选搜索引擎

    Returns:
        str: Markdown 格式的最终报告
    """

    # 1. 初始化状态
    state = ResearchState(
        research_topic=research_topic,
        max_loops=max_loops
    )

    # 2. 创建辅助组件
    search_adapter = SearchAdapter(preferred_engine)

    # 3. 研究循环
    while state.should_continue():
        state.loop_count += 1

        # === Node 1: 生成查询 ===
        state.search_query = await _run_query_node(state)

        # === Node 2: 执行搜索 ===
        search_results = await search_adapter.search(
            state.search_query,
            max_results=10
        )
        state.search_results.extend(search_results)

        # === Node 3: 总结来源 ===
        state.running_summary = await _run_summary_node(
            state,
            search_results
        )

        # === Node 4: 反思与决策 ===
        reflect_result = await _run_reflect_node(state)

        state.knowledge_gaps = reflect_result["knowledge_gaps"]

        if not reflect_result["should_continue"]:
            break

    # 4. 最终化报告
    final_report = await _run_finalize_node(state)

    return final_report
```

### 3.2 节点执行函数

```python
async def _run_query_node(state: ResearchState) -> str:
    """执行查询生成节点"""

    prompt = f"""你是研究查询生成专家。

## 输入
- 研究主题: {state.research_topic}
- 当前摘要: {state.running_summary or "(无)"}
- 循环次数: {state.loop_count}/{state.max_loops}

## 任务
生成优化的搜索查询。

## 输出
直接输出查询，不要解释。
"""

    response = await call_clude_api(
        model="claude-sonnet-4-6",
        prompt=prompt,
        max_tokens=200
    )

    return response.strip()

async def _run_summary_node(
    state: ResearchState,
    new_results: List[Dict]
) -> str:
    """执行总结节点"""

    results_text = _format_search_results(new_results)

    prompt = f"""你是研究摘要专家。

## 输入
- 研究主题: {state.research_topic}
- 现有摘要: {state.running_summary or "(无)"}
- 新搜索结果: {results_text}

## 任务
将新结果整合到摘要中。

{(_SUMMARY_INSTRUCTIONS if not state.running_summary else _SUMMARY_UPDATE_INSTRUCTIONS)}
"""

    response = await call_claude_api(
        model="claude-sonnet-4-6",
        prompt=prompt,
        max_tokens=4000
    )

    return response.strip()

async def _run_reflect_node(state: ResearchState) -> Dict:
    """执行反思节点"""

    prompt = f"""你是研究反思专家。

## 输入
- 研究主题: {state.research_topic}
- 当前摘要: {state.running_summary}
- 循环次数: {state.loop_count}/{state.max_loops}

## 任务
评估完整性，识别缺口，决策是否继续。

## 输出格式
JSON:
{{
  "completeness_score": <1-10>,
  "knowledge_gaps": ["缺口1", "缺口2"],
  "follow_up_query": "后续查询",
  "should_continue": true/false,
  "reasoning": "决策理由"
}}
"""

    response = await call_claude_api(
        model="claude-sonnet-4-6",
        prompt=prompt,
        max_tokens=1000
    )

    return json.loads(response)

async def _run_finalize_node(state: ResearchState) -> str:
    """执行最终化节点"""

    sources_text = _format_sources(state.sources)

    prompt = f"""你是研究报告生成专家。

## 输入
- 研究主题: {state.research_topic}
- 完整摘要: {state.running_summary}
- 来源列表: {sources_text}
- 循环次数: {state.loop_count}

## 任务
生成规范的 Markdown 报告。

{(_FINALIZE_INSTRUCTIONS)}
"""

    response = await call_claude_api(
        model="claude-sonnet-4-6",
        prompt=prompt,
        max_tokens=8000
    )

    return response.strip()
```

---

## 四、SKILL.md 结构设计

```markdown
---
name: deep-research
description: 深度研究助手，通过迭代式"搜索-总结-反思"循环生成带引用的综合性研究报告。适用于需要深入了解某个主题、收集多维度信息的场景。
---

# deep-research

深度研究助手，基于 IterDRAG 方法论，通过多轮迭代循环生成结构化研究报告。

## 核心特性

- **迭代式研究**: 多轮"搜索-总结-反思"循环，逐步完善内容
- **增量式总结**: 每轮基于已有信息补充，避免重复
- **规范引用**: 自动生成带来源链接的研究报告
- **可配置深度**: 自定义研究循环次数

## 适用场景

- 学术主题研究
- 技术方案调研
- 市场分析
- 竞品分析
- 行业趋势研究

## 使用方法

### 基本用法

```
用户: 帮我深入研究"量子计算在密码学中的应用"
```

### 高级用法

```
用户: 研究一下"Rust 语言的所有权机制"，循环 5 次
```

## 工作流程

```
1. 初始化研究状态
2. 循环 (用户指定的次数):
   a. 生成搜索查询
   b. 执行网络搜索
   c. 整合到摘要
   d. 反思并识别缺口
3. 生成最终报告
```

## 配置选项

- `max_loops`: 最大循环次数 (默认: 3)
- `search_engine`: 搜索引擎 (volcengine/bing/duckduckgo)
- `max_results`: 每轮最大搜索结果数 (默认: 10)

## 输出格式

Markdown 格式的研究报告，包含:
- 结构化摘要
- 分段内容
- 编号引用来源

## 依赖要求

- Claude API 访问
- 网络连接
- 搜索引擎访问
```

---

## 五、错误处理与容错设计

### 5.1 搜索失败处理

```python
async def search_with_fallback(
    query: str,
    max_retries: int = 3
) -> List[SearchResult]:
    """带 fallback 的搜索"""

    for attempt in range(max_retries):
        try:
            results = await search_adapter.search(query)
            return results
        except Exception as e:
            if attempt == max_retries - 1:
                # 最后一次失败，使用备选策略
                return await _fallback_search_strategy(query)
            logger.warning(f"搜索失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            await asyncio.sleep(2 ** attempt)  # 指数退避
```

### 5.2 LLM 调用超时处理

```python
async def call_claude_with_timeout(
    prompt: str,
    timeout: int = 30
) -> str:
    """带超时的 Claude 调用"""

    try:
        async with asyncio.timeout(timeout):
            return await anthropic.messages.create(...)
    except asyncio.TimeoutError:
        # 返回安全的默认响应
        return _get_default_response(prompt)
```

### 5.3 状态恢复机制

```python
def save_checkpoint(state: ResearchState):
    """保存检查点"""
    checkpoint_dir = Path.home() / ".claude" / "deep-research" / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = checkpoint_dir / f"{state.created_at}.json"
    state.save(checkpoint_path)

def load_latest_checkpoint() -> Optional[ResearchState]:
    """加载最新的检查点"""
    checkpoint_dir = Path.home() / ".claude" / "deep-research" / "checkpoints"

    checkpoints = sorted(checkpoint_dir.glob("*.json"), reverse=True)
    if checkpoints:
        return ResearchState.load(checkpoints[0])
    return None
```

---

## 六、性能优化策略

### 6.1 并行搜索

```python
async def parallel_search(
    queries: List[str],
    max_results: int = 10
) -> List[SearchResult]:
    """并行执行多个搜索查询"""

    tasks = [
        search_adapter.search(q, max_results)
        for q in queries
    ]

    results = await asyncio.gather(*tasks)

    # 合并去重
    all_results = []
    seen_urls = set()

    for result_list in results:
        for result in result_list:
            if result.url not in seen_urls:
                all_results.append(result)
                seen_urls.add(result.url)

    return all_results
```

### 6.2 增量总结缓存

```python
@lru_cache(maxsize=100)
def get_summary_template(topic: str) -> str:
    """缓存摘要模板"""
    return generate_summary_template(topic)
```

### 6.3 流式输出支持

```python
async def stream_research_progress(
    research_topic: str,
    max_loops: int = 3
) -> AsyncIterator[str]:
    """流式输出研究进度"""

    for loop in range(1, max_loops + 1):
        yield f"🔄 开始第 {loop}/{max_loops} 轮研究...\n"

        # 执行研究步骤...
        yield f"  ✅ 生成查询: {query}\n"
        yield f"  ✅ 搜索完成: {len(results)} 条结果\n"
        yield f"  ✅ 摘要更新完成\n"

        reflect_result = await _run_reflect_node(state)
        if not reflect_result["should_continue"]:
            yield f"  ℹ️  研究完成，无需继续\n"
            break
```

---

*文档版本: 1.0*
*创建日期: 2026-03-24*
