# LLM 判定编排（Judge 端口族）- agent-retrieval

> 对应库版本：agent-retrieval 0.2.0（2026-11-08，judge 端口 + JevJudge/ChatJudge 收编）。
> 0.x 系列 API 可能调整，使用前核对 `pip show agent-retrieval` 的版本与随包 CHANGELOG。

0.2.0 把判定面从"调用方自写 HTTP"升级为一等组件族：core 层定义端口与消费语义（零依赖），`[judge]` extra 提供两种线协议实现。本篇讲端口族怎么编排、两种实现怎么选、以及判定特有的纪律。

## 端口族总览

```python
from agent_retrieval import (          # core，零依赖，无 extras
    Judge,               # Protocol：judge(query, candidates, *, instruction="") -> Judgment
    JudgedCandidate,     # id/name/description + use_when/avoid_when 五字段声明面
    Judgment,            # probabilities: dict[id, float] + model/latency/tokens 元数据
    select_with_judge,   # 消费 Judgment：argmax + minimum_probability 门槛（弃权返回 None）
)
from agent_retrieval import (          # [judge] extra（requests）
    JevJudge, JevJudgeConfig,      # System One wire 裸 HTTP（不依赖 typesafe-sdk）
    ChatJudge, ChatJudgeConfig,    # 任意 chat completions 端点判定
    JudgeResponseError,            # 判定调用失败——编排面按类型捕获
)
```

| 符号 | 层 | 语义要点 |
|------|-----|---------|
| `Judge`（Protocol） | core | 判定端口；`instruction` 是逐次调用参数（默认空串）；窗口与判停 τ 是宿主配置，**不进端口** |
| `JudgedCandidate` | core | 五字段冻结 dataclass：`id/name/description` 必填，`use_when/avoid_when` 默认空串 |
| `Judgment` | core | `probabilities` 键集必须与候选 id 集一一对应；`input_tokens/output_tokens` 可 `None`（部分端点不计量，缺席用 None 不用伪 0） |
| `select_with_judge` | core | 门槛 `minimum_probability` **无默认值**（照 `clearly_related` 风格——判停门槛各调用点自行标定，不给跨调用点搬数值开口子） |
| `JudgeResponseError` | `[judge]` | 鉴权失败/响应缺键等结构错误抛它；编排面按类型捕获，不裸穿 requests 异常 |

## 编排模式：exact 短路在调用方

`select_with_judge` **只消费已有 Judgment，不触发判定**。exact 命中短路发生在调用方编排层——先查 `hit.exact`，命中就不必花一次 judge 调用（范例见仓库 `experiments/jev_retrieval.py`）：

```python
from agent_retrieval import rank_candidates, select_with_judge, Judgment, JudgedCandidate

hits = rank_candidates(pool, query, corpus_text=corpus, item_id=lambda t: t.id)
shortlist = hits[:20]                        # 窗口 N 是宿主配置（推荐起点 20，见 config-selection）

if any(hit.exact for hit in shortlist):
    picked_id = next(hit.item.id for hit in shortlist if hit.exact)   # 短路：不调 judge
else:
    judged = [JudgedCandidate(id=item_id(h.item), name=name(h.item),
                              description=desc(h.item)) for h in shortlist]
    judgment = judge.judge(query, judged)     # 一次调用判全部候选
    picked_id = select_with_judge(
        shortlist,
        judgment,
        minimum_probability=0.7,              # 必填：各调用点按查询形态自行标定
        item_id=lambda t: t.id,               # 候选对象 → id（与 rank_candidates 同签名）
    )
    # picked_id 为 None = 弃权（最佳概率 < 门槛）——正常返回值，不是异常
```

`select_with_judge` 的校验语义（违反抛 `ValueError`）：候选 id 重复、`judgment.probabilities` 键集与候选 id 集不一致、任一概率越界 `[0, 1]`（NaN 恒按越界拦截）；`max()` 并列时保留 shortlist 检索序。

## 两种判定实现（并列，不互相包装）

| | `JevJudge` | `ChatJudge` |
|---|---|---|
| 线协议 | System One `POST /v1/systemone` 三键 JSON（裸 requests，无 typesafe-sdk 依赖） | 任意 OpenAI 兼容 `{base_url}/chat/completions` |
| 问题形态 | 结构化 Noul 问题（criteria true/false），端点返回逐候选概率 | 单 prompt 输出 JSON 概率映射（markdown 围栏可剥） |
| 身份锚点 | `JevJudgeConfig`（base_url/api_key/model_name/timeout） | `ChatJudgeConfig.identity()` = (model, prompt 版本 `"1"`, temperature) |
| 采样参数 | 端点语义决定 | `temperature=0.0` 显式进身份串——采样参数影响输出语义，不含它会掩盖复现差异 |

