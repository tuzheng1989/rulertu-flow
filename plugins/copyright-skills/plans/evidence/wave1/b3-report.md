# B3 回报摘要（测试基建：现有脚本行为基线）

日期：2026-09-03　批次：B3（T1，纯加法测试，未改任何生产文件）

## 验证命令与结果

- `python -m pytest plugins/copyright-skills/tests -q`
- 退出码：0
- 结果：29 passed，0 failed，0 skipped
- 完整输出：`plugins/copyright-skills/plans/evidence/wave1/b3-pytest.log`

## 新增文件与用例数

| 文件 | 用例数 |
|---|---|
| tests/conftest.py | （fixture：脚本加载 / CLI 运行器 / write_tree / make_lines / tiny_png / autouse git 隔离） |
| tests/test_inventory_repo.py | 7 |
| tests/test_build_source_docx.py | 6 |
| tests/test_build_manual_docx.py | 4 |
| tests/test_registration_form.py | 4 |
| tests/test_scan_source.py | 5 |
| tests/test_similarity_check.py | 3 |
| tests/README.md | —（一行 dev 依赖说明） |

合计 29 个用例。

## skip

无。

## 与用例清单的偏差（行为事实，脚本未改）

1. `registration_form.fill` 的"模板与输出同路径"分支（:50-51）在输出已存在时不可达
   （先命中覆盖检查），且路径相同时文件必然已存在；用例以"同一路径且均不存在"触发，
   锁定检查语序与 `output must differ from template` 文案。
2. 清单排序用例不断言"同 casefold 键内的次序"：该次序取决于 rglob 枚举顺序（文件系统相关）；
   且 Windows 文件系统大小写不敏感，`A.py`/`a.py` 是同一文件。改用 4 个大小写混合的
   互异文件名断言 casefold 序（apple < Banana < cherry < Zebra）。
3. `scan_source` CLI 入口候选：`app.py` 本身在 ENTRY_FILE_NAMES（:41-44），
   CLI 汇总断言为 `["app.py", "main.py"]`（负例由 scan_file 单元用例覆盖）。
4. 3001 行切片的独立真值：records[:1500] 为 1..1500 行、records[-1500:] 为 1502..3001 行，
   第 1501 行被跳过；manifest 断言 first=1 / head_end=1500 / tail_start=1502 / last=3001。
5. git 隔离：conftest autouse 设置 `GIT_CEILING_DIRECTORIES=tmp_path`，使所有用例稳定命中
   "非 git 目录"分支（已实测 git ls-files exit 128 → 脚本返回 None）。

## 范围说明

本批次仅新增 `plugins/copyright-skills/tests/`；git status 中两个 SKILL.md 的修改来自
并行的 B1/B2 批次，非本批次产出。
