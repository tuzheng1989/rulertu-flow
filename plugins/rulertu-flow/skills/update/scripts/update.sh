#!/usr/bin/env bash
# update.sh — 一键更新本机 Claude Code 工具链的外部组件
#
# 注意：Claude Code 本体（claude update）不在本技能范围内——它无法在运行中
#       自我更新（会话内进程无法替换自身）。如需升级本体，请退出会话后手动
#       `claude update`。
#
# 覆盖 6 类更新：
#   1. 所有 marketplaces       : claude plugin marketplace update
#   2. 已安装 plugins          : 逐个 claude plugin update <id> --scope <scope>
#                                （CLI 无原生 update-all；必须按每个插件的实际 scope 调用，
#                                 否则默认 user scope 会报 "Plugin not found"）
#   3. openwiki (npm 全局)     : npm install -g openwiki@latest
#   4. codegraph (npm 全局)    : npm install -g @colbymchenry/codegraph@latest
#   5. open-code-review(npm)   : npm install -g @alibaba-group/open-code-review@latest
#                                （CLI 命令为 ocr；纯 CLI 非常驻 MCP，无文件锁问题）
#   6. deepeval (pip + skills) : pip install --upgrade deepeval
#                                + npx skills update deepeval（skill 本体走 skills CLI）
#
# 未安装组件的安装闸门：
#   npm/pip 组件的「更新」命令对未安装的包会直接装上。默认对未安装组件跳过并
#   给出安装命令；仅当组件名出现在 UPDATE_INSTALL（逗号分隔，如
#   UPDATE_INSTALL=openwiki,codegraph,ocr,deepeval）时才允许新装，
#   汇总中标注「新装」。是否勾选由 SKILL.md 的步骤 0（询问用户）决定。
#
# 代理预检：
#   marketplace/plugins 走 github，npm 包走 npm registry；本机多半直连可用，
#   但受限网络（如 github 间歇性拦截）需代理。启动时先探测：可达(直连或经代理)→继续；
#   不可达且无代理 → 提示启动代理并退出。设 UPDATE_NO_PROXY_GATE=1 可跳过预检。
#
# 设计原则：单步失败不中断整体流程；每步采集「前→后」版本；结尾输出汇总表。
#
# 注意事项（已实测）：
#   - codegraph CLI *没有* `upgrade` 子命令（报 unknown command 'upgrade'），
#     它是 npm 全局包 @colbymchenry/codegraph，更新走 npm。
#   - plugins 更新仅「暂存」新版本，需重启 Claude Code 才生效。
#   - codegraph 更新后，若其 MCP server 已在运行，可能需重跑 `codegraph install`。

set -o pipefail

# 脚本自身位置：所有路径均相对技能目录解析，不写死安装位置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------- 颜色与输出 ----------
RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; CYAN=$'\033[36m'; BOLD=$'\033[1m'; RESET=$'\033[0m'
section() { echo ""; echo "${BOLD}${CYAN}### [$1] $2${RESET}"; }
info()    { echo "  $1"; }
good()    { echo "  ${GREEN}✅ $1${RESET}"; }
bad()     { echo "  ${RED}❌ $1${RESET}"; [ -n "$2" ] && printf '%s\n' "$2" | tail -8 | sed 's/^/      /'; }
warn()    { echo "  ${YELLOW}⚠️  $1${RESET}"; }

declare -a SUMMARY=()
sum_ok()   { SUMMARY+=("${GREEN}✅${RESET} $1"); }
sum_fail() { SUMMARY+=("${RED}❌${RESET} $1"); }
sum_skip() { SUMMARY+=("${YELLOW}⏭️ ${RESET} $1"); }

# ---------- 版本采集 ----------
npm_ver() {
  npm list -g "$1" --depth=0 --json 2>/dev/null \
    | python -c "import sys,json;d=json.load(sys.stdin);print(d['dependencies']['$1']['version'])" 2>/dev/null
}
codegraph_ver() { codegraph --version 2>/dev/null | head -1; }
# deepeval 版本从 pip 元数据取（CLI 未上 PATH 时也能采集）
deepeval_ver() { python -m pip show deepeval 2>/dev/null | sed -n 's/^Version: //p'; }