两者是**并列实现不互相包装**（ADR-0001）：System One wire 与 chat 自由文本是两种线协议，`Judge` 端口已抽象掉差异；判定载体不同概率不可比，两者不做数值对拍。选型看端点可得性——有 System One 端点用 `JevJudge`（结构化约束更强），只有通用 chat 端点用 `ChatJudge`。prompt 措辞冻结于版本 `"1"`，改措辞必须升版本号。

配置全部显式构造（库纪律：不读环境变量）——凭据由宿主从自己的配置体系解析后传入 Config：

```python
from agent_retrieval import JevJudge, JevJudgeConfig, ChatJudge, ChatJudgeConfig

jev = JevJudge(JevJudgeConfig(base_url=..., api_key=..., model_name=...))
chat = ChatJudge(ChatJudgeConfig(base_url=..., api_key=..., model_name=...))
# 两者同为 judge(query, candidates, *, instruction="") -> Judgment，可互换
```

## 候选投影单一出处

判定输入的候选投影收敛在 `judges.api.projected_candidates`（`judge_state` 与 ChatJudge 共用的单一出处）：每候选只投影 **name + description（截 2,000 字符）**——`tags`/`use_when`/`avoid_when` 不进判定输入（R3 定案；描述截断继承实验旧版语义，20 候选窗口不截断会顶爆 System One 输入预算 HTTP 400）。

这条纪律的意义：投影口径漂移 = 两类 judge 语义分叉。自写编排时不要绕过端口自己拼 state——判定语义（task / retrieval_instruction / 逐候选"具体步骤"、判声明能力不判共享关键词）已经由端口族固化，`JevJudgeConfig`/`ChatJudgeConfig` 显式构造即可复用。

## HTTP 纪律与排查：fail-fast，不降级

两种实现同一套重试语义：退避 (0, 2.0, 5.0, 10.0) 秒；**401/403 鉴权失败抛 `JudgeResponseError` 不重试**；其余 4xx 记入 `last_error` 退避重试 3 次（网关把瞬时限流也报成普通 4xx——实测教训）；网络/解析异常同循环；超时显式传参。

排查时先分类错误再动手：

| 现象 | 性质 | 处置 |
|------|------|------|
| `JudgeResponseError` 且消息含"鉴权失败" | 结构错误，**不重试** | 修凭据/权限 |
| `JudgeResponseError` 且消息含"已重试 3 次" | 端点持续 4xx/网络故障 | 看嵌的 last_error：限流则降 RPM，端点故障则等恢复 |
| ChatJudge 消息含"键集与候选不一一对应"或"概率越界" | 模型结构性输出错误（温度 0.0 下重试无意义；越界不 clamp——失控信号） | 换模型或收紧 prompt，别加重试 |

**Judge 失败 fail-fast 唯一语义，不做降级**（ADR-0001）：Jev 挂了回退检索原序，会把"要不要绑定"的判停标准静默换掉。与嵌入路的 fail-open（降级 BM25，契约 7）刻意不对称——降档安全才 fail-open，语义会漂移就 fail-fast。编排面应按类型捕获 `JudgeResponseError` 显式处理（报错/重试/放弃本次绑定），而不是吞掉后沿用检索序。

## 题型两档与准入红线

判定题型在 0.2.0 终局为**两档并存**（三票预注册实验 #13/#14/#15，完整数字与机制见 [[config-selection.md]] 的 Jev 精排节）：

- **noul（默认）**："能否执行任务所需的一个具体步骤"，二元概率——硬 recall 下限场景维持；
- **score 量规 + P(3) 折叠**：4 档量规折叠出"直接覆盖"概率，供分级排序消费处（MRR/NDCG）。

两条横切纪律（无论哪种题型）：

1. **任何判定读数不得单独作准入闸**——端点对纯问候语稳定给 P(3)=0.96（三连复现，noul 也拦不住全部无任务文本）；准入配 `clearly_related` 式声明面证据。
2. **量化噪声是阈值校准的底座**——端点概率 0.01 量化、同臂重跑抖动 0.02–0.05（judge_parity 实测）。判定阈值校准与"微差异"判读都要以此为底座：0.02 量级的差异在噪声带内，不构成换配置的依据。

## 相关文档

- 题型选型与实验证据：[[config-selection.md]]
- 检索面与 exact 判定（编排的上游）：[[ranking-api.md]]
- BM25 判定闸（`clearly_related`，判定的对偶证据面）：[[bm25-internals.md]]
- 8 条契约与降级不对称的背景：[[core-concepts.md]]
