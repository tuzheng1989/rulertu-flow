# B0 真冒烟记录（主控执行，2026-10-29）

```
$ python plugins/work-skills/scripts/dual-listen.py --mode diverge \
    --snapshot .scratch/smoke-b0-r2/in.md --workdir .scratch/smoke-b0-r2 \
    --task-id smoke-b0-r2 --budget-limit 3 --proc-timeout 240
exit=0
{"ok": true, "output_path": ".../.listen/outputs/20261029T095843Z_smoke-b0-r2_diverge.md",
 "failure": null, "model_effective": "gpt-6.1-sol", "model_verified": false,
 "usage": {"input_tokens": 69900, "cached_input_tokens": 45312,
           "cache_write_input_tokens": 0, "output_tokens": 1351,
           "reasoning_output_tokens": 903},
 "budget_remaining": 1, "disabled": false}
```

- 产出：8 条新分支，每条 ≤40 字、带透镜标注、markdown 列表，与提示词逐字一致
- state：thread_id 捕获、usage_log 入账、cleanup=ok；used=2（含第一轮被杀进程的不返还预留，预算语义正确）
- model_verified=false：事件流未暴露模型字段，按契约如实记"请求值未验证"
- 缓存观察：45312/69900 前缀缓存命中（65%）；69.9K 输入大头为 codex 自身系统提示词，非快照
- 备注：第一轮冒烟暴露 P1×2（stdin 未隔离挂死、超时非硬超时），已修复并补测试；被杀进程遗留孤儿尝试目录 .listen-tmp/4c8f79（清理命令被拒，残留于 gitignored 的 .scratch，无害）
