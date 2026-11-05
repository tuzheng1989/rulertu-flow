/** plan-iterate 单轮评审结果摘要（源自 review-RN.json） */
export type ReviewRound = {
  round: number
  score: number
  p0: number
  p1: number
  p2: number
}

/** 一个方案的评审概览（源自 .plan-iterate/<plan名>/ 下的落盘文件） */
export type PlanReview = {
  /** 方案名（.plan-iterate 下的目录名） */
  name: string
  /** .plan-iterate/<plan名> 的路径（相对会话工作目录） */
  dir: string
  /** 方案文档路径（state.json 的 plan_path 原文，可为绝对路径）；缺失则面板不可点击跳转 */
  docPath?: string
  /** 评审后端（state.json 的 backend 字段） */
  backend?: string
  /** 当前轮次（state.json 的 round 字段，缺失时取最新评审轮） */
  round: number
  /** 已落盘的各轮评审，按轮次升序 */
  rounds: ReviewRound[]
  /** 最新轮是否达标（score >= 8.5 且无 P0/P1） */
  passed: boolean
}

/** $.agent.list() 的展示字段；manifest 类型契约必须自包含 */
export type SubagentInfo = {
  id: string
  description: string
  type: string
  status: string
  parentId?: string
  spawnedBy?: string
  name?: string
}

/** 宿主当前会话的子代理清单及读取状态 */
export type AgentSnapshot = {
  agents: SubagentInfo[]
  loaded: boolean
  /** 查询失败时保留上次清单；面板需提示状态可能已过期 */
  error: boolean
}

/** 当前会话任务，与历史评审及执行记录分开保存 */
export type FlowTask = {
  kind: 'iterate' | 'implement'
  plan: string
  batch?: string
}

/** 全绿收口的战报统计（组装与解析同一契约）：files 为声明边界数（必填，缺失/非法整个 closure 丢弃）；
 *  added/removed/minutes 为 number | null 且缺省与 null 等价——null = 统计不可用/无首报起点，
 *  与真实 0 可区分；statsAt 为统计快照 fetchedAt（ms），仅统计可用时写入、可缺省 */
export type ClosureStats = {
  files: number
  added: number | null
  removed: number | null
  minutes: number | null
  statsAt?: number
}

/** 一条 implement-plan 执行进度上报（源自 flow_report 工具调用） */
export type ExecutionReport = {
  /** 方案名（方案文档文件名去扩展名） */
  plan: string
  /** 批次标识，如 B2 */
  batch: string
  /** 当前阶段：开工 | 派单 | 执行 | 验证 | 收口 */
  phase: string
  /** 风险定级：T0-T3 */
  tLevel?: string
  /** 已通过的定向测试数 */
  testsPassed?: number
  /** 定向测试总数 */
  testsTotal?: number
  /** 证据目录路径 */
  evidenceDir?: string
  /** 全绿收口战报；缺省不出现（非收口或前置校验不过时整个不写） */
  closure?: ClosureStats
  /** 上报时间（ms）；$.store 旧值缺失时为 0 */
  updatedAt: number
}

/** 一个批次的改动边界（源自 flow_batch 工具声明） */
export type BatchScope = {
  /** 方案名 */
  plan: string
  /** 批次标识，如 B2 */
  batch: string
  /** 本批允许改动的文件集合（经路径归一化，相对会话工作目录） */
  files: string[]
}

/** 一个批次的依赖节点（源自 flow_deps 工具声明） */
export type BatchDep = {
  /** 批次标识，如 B2 */
  batch: string
  /** 依赖的前置批次标识列表 */
  dependsOn: string[]
}

/** 一个方案的波次依赖图（按推荐执行顺序排列） */
export type DepGraph = {
  /** 方案名 */
  plan: string
  /** 批次依赖节点，按推荐执行顺序 */
  batches: BatchDep[]
}

/** 一个 git 文件的更改状态（源自 git status --porcelain 的 XY 码） */
export type GitFileState = {
  /** 原始 XY 码，如 ' M'、'M '、'??'、'UU' */
  code: string
  /** 文件路径（rename 为新路径） */
  path: string
  /** rename 原路径 */
  oldPath?: string
}

