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

declare module 'claude-code' {
  interface PluginState {
    'flow-deck': {
      /** 最近一次扫描发现的所有方案评审概览 */
      plans: PlanReview[]
      /** 已通知过的 plan+轮次组合键（<dir>#R<n>），防止重复 toast */
      notified: string[]
      /** 首次扫描已把存量评审静默标记为已通知 */
      baselined: boolean
    }
  }
}
