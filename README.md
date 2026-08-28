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

## 三个 Skill

- `optimization-plan`：需求需要至少两个有依赖关系的批次时，编写并定级方案。
- `implement-plan`：执行一份已有 T0–T3 定级的分批方案。
- `plan-iterate`：独立评审与迭代方案文档；不用于代码 diff review。

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

真实 Codex 方案评审只在已登录环境且用户明确授权后执行。

## 角色模型路由

Claude Code 保留插件内的静态分级：Executor 使用 Sonnet，Auditor 与 Advisor 使用 Opus。Codex 使用原生新上下文代理，在创建代理时按角色选择 Codex 模型与推理档位；默认建议 Executor 侧重延迟与成本，Auditor/Advisor 侧重能力。两种宿主的模型标识彼此独立。
