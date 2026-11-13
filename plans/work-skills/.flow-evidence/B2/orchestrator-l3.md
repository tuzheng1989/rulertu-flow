# B2 主控验证记录（抽查 + L3 链路演练）

- 日期：2026-11-10
- 主控抽查与演练均在 Executor 停止写入后执行。

## 主控抽查（Auditor 可采信项）

1. **红线回归复跑**：`cd plugins/work-skills/skills/deep-research && PYTHONIOENCODING=utf-8 python scripts/test_state_manager.py` → `测试结果: 31/31 通过`，退出码 0。与 Executor 回报一致。
2. **差异核验**：`git diff --stat` 6 文件 +40/−8，加法式为主；SKILL.md 与 research-node-query.md 完整 diff 逐处人工核对，与方案 B2 节 5 处锚点一一对应（映射表行、子工具选择、normalize、实现说明表、降级枚举 L408、prose 6 通道、query 节点 schema L25/字段说明 L38/选择指南表/选择原则两句），无越界改动。`--name` 参数形态、`--limit` 上限 8、`source_tier: secondary`、榜单偏置声明均与 B1 实测契约一致。
3. **版本三处**：CHANGELOG Unreleased 顶部 `work-skills 2.4.0` / `.claude-plugin/plugin.json` 2.4.0 / `.codex-plugin/plugin.json` 2.4.0 / SKILL.md frontmatter `version: 0.7.0`，四点一致。

## L3 链路演练（方案验收 1、2 条）

### 演练一：product query 分派 → 脚本调用 → normalize（验收 1）

- 查询「AI notetaker 竞品对比」按新选择指南（research-node-query.md 选择指南表 product 行）标注 `source_type: product`；按映射表子工具选择（竞品对比 → `semantic`）实调：

  ```
  cd plugins/work-skills/skills/deep-research
  PYTHONIOENCODING=utf-8 python ../sn-search-producthunt/scripts/producthunt_search.py semantic "AI notetaker competitor comparison" --limit 8
  ```

- 结果：`success:true`，items 8 条，**8/8 含 `source_type:"product"`**（验收线 ≥3，PASS），首条 `{title: Reflect, slug: reflect-notes}`，items 含 `funding` 字段（融资数据增量价值实证）。

### 演练二：失败信号触发（验收 2）

- 命令：同目录 `... producthunt_search.py leaderboard`（缺必填 `--date`）。
- 结果：argparse 拦截，stderr 输出 usage + `error: the following arguments are required: --date`，**退出码 2**，无 JSON。
- 判定：降级规则文字（SKILL.md 3.2「脚本 `success:false`、**报错**、缺依赖」）的「报错」分支覆盖非零退出码形态，触发信号可观测，PASS。`success:false` JSON 形态（网络错误 / JSON-RPC error / 非 2xx → exit 1）由 B1 离线套件 `assert_failure` 断言族覆盖（见 `.flow-evidence/B1/`）。

### 口径限制（如实记录）

本会话未配置 `mcp__web-search-prime` MCP server，「回退 web-search-prime 并 log」的真实调用不可演练。该环节为 prompt 协议行为（deep-research 无降级可执行代码），以两点覆盖：① 触发信号实证（演练二 + B1 失败路径离线断言）；② 降级规则文本一致性（SKILL.md L408 降级枚举已含 product，与 3.2 通用规则形成单一出处）。

## 建议 Auditor 抽查命令

```
cd plugins/work-skills/skills/deep-research && PYTHONIOENCODING=utf-8 python scripts/test_state_manager.py
grep -n "product" plugins/work-skills/skills/deep-research/SKILL.md plugins/work-skills/skills/deep-research/agents/research-node-query.md
grep -n '"version"' plugins/work-skills/.claude-plugin/plugin.json plugins/work-skills/.codex-plugin/plugin.json
```
