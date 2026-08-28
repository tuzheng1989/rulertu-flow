#!/usr/bin/env bash
# codex-review.sh — 发起/续接一次 codex 方案评审，结构化结果落盘
#
# 用法:
#   首轮评审:  codex-review.sh <plan文件路径> <输出json路径>
#   续轮复审:  codex-review.sh <plan文件路径> <输出json路径> <session_id>
#
# 输出:
#   成功: stdout 打印 "SESSION_ID=<uuid>"（复审时与传入一致），评审 JSON 写入 <输出json路径>
#   失败: 非零退出，完整 codex 输出保留在 <输出json路径>.log
#
# 说明:
#   - codex 以 read-only 沙箱运行，能读仓库代码验证方案锚点，不能写任何文件
#   - 非 tty 环境必须 </dev/null，否则 codex 会一直等 stdin
#   - 复审用 `codex exec resume <session_id>`，codex 保留首轮评审全部上下文
set -euo pipefail

plan="$1"
out="$2"
session_id="${3:-}"

[[ -f "$plan" ]] || { echo "ERROR: plan 文件不存在: $plan" >&2; exit 1; }

# 统一转绝对路径（codex 的工作目录取 plan 所在仓库）
plan_abs=$(cd "$(dirname "$plan")" && pwd)/$(basename "$plan")
workdir=$(dirname "$plan_abs")
schema="$(cd "$(dirname "$0")" && pwd)/review-schema.json"
log="${out}.log"

if [[ -n "$session_id" ]]; then
  read -r -d '' PROMPT <<EOF || true
上一轮你评审了方案文档 $plan_abs 并给出了问题清单。作者已按你的评审意见完成修复。

请重新完整阅读该文档（以当前磁盘内容为准，不要依赖你记忆中的旧版本），然后复审：
1. 逐条核对上轮提出的 P0/P1 问题是否真正解决（修复是否到位，还是只改了表面文字）
2. 检查修复过程是否引入了新问题
3. 抽查文档中引用的 文件:行号 锚点与代码事实是否属实
4. 仓库访问边界: 代码与事实仅用于核验方案声明的真伪（失实记 P0）；AGENTS.md、roadmap 等规范性文档不是评审依据——方案面向未来，允许且预期突破现行基线，基线变更只审「是否显式、穿透是否完整」，不审「是否应该变更」，不要因与现行规范冲突而扣分或记 P0/P1。
5. 重新评分并输出与首轮相同格式的 JSON（issues 若已解决则不再列出，只列仍存在或新发现的问题）
EOF
  cmd=(codex exec resume "$session_id" --skip-git-repo-check "$PROMPT")
else
  read -r -d '' PROMPT <<EOF || true
你是资深架构评审。请评审方案文档: $plan_abs

先完整阅读该文档。你拥有当前仓库的只读权限，务必抽查文档中引用的 文件:行号 锚点与代码事实是否属实——锚点造假、指向不存在的代码、或与代码现状矛盾，属于最高优先级问题。

仓库访问边界（重要，先读再评）:
- 代码与事实 → 用: 文档对现有代码的事实性声明（锚点、既有设施、依赖、运行行为），逐一对照代码核验真假，失实记 P0。
- 规范与基线 → 不用: AGENTS.md、roadmap、进度文档等规范性文档不是评审依据。本方案面向未来目标状态，允许且预期突破现行基线（新增能力、修改约束均合法）。涉及基线变更时，只审「变更是否显式、穿透是否完整（解析点/schema/配置/测试同步）」，不审「是否应该变更」——不要因方案与现行规范文档冲突而扣分或记 P0/P1。

评审维度:
1. 整体质量: 结构完整性、逻辑自洽性、可执行性
2. 问题清单: P0(致命: 方案不可行/锚点造假/逻辑矛盾) / P1(严重: 关键缺口/验证方案缺失) / P2(改进: 表述不清/次要优化)
3. 每个问题给出具体可执行的修复建议
4. 分级校验: 若文档为分批实施计划，逐批核查「分级与验证流程」——(a)每批次是否有 T 级定级(T0-T3)及定级依据; (b)该级验证流程是否与定级匹配(如 T1 不派 auditor 由主控机械验证收口、T2 派 auditor 证据包、T3 另加 codex 第二意见)。定级缺失或依据不成立记 P1，流程与定级错配记 P1，边界模糊未就高定级记 P2。非分批计划(无批次结构)跳过本维度。
5. 最终评分: 0-10 分

按 output schema 输出 JSON。issues[].detail 必须引用文档章节标题或锚点位置，让作者能直接定位。
EOF
  cmd=(codex exec -s read-only --skip-git-repo-check "$PROMPT")
fi

# codex 评审可能耗时数分钟（reasoning effort 高时更久），调用方应以后台方式运行本脚本
cd "$workdir"
if "${cmd[@]}" --output-schema "$schema" -o "$out" </dev/null >"$log" 2>&1; then
  # 归一化字段漂移并校验必需字段（见 normalize.py 顶部说明）
  if ! python "$(cd "$(dirname "$0")" && pwd)/normalize.py" "$out"; then
    echo "ERROR: codex 返回的 JSON 缺少必需字段（score/issues 等），原始输出见 $log" >&2
    exit 2
  fi
  sid=$(grep -oE 'session id: [0-9a-f-]{36}' "$log" | head -1 | cut -d' ' -f3)
  [[ -n "$sid" ]] || sid="$session_id"
  echo "SESSION_ID=$sid"
else
  echo "ERROR: codex 调用失败，完整输出见 $log" >&2
  exit 3
fi