# ---------- 未安装组件的安装闸门 ----------
# 仅当组件名出现在 UPDATE_INSTALL（逗号分隔）中，未安装的组件才允许新装；
# 否则跳过并在汇总中给出手动安装命令。由 SKILL.md 步骤 0 询问用户后传入。
want_install() {
  case ",${UPDATE_INSTALL:-}," in *",$1,"*) return 0 ;; esac
  return 1
}
# 汇总用「前→后」描述：before 为空即本次新装
delta_label() {
  if [ -z "$1" ]; then printf '🆕 新装 %s' "${2:-?}"; else printf '%s → %s' "$1" "${2:-?}"; fi
}

# ---------- 0. 代理预检 ----------
# 技能在脚本内 export *_PROXY，子进程（npm/curl）自动继承，
# 用户无需在 shell 里手动设置；代理端口靠自动探测或一次性配置文件解决。
# proxy.env 与 SKILL.md 同目录（跟随技能安装位置，自动生成）
PROXY_CONF="$SCRIPT_DIR/../proxy.env"

# 在脚本进程内套用代理（export 后所有子进程继承）
apply_proxy() {
  [ -z "$1" ] && return
  export HTTPS_PROXY="$1" https_proxy="$1" HTTP_PROXY="$1" http_proxy="$1"
  export ALL_PROXY="$1" all_proxy="$1"
}

# 解析已知代理，优先级：现有 env > UPDATE_PROXY > 持久配置文件 proxy.env
resolve_proxy() {
  local p="${HTTPS_PROXY:-${https_proxy:-${ALL_PROXY:-${all_proxy:-${HTTP_PROXY:-$http_proxy}}}}}"
  [ -n "$p" ] && { echo "$p"; return; }
  [ -n "${UPDATE_PROXY:-}" ] && { echo "$UPDATE_PROXY"; return; }
  if [ -f "$PROXY_CONF" ]; then
    # source 用户自己的配置文件（仅含 HTTPS_PROXY=... 一行）
    # shellcheck source=/dev/null
    source "$PROXY_CONF" 2>/dev/null
    echo "${HTTPS_PROXY:-}"
  fi
}

