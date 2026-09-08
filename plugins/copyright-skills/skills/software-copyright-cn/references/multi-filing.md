# 多软著批量申报（一项目多报）

一份项目拆多个软件著作权申报：按模块真实边界把代码切给 N 份材料（如 5 份），每份独立走单套流程，构建前先用 `scripts/batch_validate.py` 做批量校验。本文件是批量模式的权威出处；单套流程的口径（注释、统计、构建命令）见 source-code.md，不变。

## 先说风险：什么叫"换汤不换药"，为什么不行

同代码换名称批量报软著是高概率团灭路径：登记机关审查会把提交代码与已登记软著库比对，雷同直接打回；一项目 5 份之间代码高度雷同，等于把"撞车"做成批量的。合法做法只有一个——**按模块真实边界拆分**：每份材料限定在自己的模块文件集内，共享代码唯一归属，模块间不得复制粘贴改皮。批量校验就是把这些红线变成构建前阻断。

## batch 配置 schema

```json
{
  "entries": [
    {
      "name": "XX调度软件",
      "version": "V1.0",
      "module_roots": ["src/scheduler"],
      "exclude": ["src/scheduler/legacy_stub.py"],
      "first": "src/scheduler/main.py",
      "output_dir": "deliverables/2026-q3/scheduler"
    }
  ],
  "shared_allowlist": ["src/common/version.py"],
  "similarity": {"window": 6, "containment_threshold": 0.2, "min_run": 10}
}
```

- `name` / `version` / `module_roots` / `output_dir` 必填；`name+version` 组合、`output_dir` 各自不得重复。
- `module_roots` 按目录（或精确文件路径）过滤，叠加 `inventory_repo.py` 的默认排除（tests/vendor/minified 等）与条目级 `exclude`。
- `first` 可选，指向该条目文件集内的主程序入口；校验时会核对它在文件集内。
- `shared_allowlist`：有意共享给多个条目的文件清单；列入后不阻断，但必须转入 `review-needed.md` 人工核对（报告的 `review_items` 已生成对应条目）。allowlist 里的文件在两两查重中豁免——有意共享的雷同是已声明的，不重复计罚；allowlist 写了不存在的文件也只记 review 项，不静默。
- `similarity` 可选，默认与 `similarity_check.py` 一致（窗口 6 行、包含度 0.2、最小连续 10 行）。

## 校验项与阻断语义（batch_validate.py）

1. **配置合法性**：必填字段缺失、`name+version` 或 `output_dir` 重复 → 阻断。
2. **唯一归属**：同一文件出现在 ≥2 个条目且未列入 allowlist → 阻断。共享代码唯一归属是拆分的底线；确需共享的（如公共版本头），列入 allowlist 并人工确认每份说明书的表述。
3. **代码行达标**：每份代码行（strip_source 代码行口径）≥ `--min-code-lines`（默认 500，**内部风控下限，非官方要求**）→ 低于即阻断。软著没有官方最低行数，但材料要能独立支撑一个完整软件。
4. **两两查重**：条目两两之间（双向）用 6 行窗口指纹比对，任一文件超限（containment ≥ 0.2 或连续相似 ≥ 10 行）→ 该对阻断。同项目多报最大的驳回风险是提交件互相雷同，此校验在构建前拦截。

任一阻断存在时脚本非零退出；`passed: true` 只代表拆分过了本地自检，不等于登记机关审查通过。

## 循环编排顺序（每份独立走单套流程）

`batch_validate.py` 通过后，逐条目执行单套流程，条目之间互不复用材料内容：

1. `inventory_repo.py --repo . --include-root <module_roots>... --exclude <entry.exclude>... --output <output_dir>/code-inventory.json`
2. `scan_source.py --repo . --include-root <module_roots>... --exclude <entry.exclude>... --output <output_dir>/scan-report.json`（+ 可选 `similarity_check.py` 对项目外参考源），命中经用户审批整改
3. `build_source_docx.py --inventory ... --output <output_dir>/源代码.docx --title <该份软件全称> --version ...`
4. 说明书：每份独立编写页式 spec——功能、操作流程、界面截图按该模块真实动线来；不同份的说明书若高度同构，本身就是"批量套模板"的痕迹，人工把关
5. 登记表底稿：`registration_form.py inspect/fill`，facts 逐份编制；源程序量取该份 manifest 的 `total_code_lines`
6. `render_check.py`、`check_submission.py` 逐份跑
7. 每份独立输出目录交付，禁止跨份复用说明书文本、截图与事实表结论（截图可复用同一真实系统，但界面动线与功能表述必须与该份材料对应）

批量模式不自动生成说明书与登记表内容——它们必须逐份人工/Agent 撰写，脚本的职责是把代码侧的拆分、行数、查重拦在构建之前。
