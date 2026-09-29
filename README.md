# Rulertu Flow 2.0

面向 Codex 与 Claude Code 的团队 marketplace 插件，用 T0–T3 风险分级组织方案、实施和独立验证。

## 安装

Codex（不会改动真实配置的试装可设置临时 `CODEX_HOME`）：

```sh
codex plugin marketplace add .
codex plugin add rulertu-flow@rulertu-flow
codex plugin list
```

Claude Code：

```sh
/plugin marketplace add tuzheng1989/rulertu-flow
/plugin install rulertu-flow@rulertu-flow
```

## 选择性与安装范围

marketplace 内四个插件（`rulertu-flow` / `work-skills` / `agent-skills` / `copyright-skills`）互相独立，按需单独安装，同时支持用户全局与项目级两种范围。

Claude Code：安装时用 `--scope` 指定范围——`user`（写入 `~/.claude/settings.json`，所有项目可用，默认）、`project`（写入项目 `.claude/settings.json`，随仓库共享给团队）、`local`（写入 `.claude/settings.local.json`，仅本机本项目）：

```sh
claude plugin install work-skills@rulertu-flow --scope user    # 全局
claude plugin install agent-skills@rulertu-flow --scope project # 项目级共享
```

Codex：marketplace 位置决定可见范围——仓库内 `.agents/plugins/marketplace.json` 随仓库分发（项目级，克隆即得）；把本仓库加到 `~/.agents/plugins/` 则为个人全局。所有条目均为 `policy.installation: "AVAILABLE"` 按需选装，装后可在 `~/.codex/config.toml` 逐插件启停。

## work-skills

17 个工作型技能：深度研究（`deep-research`，多源搜索通道）、战略分析、头脑风暴、费曼教学、灵感节拍器、长文写作、去 AI 味改写（`humanizer`）、书籍转技能（`book-to-skill`）、文档转换（`anydoc-to-md` / `url-to-md` / `md-to-pdf` / `html-to-pdf`）、公司调研，以及 deep-research 依赖的搜索通道（`sn-search-code` / `sn-search-social-cn` / `sn-search-social-en` / `deepxiv`）。

依赖说明：`deep-research` 需要 `web-search-prime` / `web-reader` 两个 MCP server 与 deepxiv CLI（专门通道失败会自动降级到 MCP 搜索）；`url-to-md` 需要 bun，首次使用时在其 `scripts/` 目录执行 `bun install`（node_modules 不随仓库分发）；`md-to-pdf` 需按其 `requirements.txt` 安装并下载 playwright 浏览器；`html-to-pdf` 需本机 Chrome。

## agent-skills

6 个 Agent 工程技能：`ai-agent-design`（《深入理解 AI Agent》知识包统一路由，含百科 / 原文 / 方法 / 案例 / 实践五组件，原书插图不随插件分发）、`agent-evaluator`（Agent 评测 Harness 构建）、`deepagents`（LangChain DeepAgents 使用指南）、`agent-retrieval`（确定性 BM25 + 向量双路 RRF 融合检索库使用指南：接入分层与契约排查）、`deepagents-update`（技能文档与 Python 包同步）、`model-info`（模型参数查询）。

## copyright-skills

5 个知识产权申报技能：`software-copyright-cn`（从代码仓库生成软著申报全套材料——登记表底稿、带图说明书、源代码 docx，附渲染实测与提交前校验）、`copyright-code-review`（提交前源代码合规预审：AI 特征注释、敏感信息、第三方权属、材料一致性，分级问题清单 + 审批修复）、`copy-polisher`（申报文稿与源码注释去 AI 味改稿/检测）、`patent-analysis`（发明专利点挖掘与三性预筛）、`patent-drafting`（专利技术交底书撰写）。

源代码口径（2026-09-08）：提交文档保留注释与空行（中文功能注释是审查要点），行数达标按代码行统计——3,000 行阈值、前/后 1,500 段截取、登记表源程序量全部代码行口径，manifest 双轨可核。支持一份项目按模块真实边界拆多份软著批量申报：`batch_validate.py` 在构建前做唯一归属、每份满 3,000 代码行、条目两两查重三道校验，同代码换名称的批量申报不做。

测试：

```sh
python -m pytest plugins/copyright-skills/tests -q
```

## 三个 Skill

- `optimization-plan`：需求需要至少两个有依赖关系的批次时，编写并定级方案。
- `implement-plan`：执行一份已有 T0–T3 定级的分批方案。
- `plan-iterate`：独立评审与迭代方案文档；不用于代码 diff review。

`plan-iterate` 使用对称的跨模型后端：Claude Code 宿主外调 Codex CLI，Codex 宿主外调 Claude Code `opus/high`。两个方向都使用相同 schema、8.5 分门槛、最多三轮状态机和可续接 session；真实外部调用需要用户明确授权且目标 CLI 已登录。

## 测试职责

Executor 在红绿循环运行锚点测试，子任务收尾运行受影响模块、必要集成测试以及类型和静态检查。Auditor 默认采信主控已抽查的证据，只对一至两条高风险或可疑测试复跑。所有写入任务停止后，波次收口统一运行一次全量测试、构建和项目红线。

修改测试运行器、构建系统、依赖锁文件或全局配置，或者修改跨模块公共契约/共享测试设施且无法建立可信定向范围时，可提前触发全量测试，回报必须记录依据。失败能定位到批次就退回对应 Executor；归属不明则阻断波次并独立诊断。只有绿色基线或独立复现可证明既有失败，flaky 最多定向复跑一次。

## 从 1.x 升级

2.0 将插件从仓库根迁移到 `plugins/rulertu-flow`，属于破坏性安装契约变更。先卸载旧插件和旧 marketplace 条目，拉取 2.0 后重新添加 marketplace、安装插件，并开启新会话刷新 Skill 缓存。旧 plan-iterate 的 `session.txt` 会在下一轮成功评审后迁移为 `state.json`。

## 本地验证

```sh
python scripts/validate_repo.py
python -m unittest discover -s plugins/rulertu-flow/tests -v
```

真实外部方案评审只在目标 CLI 已登录且用户明确授权后执行。

## 角色模型路由

Claude Code 保留插件内的静态分级：Executor 使用 Sonnet，Auditor 与 Advisor 使用 Opus。Codex 使用固定路由：Executor=`gpt-5.6-terra`/`medium`，Auditor=`gpt-5.6-sol`/`high`，Advisor=`gpt-5.6-sol`/`xhigh`。Executor 只继承最近三轮上下文，Auditor/Advisor 使用独立上下文；固定模型不可用时阻断，不静默继承或替换。两种宿主的模型标识彼此独立。