/** 一次 git 仓库状态快照（源自 status --porcelain=v1 -b 与 diff --numstat） */
export type GitStatus = {
  /** 当前分支名；detached HEAD 时为 'HEAD*' */
  branch: string
  /** 上游分支名；未设置或 unborn 时为 null */
  upstream: string | null
  /** 领先上游的提交数 */
  ahead: number
  /** 落后上游的提交数 */
  behind: number
  /** 已暂存的文件（X ∈ M/A/D/R/C 且非冲突） */
  staged: GitFileState[]
  /** 未暂存的改动文件（Y ∈ M/D 且非冲突） */
  unstaged: GitFileState[]
  /** 未跟踪的文件（??） */
  untracked: GitFileState[]
  /** 合并冲突文件（UU/AA/DD/AU/UA/DU/UD），最优先展示 */
  conflicts: GitFileState[]
  /** 行级新增合计（tracked 改动，untracked 不计） */
  added: number
  /** 行级删除合计 */
  removed: number
  /** 快照时间（ms） */
  fetchedAt: number
  /** numstat 逐文件行级增删（键为归一化小写路径，rename 取目标路径，值 [added, removed]） */
  byPath?: Record<string, [number, number]>
  /** 两侧 numstat 查询状态：ok 发起且成功；skipped 该侧无 tracked 改动未查询；failed 本应查询但失败 */
  numstatSides?: { worktree: 'ok' | 'skipped' | 'failed'; cached: 'ok' | 'skipped' | 'failed' }
}

/** $.fs.list() 的展示字段子集（文件树面板） */
export type FsEntryLike = {
  name: string
  kind: string
  isLink: boolean
}

declare module 'claude-code' {
  interface PluginState {
    'flow-deck': {
      /** 最近一次扫描发现的所有方案评审概览 */
      plans: PlanReview[]
      /** 已通知过的 plan+轮次组合键（<dir>#R<n>），防止重复 toast */
      notified: string[]
      /** 首次扫描已把存量评审静默标记为已通知 */
      baselined: boolean
      /** 当前会话正在进行的任务；历史文件、依赖声明不会激活任务 */
      currentTask: FlowTask | null
      /** 本会话最近一次执行上报；无则 null */
      execution: ExecutionReport | null
      /** 当前批次改动边界；未声明则 null（守卫放行） */
      batchScope: BatchScope | null
      /** 已越界提醒过的归一化路径键，同批同文件不重复告警；批次重声明或新会话时清空 */
      guardWarned: string[]
      /** 各批次最新阶段，键 <plan>#<batch>，flow_report 逐批累积 */
      progress: Record<string, string>
      /** 当前方案的波次依赖图；未声明则 null */
      deps: DepGraph | null
      /** 最近一次 git 仓库状态快照；非 git 仓库或尚未取数则 null */
      git: GitStatus | null
      /** 宿主当前会话的子代理状态，仅打开面板时查询 */
      agents: AgentSnapshot
      /** GitHub 仓库 open issue 清单（gh issue list 拉取，60s 独立轮询）；未取数 loaded=false，
       *  拉取失败 error=true（区块静默不绘制，D13）；失败后下一轮询可自愈回正常态 */
      ghIssues: { issues: { number: number; title: string; url: string; labels: string[] }[]; loaded: boolean; error: boolean }
      /** 跨会话恢复的上次执行摘要（源自 $.store），空态面板的面包屑；无则 null */
      lastRun: ExecutionReport | null
      /** 全绿收口通关卡（方案+批次+战报统计）；非收口/任务切换/新边界声明时清空，无则 null */
      closureCard: { plan: string; batch: string; closure: ClosureStats } | null
      /** 执行停滞提示：距上次上报的分钟数（超过阈值）；未停滞或无执行则 null */
      stall: number | null
      /** 文档浏览面板装载的文档；text 为 null 表示读取失败（error 记原因）；kind 缺省 'file' 全文，'diff' 为未提交变更对比 */
      doc: { path: string; text: string | null; error?: string; kind?: 'file' | 'diff' } | null
      /** 文档浏览面板当前选中节在 parseSections 结果中的下标 */
      docSection: number
      /** 文档浏览模式：all 全文阅读（默认），section 单节浏览（修改请求锚定） */
      docMode: 'all' | 'section'
      /** 文件树面板当前浏览目录（相对会话工作目录）；null 表示根 */
      treeDir: string | null
      /** 文件树面板最近一次目录列表；loaded 表示已取数（含空目录） */
      treeEntries: { entries: FsEntryLike[]; loaded: boolean } | null
      /** 本会话 Edit/Write 改动记录（去重保序，上限 50，最新在末尾） */
      touched: { path: string; at: number }[]
      /** deck 面板当前页签；/deck 无参打开时保持上次所在页签 */
      activeTab: 'flow' | 'files' | 'doc'
      /** 呼吸节拍帧（0|1）：beatTimer 每 800ms 翻转、仅 deck 面板可见时写入。帧三红线 1——
       *  帧状态只写本专用键，禁止写入其余任何 PluginState 键（否则击穿 git 快照时间戳防抖） */
      beat: 0 | 1
    }
  }
}
