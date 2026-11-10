# code-review 未修项记档（324159a 返工后余项）

- 来源：/code-review HEAD（2026-11-10，10 条 CONFIRMED，8 条已修于 324159a）
- 性质：记档不阻断，均为有意决策或低危清理项

1. **SSE 多行 `data:` 拼接未实现**（producthunt_search.py `_parse_response_body`）：按 SSE 规范单事件多 data: 行应聚合后再解析；当前仅支持单行。当前端点实测为单行（B1 fixture 即真实响应形态），多行属上游改版风险——方案风险条款 2 已接受此类破坏（L1 fixture 测试最先暴露，修复面限单脚本），按极简原则不预兼容。
2. **清理类候选**（评审自认严重度低，避免顺手改动的连锁）：`_normalize_entry` 死透传包装；`[DONE]` 特判行为死分支；`test_rpc_payload_is_tools_call` 复制 run_cli 脚手架；SEARCH_MIGRATION v0.7.0 节与 query 节点、sn-search-producthunt SKILL.md 三处使用边界指引近逐字重复（可发现性设计，包络 JSON 单一出处的硬约束未破坏）。
3. **frontmatter description 版本史追加句**：兄弟技能无此惯例，但为 deep-research 既有惯例（v0.5.0/0.6.0/0.6.1 均追加）且系方案明确要求，本次不视为偏差；后续版本可考虑停止追加。
