# Quickstart — 安装、CLI 与最小闭环

> 版本锚点：rhetra 0.1.0（2026-09）。源码 `D:/runspace/rhetra-harness/`。

## 安装来源与导入（导入方必读）

**rhetra 未发布 PyPI**。当前唯一的分发渠道是 GitHub 仓库
`tuzheng1989/rhetra-harness`（或本机源码路径）。无论哪种渠道，导入方代码统一写：

```python
from rhetra import run_flow, serve, load_flow  # 包名恒为 rhetra
```

### 渠道 1：git 安装（消费方正式接入）

```bash
# base（仅 offline 模式可用）
pip install git+https://github.com/tuzheng1989/rhetra-harness.git

# 需要 mode="auto"（真实模型栈）时装 extras
pip install "rhetra[live] @ git+https://github.com/tuzheng1989/rhetra-harness.git"

# 锁定到指定 commit（消费方推荐，保证可复现）
pip install "rhetra[live] @ git+https://github.com/tuzheng1989/rhetra-harness.git@a317592"
```

- extras `live` = `openai` + `langchain-openai` + `httpx`（真实 adapter 的全部重依赖）。
- base 安装下 `mode="auto"` 会 fail closed：`ImportError` 提示装 `rhetra[live]` 或改 offline。
- 重依赖纪律：`rhetra.api` 顶层零 openai/langchain 导入，真实栈在 `mode="auto"`
  分支内惰性装配——base 消费方不会被动拉入重依赖。

### 渠道 2：本地路径（同机开发联调）

```bash
pip install D:/runspace/rhetra-harness                 # 常规安装（拷贝快照）
pip install -e D:/runspace/rhetra-harness              # editable：源码改动即时生效
pip install -e "D:/runspace/rhetra-harness[live]"      # editable + 真实栈
```

EvoMAV（`D:/runspace/deepchat`）等本机消费者联调时用 editable 最省事；
交付前切换到 git 渠道锁定 commit。

### 环境要求

- Python **>= 3.12**（`pyproject.toml` 硬约束）。
- 运行时强依赖：`langgraph==1.2.7`（执行内核编译驱动，版本钉死）、`pydantic`、
  `jsonschema`、`PyYAML`、`rfc8785`（hash 规范化）。
- 与宿主项目依赖冲突时优先保 langgraph 钉死版本——这是执行内核的强身份要求。

### 导入面注意

- `from rhetra import plan_flow, PlannerError` 走 PEP 562 惰性解析（访问时才
  import `rhetra.planner`）；不用 planner 的进程零 planner 导入开销。
- `__all__`（24 符号）即 0.x 兼容承诺，别从子模块（`rhetra.api`、`rhetra.planner`
  除外）deep import。

## 最小 Python 闭环

```python
from rhetra import run_flow

result = run_flow(
    "cases/civil-rescue/flow.yaml",            # 路径 | YAML/JSON 源文本 | FlowDefinitionV1
    input="cases/civil-rescue/input-full.json",  # 路径 | dict（必传）
    resources="cases/civil-rescue/snapshot-offline.json",  # 路径 | dict | ResourceSnapshot
    work_dir="evidence",                        # 证据落盘根，恒落盘不接受 None
    mode="offline",                             # offline=替身通道；真实用法 mode="auto"
)
print(result.status)                # completed / failed / cancelled
print(result.evidence.verify())     # finalized（证据完整封口）
```

Bundle 位于 `<work_dir>/<flow_id>/<flow_version>/<invocation_id>/`。

viewer 一键审计（阻塞，Ctrl-C 退出，仅绑 127.0.0.1）：

```python
from rhetra import serve
serve(work_dir="evidence", port=8765)
```

## CLI 五命令

```bash
rhetra validate cases/civil-rescue/flow.yaml
rhetra freeze  cases/civil-rescue/flow.yaml --input cases/civil-rescue/input-full.json --resources cases/civil-rescue/snapshot-offline.json
rhetra run     cases/civil-rescue/flow.yaml --input cases/civil-rescue/input-full.json --resources cases/civil-rescue/snapshot-offline.json --evidence-root evidence
rhetra import-models <models.json目录> -o snapshot.json          # models.json → 版本化资源快照
rhetra viewer  evidence --port 8765                               # 本地只读证据审查
```

**退出码**：completed=0 / failed=1 / cancelled=2 / internal_failure=3 / 用法错误=64。

秘密通道：CLI 启动时会加载**源码仓库根的 `.env`**（`cli/__init__.py` 按
`parents[2]` 定位，仅存在时加载；值只进 `os.environ`，绝不打印——pip 安装态
该路径基本不生效，凭据走进程环境变量即可）。`mode="auto"` 的 API key 从环境
变量解析，缺失即 fail closed。

## 异常面（A2：准入失败异常外显）

以下异常从 `run_flow` 直接抛出，**不包装为 RunResult**（准入失败没有 Invocation，
无证据可持）：

| 异常 | 含义 |
|------|------|
| `UsageError` | 调用方用法错误（参数形状/取值，CLI 映射退出码 64） |
| `SpecErrorList` | flow 定义不合法（schema/结构错误） |
| `PreflightError` | preflight 冻结失败（选择器解析、契约冲突等） |
| `PlannerError` | 仅 `task` 形态：选模失败 / 装配失败 / 重试耗尽 |
| 装配 `ValueError` / `SecretResolutionError` | 真实栈装配或凭据解析失败 |
| `OSError` | 证据持久化失败（CLI → 退出码 3） |

## 可复制样例

`D:/runspace/rhetra-harness/examples/`（头部 docstring 载明前置与运行方式）：

| 脚本 | 演示 |
|------|------|
| `civil_rescue_explicit.py` | 显式 flow 路径 offline 全链 |
| `civil_rescue_planner.py` | planner 语法糖路径（task → Draft → run） |
| `doc_editor.py` | 通用性冒烟：step_output 线程链 + fork 并行变体 |
| `large_artifact.py` | tool 步 >64KiB 大产物溢出与恢复 |
| `save_and_reload.py` | save_flow 三态版本 + 采纳草案复用 |