# 探测本地常见代理端口（Clash/V2RayN/Clash Verge 等的默认 HTTP 代理口）
probe_proxy() {
  local ports="7890 7897 10809 1080 2080 8080 1087 33210 20171"
  for p in $ports; do
    local cand="http://127.0.0.1:$p" code
    code=$(curl -sS --max-time 4 -x "$cand" -o /dev/null -w '%{http_code}' \
            https://github.com/ 2>/dev/null || true)
    if [ -n "$code" ] && [ "$code" != "000" ]; then
      echo "$cand"; return 0
    fi
  done
  return 1
}

# github.com 是否可达（marketplace/plugins 的来源；curl 自动走已 export 的代理）
reach_github() {
  local code
  code=$(curl -sS --max-time 12 -o /dev/null -w '%{http_code}' \
          https://github.com/ 2>/dev/null || true)
  [ -n "$code" ] && [ "$code" != "000" ]
}

preflight_proxy() {
  section "0/6" "代理与连通性预检"
  if [ "${UPDATE_NO_PROXY_GATE:-0}" = "1" ]; then
    warn "已设 UPDATE_NO_PROXY_GATE=1，跳过代理预检（受限网络下 marketplace/plugins 可能失败）"
    return 0
  fi

  # 1. 套用已知代理（env > UPDATE_PROXY > proxy.env）
  local known
  known=$(resolve_proxy)
  if [ -n "$known" ]; then
    apply_proxy "$known"
    good "套用代理: $known"
  else
    info "未配置代理，先试直连…"
  fi

  # 2. 测可达（已 export 的代理 curl 会自动走）
  if reach_github; then
    good "github.com 可达（marketplace/plugins 来源），开始更新"
    return 0
  fi

  # 3. 直连/已知代理都不通 → 自动探测本地常见代理端口
  warn "直连/已知代理不可达，探测本地常见代理端口（7890/7897/10809/…）…"
  local found
  if found=$(probe_proxy); then
    apply_proxy "$found"
    good "自动探测到可用代理: $found"
    # 持久化，下次免探测
    { echo "# 由 update 技能自动写入；删掉本文件即可重新探测"; echo "HTTPS_PROXY=$found"; } > "$PROXY_CONF"
    info "已记住到 $PROXY_CONF，下次直接复用"
    return 0
  fi

  # 4. 全部失败
  bad "未找到可用代理，github.com 不可达"
  echo ""
  echo "${BOLD}${YELLOW}👉 请启动本地代理（Clash/V2Ray 等）后重跑 /update，脚本会自动探测端口并记住。${RESET}"
  echo "  ${YELLOW}或手动指定一次：UPDATE_PROXY=http://127.0.0.1:7890 bash \"$SCRIPT_DIR/update.sh\"${RESET}"
  echo "  ${YELLOW}（npm 组件 openwiki/codegraph/ocr 多走 npm registry，设 UPDATE_NO_PROXY_GATE=1 可跳过预检让其照跑）${RESET}"
  echo ""
  echo "${BOLD}================================================${RESET}"
  return 1
}

# ---------- 1. 所有 marketplaces ----------
update_marketplaces() {
  section "1/6" "所有 marketplaces"
  local count err
  count=$(claude plugin marketplace list 2>/dev/null | grep -c '❯' || true)
  info "已配置市场数: ${count:-?}"
  if err=$(claude plugin marketplace update 2>&1); then
    good "全部市场已更新"
    sum_ok "Marketplaces ×${count:-?} 已更新"
  else
    bad "marketplace update 失败" "$err"
    sum_fail "Marketplaces 更新失败"
  fi
}

# ---------- 2. 已安装 plugins（按 scope 逐个） ----------
update_plugins() {
  section "2/6" "已安装 plugins（按 scope 逐个）"
  local rows err
  # 同时取 id 与 scope（scope 不传会默认 user → Plugin not found）
  # 注意：Windows 上 Python stdout 是文本模式，会把 \n 翻译成 \r\n，
  #       污染行尾的 scope 字段（变成 "local\r"），导致 --scope 校验失败。
  #       故末尾接 tr -d '\r' 去掉回车。
  if ! rows=$(claude plugin list --json 2>/dev/null \
        | python -c "import sys,json
for p in json.load(sys.stdin):
    print(p['id']+'\t'+p.get('scope','user'))" 2>/dev/null | tr -d '\r'); then
    bad "无法解析 claude plugin list --json"
    sum_fail "Plugins 列表解析失败"
    return
  fi

  local total okn failn
  total=$(printf '%s\n' "$rows" | grep -c . || true)
  [ -z "$rows" ] && { warn "无已安装插件"; sum_skip "Plugins（无）"; return; }
  info "待更新插件数: $total"

  okn=0; failn=0
  while IFS=$'\t' read -r id scope; do
    [ -z "$id" ] && continue
    local out
    if out=$(claude plugin update "$id" --scope "$scope" 2>&1); then
      # 从输出里抽 "updated from X to Y"；抽不到就显示原行首
      local delta
      delta=$(printf '%s' "$out" | grep -oiE 'updated from [^ ]+ to [^ ]+（[需重启]*）?' \
              | sed -E 's/updated from /前:/; s/ to / → 后:/I' | head -1)
      if [ -n "$delta" ]; then
        good "$id [$scope]：$delta（重启后生效）"
      else
        good "$id [$scope]：已是最新或已暂存（重启后生效）"
      fi
      okn=$((okn+1))
    else
      bad "$id [$scope] 更新失败" "$out"
      failn=$((failn+1))
    fi
  done <<< "$rows"

  warn "plugins 更新需重启 Claude Code 才生效（CLI: restart required to apply）"
  if [ "$failn" -gt 0 ]; then
    sum_ok "Plugins: $okn 成功 / $failn 失败（共 $total，重启后生效）"
  else
    sum_ok "Plugins: $okn 成功（共 $total，重启后生效）"
  fi
}

# ---------- 3. openwiki (npm) ----------
update_openwiki() {
  section "3/6" "openwiki (npm 全局包)"
  local before after err
  before=$(npm_ver openwiki)
  if [ -z "$before" ] && ! want_install openwiki; then
    warn "未安装且未勾选安装，跳过（手动安装：npm install -g openwiki@latest）"
    sum_skip "openwiki（未安装，未跑安装）"
    return
  fi
  info "更新前: ${before:-未安装}"
  if err=$(npm install -g openwiki@latest 2>&1); then
    after=$(npm_ver openwiki)
    good "更新后: ${after:-未知}  ( $(delta_label "$before" "$after") )"
    sum_ok "openwiki: $(delta_label "$before" "$after")"
  else
    bad "npm install openwiki 失败" "$err"
    sum_fail "openwiki 更新失败"
  fi
}

# 释放 codegraph 二进制文件锁：精确杀掉占用 node.exe 的 codegraph 进程。
# 为何这么做：codegraph MCP server 运行时持有 node.exe，npm 无法替换（EBUSY）。
#   - claude mcp 无 disable/enable 子命令，改配置也不会杀正在运行的进程；
#   - 按 ExecutablePath 含 'codegraph' 精确匹配，不误伤其他 node.exe；
#   - codegraph 自带 watchdog（卡死自重启），被杀重启是其设计的正常路径。
# 授权：用户已明确同意在更新 codegraph 时终止这些进程。
kill_codegraph_procs() {
  local pids
  pids=$(powershell.exe -NoProfile -Command "
    Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" |
      Where-Object { \$_.ExecutablePath -like '*codegraph*' } |
      ForEach-Object { \$_.ProcessId }
  " 2>/dev/null | tr -d '\r ' | grep -E '^[0-9]+$')
  [ -z "$pids" ] && return 0
  info "检测到占用二进制的 codegraph 进程，先终止以释放文件锁: $(echo $pids | tr '\n' ' ')"
  powershell.exe -NoProfile -Command "
    Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" |
      Where-Object { \$_.ExecutablePath -like '*codegraph*' } |
      ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }
  " >/dev/null 2>&1
  sleep 1   # 留时间给 Windows 释放文件句柄
}

# ---------- 4. codegraph (npm) ----------
update_codegraph() {
  section "4/6" "codegraph (npm 全局包 @colbymchenry/codegraph)"
  local before after err
  before=$(codegraph_ver)
  if [ -z "$before" ] && ! want_install codegraph; then
    warn "未安装且未勾选安装，跳过（手动安装：npm install -g @colbymchenry/codegraph@latest）"
    sum_skip "codegraph（未安装，未跑安装）"
    return
  fi
  info "更新前: ${before:-未知}"
  kill_codegraph_procs   # 释放可能被 codegraph MCP server 占用的二进制文件锁
  if err=$(npm install -g @colbymchenry/codegraph@latest 2>&1); then
    after=$(codegraph_ver)
    good "更新后: ${after:-未知}  ( $(delta_label "$before" "$after") )"
    warn "codegraph MCP 进程已在本步终止以释放文件锁；配置未改，重启 Claude Code 会话即自动恢复。"
    sum_ok "codegraph: $(delta_label "$before" "$after")"
  else
    bad "npm install codegraph 失败" "$err"
    # EBUSY/locked：codegraph MCP server 正运行时其二进制被占用，npm 无法替换
    if printf '%s' "$err" | grep -qi 'EBUSY\|resource busy or locked'; then
      warn "codegraph 二进制被占用（codegraph MCP server 正在运行）。请在『未加载 codegraph MCP 的会话』中重跑 /update，或先用 /mcp 停用 codegraph 再更新。"
      sum_fail "codegraph 更新失败（二进制被 MCP 占用，换会话重跑）"
    else
      sum_fail "codegraph 更新失败"
    fi
  fi
}

# ---------- 5. open-code-review (npm) ----------
update_ocr() {
  section "5/6" "open-code-review (npm 全局包 @alibaba-group/open-code-review)"
  local before after err
  before=$(npm_ver @alibaba-group/open-code-review)
  if [ -z "$before" ] && ! want_install ocr; then
    warn "未安装且未勾选安装，跳过（手动安装：npm install -g @alibaba-group/open-code-review@latest）"
    sum_skip "open-code-review（未安装，未跑安装）"
    return
  fi
  info "更新前: ${before:-未安装}"
  if err=$(npm install -g @alibaba-group/open-code-review@latest 2>&1); then
    after=$(npm_ver @alibaba-group/open-code-review)
    good "更新后: ${after:-未知}  ( $(delta_label "$before" "$after") )"
    sum_ok "open-code-review(ocr): $(delta_label "$before" "$after")"
  else
    bad "npm install @alibaba-group/open-code-review 失败" "$err"
    sum_fail "open-code-review 更新失败"
  fi
}

# ---------- 6. deepeval (pip 包 + skills CLI 管理的 skill 本体) ----------
# deepeval 有两层：pip 包（CLI 与 SDK）和 skill 文档本体（由 npx skills 管理），
# 分别更新、分别汇总；pip 走 PyPI，npx 走 npm registry，均继承已 export 的代理。
update_deepeval() {
  section "6/6" "deepeval (pip 包 + npx skills 管理的 skill)"
  local before after err

  # 6a. Python 包
  before=$(deepeval_ver)
  if [ -z "$before" ] && ! want_install deepeval; then
    warn "未安装且未勾选安装，跳过（手动安装：python -m pip install --upgrade deepeval）"
    sum_skip "deepeval（未安装，未跑安装）"
    return
  fi
  info "更新前(pip): ${before:-未安装}"
  if err=$(python -m pip install --upgrade deepeval 2>&1); then
    after=$(deepeval_ver)
    good "更新后(pip): ${after:-未知}  ( $(delta_label "$before" "$after") )"
    sum_ok "deepeval(pip): $(delta_label "$before" "$after")"
  else
    bad "pip install --upgrade deepeval 失败" "$err"
    sum_fail "deepeval(pip) 更新失败"
  fi

  # 6b. skill 本体（-y 免 npx 首次安装确认）
  if err=$(npx -y skills update deepeval 2>&1); then
    good "skill 本体: npx skills update 完成"
    # 顺带列出 skill 当前版本行（无输出不算失败，仅展示）
    local skill_line
    skill_line=$(npx -y skills ls 2>/dev/null | grep -i deepeval | head -2)
    [ -n "$skill_line" ] && printf '%s\n' "$skill_line" | sed 's/^/      /'
    sum_ok "deepeval(skill): npx skills update 完成"
  else
    bad "npx skills update deepeval 失败" "$err"
    sum_fail "deepeval(skill) 更新失败"
  fi
}

# ---------- 主流程 ----------
echo "${BOLD}================================================${RESET}"
echo "${BOLD} Claude Code 工具链外部组件一键更新${RESET}"
echo "${BOLD} （本体 claude update 不在内：无法在运行中自我更新）${RESET}"
echo "${BOLD}================================================${RESET}"

# 代理预检（不可用则提示并退出，不继续）
if ! preflight_proxy; then
  exit 1
fi

update_marketplaces
update_plugins
update_openwiki
update_codegraph
update_ocr
update_deepeval

# ---------- 汇总表 ----------
echo ""
echo "${BOLD}${CYAN}==================== 汇总 ====================${RESET}"
for line in "${SUMMARY[@]}"; do
  echo "  - $line"
done
echo ""
warn "收尾提示：plugins 更新需重启 Claude Code 生效；codegraph 进程已被终止释放文件锁，重启会话即自动恢复。"
echo "${BOLD}================================================${RESET}"
