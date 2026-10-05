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
  /** 评审后端（state.json 的 backend 字段） */
  backend?: string
  /** 当前轮次（state.json 的 round 字段，缺失时取最新评审轮） */
  round: number
  /** 已落盘的各轮评审，按轮次升序 */
  rounds: ReviewRound[]
  /** 最新轮是否达标（score >= 8.5 且无 P0/P1） */
  passed: boolean
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
      /** 本会话最近一次执行上报；无则 null */
      execution: ExecutionReport | null
      /** 当前批次改动边界；未声明则 null（守卫放行） */
      batchScope: BatchScope | null
      /** 各批次最新阶段，键 <plan>#<batch>，flow_report 逐批累积 */
      progress: Record<string, string>
      /** 当前方案的波次依赖图；未声明则 null */
      deps: DepGraph | null
      /** 最近一次 git 仓库状态快照；非 git 仓库或尚未取数则 null */
      git: GitStatus | null
    }
  }
}
