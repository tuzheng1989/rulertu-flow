# B5 回报摘要（源代码构建器：显式顺序 + 入口前置 + 渲染实测）

执行人：Executor（批次 B5 / T2）
日期：2026-09-03
测试基线：44 用例全绿；交付后全量 50 用例（+6）全绿。

## 一、改动文件清单

| 文件 | 改动 |
|---|---|
| `plugins/copyright-skills/skills/software-copyright-cn/scripts/build_source_docx.py` | 新增 `--first` 参数与前置逻辑；manifest 新增 `reordered_first` 字段 |
| `plugins/copyright-skills/skills/software-copyright-cn/references/source-code.md` | 抽取规则 / 构建命令段 / 完成标准 改写对齐新参数 |
| `plugins/copyright-skills/tests/test_build_source_docx` | 追加 6 个用例（仅追加，未改既有用例；新增 `import hashlib`） |
| `plugins/copyright-skills/plans/evidence/wave3/` | 新增 b5-pytest.log（全量输出）、b5-pytest-directed.log、本摘要 |

未触碰：test_render_check.py、manual.md、check_submission.py 及其他批次文件。
tests/README.md 未改（无新增依赖，原有运行说明仍准确）。

## 二、锚点改前 / 改后

### build_source_docx.py

1. argparse（改前 :54-60，改后 :59-65）
   - 改前：仅 `--inventory / --output / --title / --version / --lines-per-page`。
   - 改后：追加 `--first`（`action="append"`，metavar PATH）。
2. 清单读取后、构建 records 前（改前 :67-70，改后 :73-86）
   - 改前：直接 `for entry in inventory["included_files"]` 串接。
   - 改后：先校验 `--first` 路径——未知路径 `raise SystemExit("--first path not in inventory: <未知路径>; available paths: <清单内全部路径>")`（路径按 `dict.fromkeys` 去重保序）；再按传入顺序前置命中文件，其余保持清单相对顺序（`ordered` 列表），records 循环改遍历 `ordered`。
3. manifest（改前 :138-154，改后 :144-160 附近）
   - 改前：无 `reordered_first`。
   - 改后：`"reordered_first": first_paths`（本次前置文件的有序列表；空列表 = 未前置）。

### source-code.md

1. 抽取规则（改前 :18，改后 :18）
   - 改前：「清单默认路径顺序不满足时，把入口文件调整到串接序列最前，并在清单中记录这一调整及理由」。
   - 改后：「默认按清单文件路径顺序串接；入口未居前时，用 `--first <入口相对路径>` 前置到串接序列最前，manifest 的 `reordered_first` 字段即记录本次前置的文件与顺序，不再要求手工改清单」。
2. 构建命令段（改前 :30-33，改后 :30-34）
   - 命令示例追加 `--first "src/main.py"` 用法；其后追加 `render_check.py --docx "源代码.docx" --min-lines 50 --output render-report.json` 步骤。
   - 新增口径段：每页 50 行对齐官方"每页不少于 50 行"（核对记录：官网申请须知 2026-09-03，URL 待人工补充，与 manual.md:30 写法一致）；说明长行折行导致实际渲染行数少于每页记录数，报告列出不足页，整改（调小 `--lines-per-page` 或字号）由人工决策，构建器不自动改版式；无 soffice 时脚本非零退出转人工。
3. 完成标准（改前 :35-41，改后 :37-45）
   - 新增：`--first`/`reordered_first` 与 `first.path` 一致可核；`reordered_first` 如实记录前置调整；渲染实测无不足页，无法渲染时转 `review-needed.md` 人工核对项。
   - 新增审计口径移交句：说明书 audit JSON 的 `page_evidence` 键为"内容页序号（1 起）"，与 docx 物理页号相差封面+目录 2 页，消费时注意换算。

## 三、TDD 红绿证据（逐切片）

- 切片 1（`--first` 参数）：
  - 红：`python -m pytest plugins/copyright-skills/tests/test_build_source_docx.py -q` → 4 failed, 6 passed，exit 1。4 个新用例全部因 `build_source_docx.py: error: unrecognized arguments: --first` 失败；既有 6 用例不受影响。
  - 绿：实现后同命令 → 10 passed，exit 0。
- 切片 2（`reordered_first`）：
  - 红：定向 `-k "reordered_first or no_first_flag"` → 2 failed（`KeyError: 'reordered_first'`），10 deselected。
  - 绿：manifest 加字段后 → 12 passed，exit 0。
- 切片 3（source-code.md）：无测试，以 Grep 断言收尾——`--first`、`reordered_first`、`render_check.py --min-lines 50`、核对记录、`page_evidence` 移交句全部命中；旧表述"在清单中记录这一调整及理由"零残留。

## 四、验证命令与结果

| 命令 | 退出码 | 结果 |
|---|---|---|
| `python -m pytest plugins/copyright-skills/tests/test_build_source_docx.py -q` | 0 | 12 passed |
| `python -m pytest plugins/copyright-skills/tests -q` | 0 | 50 passed, 5 warnings（基线 44 + 新增 6，无回归） |
| 红线回归（无 `--first` 两次构建 sha256 一致） | — | 由既有用例 `test_selected_sha256_stable_across_runs` 覆盖，全量运行中绿 |
| Grep 文档断言（source-code.md） | — | 全命中，无旧表述残留 |

全量 pytest 完整输出：`plugins/copyright-skills/plans/evidence/wave3/b5-pytest.log`（50 passed）。

## 五、设计取舍与偏差

1. 重复传入同一路径：`--first a.py --first a.py` 按 `dict.fromkeys` 去重保序（前置一次），而非报错——委派单未规定，选择最小且无歧义行为。
2. `reordered_first` 记录的是传入的路径列表（含"该文件在清单中本就居首"的显式前置请求），不是"实际位移"的差集；空列表 = 未前置。
3. `selected_sha256` 随串接顺序变化是既定设计取舍（顺序即内容），新用例断言"与按新顺序的独立重算一致"，并用独立真值（手写逐行记录字面量 + `expected_sha256` 助手）避免同义反复。
4. 渲染实测路径（有 soffice）在本机不可实测（环境事实），仅文档口径交付；render_check 接口已与 `render_check.py` 实际参数（`--docx/--min-lines/--output/--soffice`）核对一致。
5. 测试运行中出现的 5 个 warning 均为 PyMuPDF 的 DeprecationWarning（既有，与本次改动无关）。

## 六、剩余问题（报主控）

- 官方口径核对记录的 URL 仍待人工补充（沿用方案已知缺口，与 manual.md 一致标注"URL 待人工补充"）。
- Wave 2 移交项（`page_evidence` 页号换算）已写入 source-code.md:45；B7 收口时如认为放 SKILL.md 更合适，可再迁移。
