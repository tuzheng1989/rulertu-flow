# B1 探针观察记录（U1/U2 消解证据）

日期：2026-11-11。两个临时探针用例在 register.test.ts 中运行后已删除（跑完即删），输出摘录如下。

## U1：store.get 钩子入参是否携带 key —— 携带

探针：`on('store.get', (_$, e) => { payloads.push(JSON.stringify(e)); ... })` 后触发一次 session.start，强制失败打印载荷。

```
(fail) pane > PROBE: store.get 事件载荷形态（临时探针，跑完即删)
  AssertionError: expect(received).toBe()
  Expected: "FORCE_FAIL_TO_PRINT_PAYLOADS"
  Received: ["{\"key\":\"lastExecution\"}"]
```

结论：事件载荷为 `{ key: <string> }` 形态，mock 可按 key 分流（委派单 L2 用例的首选路径）。三个 L2 用例据此写为：

```ts
on('store.get', (_$, e) => ({
  value: e.key === 'progressMap' ? {...} : e.key === 'depsGraph' ? {...} : undefined,
}))
```

无需按调用序切换的兜底方案。

## U2：store.set 在测试引擎的失败形态 —— 抛 HooksError 被 catch 吃掉（非静默 no-op）

探针：捕获 ui.log 全量消息，连续调用 flow_deps + flow_report，强制失败打印。

```
(fail) pane > PROBE2: store.set 在测试引擎的失败形态（临时探针，跑完即删)
  AssertionError: expect(received).toBe()
  Expected: "FORCE_FAIL_TO_PRINT_LOGS"
  Received: "{\"text\":\"flow-deck 波次依赖持久化失败：HooksError: no implementation for store.set\",\"to\":\"debug\"} || {\"text\":\"flow-deck 批次进度持久化失败：HooksError: no implementation for store.set\",\"to\":\"debug\"} || {\"text\":\"flow-deck 跨会话持久化失败：HooksError: no implementation for store.set\",\"to\":\"debug\"}"

  nothing beneath the plugins answers store.set: a test answers it with on('store.set', ...): { value: ... } for a call on $, the event's own result otherwise
```

结论：
1. store.set 在测试引擎默认抛 `HooksError: no implementation for store.set`，被 persistProgress/persistDeps 的 try/catch 捕获后仅落 debug log，工具返回值不受影响（G4 直接证据：三条持久化失败日志在场而 flow_deps/flow_report 用例全部通过、返回文案正确）。
2. **与方案调研结论的出入（上报主控）**：引擎提示 `on('store.set', ...)` 实际可被测试钩子应答（"a test answers it with on('store.set', ...)"）——即写入侧机器断言并非不可行，register.test.ts:922「测试引擎无该设施」的注释记载过时。本批按委派单边界未加写入侧断言用例；B2（backfill 复用 persistProgress 通道）与 G8 可考虑利用该设施补写入侧断言。
