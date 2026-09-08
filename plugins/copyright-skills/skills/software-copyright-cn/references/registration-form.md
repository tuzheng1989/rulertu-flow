# 在线填报工作底稿

## 流程口径

登记全程在线办理：在线填报申请表、在线打印申请确认签章页、签章后上传 PDF、不得擅自改变签章页格式和打印比例（填报入口 https://register.ccopyright.com.cn ，软件登记 R11）。核对记录：中国版权保护中心官网"所需文件"页（https://www.ccopyright.com.cn/index.php?optionid=1080），核对于 2026-09-03。凡涉及官方要求，以官网现行文本为准。

## 输入与事实边界

用户提供的 `.xlsx` 是"在线填报工作底稿"：仅用于收集与核对字段，不是正式登记表交付物；登记表以在线系统填报为准。先复制到输出目录，再操作副本。运行：

```powershell
python scripts/registration_form.py inspect --template "登记表.xlsx" --output "form-inspection.json"  # "登记表.xlsx" 为示例文件名，以实际文件名为准
```

检查工作表、合并单元格、字段标签、现有值、公式、批注、图片和绘图对象。底稿中已有的另一软件名称、技术栈、代码量或功能描述是待替换示例，不是当前仓库事实。申请人名称、统一社会信用代码等主体信息只有经用户确认后才能沿用。

## 填写

创建 UTF-8 JSON，使用单元格坐标显式赋值：

```json
{
  "sheet": "主表",
  "values": {
    "C3": "软件全称",
    "C4": "软件简称",
    "C6": "V1.0"
  }
}
```

执行：

```powershell
python scripts/registration_form.py fill --template "登记表.xlsx" --facts "registration-values.json" --output "在线填报工作底稿-待确认.xlsx"  # "登记表.xlsx" 为示例文件名，以实际文件名为准
```

脚本拒绝覆盖模板，并将修改记录写到相邻的 `.changes.json`。涉及复选框、表单控件或绘图对象的选择项优先用 Excel/LibreOffice 在输出副本中操作；`openpyxl` 可能无法完整保留这些对象。若检测到此类对象，交付前必须打开副本进行可视检查。此处产出的是工作底稿副本，仍不是登记表交付物。

## 在线填报映射

底稿字段 → 在线表单栏目对照（以 `inspect` 实际输出为准）。勾选列取 `filled` / `pending`：对应事实表字段为 `user_confirmed` 时才可勾 `filled`；未经确认一律 `pending`，并列入 `review-needed.md`。

| 底稿字段 | 在线表单栏目 | 勾选（filled/pending） |
|---|---|---|
| 软件全称 | 软件全称（与说明书/源代码文档一致） | pending |
| 软件简称 | 软件简称（无简称可空） | pending |
| 版本号 | 版本号 | pending |
| 开发完成日期 | 开发完成日期 | pending |
| 发表状态 | 是否已发表 / 首次发表日期 | pending |
| 开发方式 | 开发方式 | pending |
| 权利取得方式 | 权利取得方式 | pending |
| 权属情形 | 申请情形（六选一，见 references/ownership.md） | pending |
| 主要功能 | 主要功能及其用途 | pending |
| 技术特点 | 技术特点 | pending |
| 著作权人及联系人信息 | 著作权人、联系人及证件信息 | pending |

示例默认 `pending`，不代表任何字段已确认。`filled` 只能由用户确认事实（事实表 `user_confirmed`）后填写。

## 当前常见字段

不同底稿坐标可能不同，以 `inspect` 输出为准。常见内容包括：软件全称、简称、版本号、作品说明、开发完成日期、发表状态、开发方式、权利取得方式、权利范围、软硬件环境、开发工具、运行平台、支持软件、编程语言、源程序量、开发目的、行业、主要功能、技术特点、著作权人及联系人信息。

功能类字段用仓库证据起草，并遵守底稿字数提示。叙述类字段（作品说明、开发目的、主要功能、技术特点）内部字数预算 500–1,300 字，唯一权威出处见 copyright-code-review SKILL.md F 项，本文件不重复展开为硬性要求；仍按「开发背景 → 核心功能 → 技术实现 → 应用场景」组织，技术实现段使用事实表中的设计要点（架构决策、业务规则来源、特殊输入与失败模式），写的是人的设计，不是代码复述。先写清输入、处理步骤、输出和用户可见结果，再用同插件 `copy-polisher` 做最小改稿。宣传语、市场地位、性能提升、生产就绪和“行业领先”等内容没有证据就不写。

## 完成标准

- 软件名称、版本与两份 Word 文档完全一致。
- 每个声称的功能指向具体代码证据（文件/函数），与说明书章节对应；无实现对应的声称功能删去或列入 `review-needed.md`，不保留。
- 源程序量取自源代码构建 manifest 的代码行数（`total_code_lines`，注释与空行不计入），与截断口径（3,000 阈值、前后 1,500 段）自洽；原始物理行数（`total_physical_lines`）与逐文件统计（`strip_stats`）在审计文件中可追溯。
- 主体、日期、发表和权利字段均为 `user_confirmed` 或明确列入 `review-needed.md`。
- 在线填报映射表中无未决的 `pending` 项，或未决项已列入 `review-needed.md`。
- 底稿模板未改，输出副本可正常打开，版式和打印区域无明显变化。
- 上传前运行 `python scripts/check_submission.py`，机检事实与 `manual_items` 人工核验项逐条处置。
