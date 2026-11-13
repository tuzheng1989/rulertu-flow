# image mode 技能文档可执行性冒烟测试结果（B1）

- 测试日期：2026-11-13
- 被测文档：`plugins/work-skills/skills/data-analysis/modes/image.md`
- 待提取图片：`plans/work-skills/.flow-evidence/2026-11-13-data-analysis-consolidation/B1/smoke-table.png`
- 结论：**文档指引足以完成"表格截图 → Markdown 表格 → DataFrame"全流程，校验全部通过**

## 一、提取过程记录

1. 读取被测文档 `image.md`，确认核心工作流：Read 工具视觉直读 → 按"视觉提取指引"输出结构化内容 → 解析为 DataFrame → 校验。
2. 用 Read 工具直读 `smoke-table.png`（会话原生视觉，未用任何外部视觉 API）。
3. 图片类型判定为"表格截图"，按指引中对应行的要点执行：**保持原行列结构逐格提取，数值不四舍五入**；图中无合并单元格，无需注明。
4. 按 "Parsing Visual Reading Results" 节的 `parse_markdown_table` 函数（原样复制，未改动）解析为 DataFrame，脚本用指定 venv 的 Python `-I` 隔离模式运行。
5. 按 Common Pitfalls 中 "Verify extracted data" 要求校验行列数与数值合理性。

## 二、视觉直读得到的 Markdown 表格原文

图片标题：某公司 2026 年前三季度销售业绩表

```markdown
| 季度 | 销售额(万元) | 同比增长 | 目标达成率 |
|------|------------|---------|-----------|
| Q1 | 128.5 | 12.3% | 96.4% |
| Q2 | 156.2 | 18.7% | 104.1% |
| Q3 | 142.8 | 9.5% | 98.2% |
```

## 三、DataFrame 解析与数值类型转换真实运行输出

脚本：`C:\Users\tuzhe\AppData\Local\Temp\B1-smoke\scripts\smoke_image_parse_table.py`
运行命令：`"C:/Users/tuzhe/AppData/Local/Temp/B1-smoke/.venv/Scripts/python.exe" -I smoke_image_parse_table.py`

```
=== DataFrame ===
   季度  销售额(万元)  同比增长  目标达成率
0  Q1    128.5  12.3   96.4
1  Q2    156.2  18.7  104.1
2  Q3    142.8   9.5   98.2

=== dtypes ===
季度             str
销售额(万元)    float64
同比增长       float64
目标达成率      float64
dtype: object
```

数值类型转换符合函数预期：百分比列自动去 `%` 转为 float64；"季度"列为非数值标签，保持 str。

## 四、数据校验结果（Common Pitfalls "Verify extracted data"）

```
=== 行列数核对 ===
期望 3 行 x 4 列，实际 3 行 x 4 列 -> 通过

=== 数值合理性校验 ===
[通过] 销售额均为正数且在 100-200 万元量级
[通过] 销售额合计 = 427.5 万元（图示区间 400-450 内合理）
[通过] 同比增长均在 0%-30% 合理区间
[通过] 目标达成率均在 90%-110% 合理区间（含 Q2 超 100% 属正常）
[通过] 无解析失败的 NaN（数值转换全部成功）

总结论： 全部校验通过
```

行列数与图片实际结构（表头 + Q1/Q2/Q3 三行 × 四列）一致，数值逐格与图核对无误。

## 五、零外部 API 断言确认

全程使用的工具：
- **Read** ×2：读 `image.md` 文档、读 `smoke-table.png` 图片（会话原生视觉直读，图片理解唯一来源）
- **Bash** ×2：检查临时目录、以 `-I` 隔离模式运行本地 pandas 解析脚本
- **Write** ×2：写解析脚本（Temp 目录）、写本结果文件

未调用任何网络服务，未使用任何 API Key，未调用 zai-mcp 视觉类工具或任何 sensenova/其他视觉 API，未发起任何 HTTP 请求。图片理解完全由会话视觉直读完成。解析脚本为纯本地 pandas 运算，无网络代码。

## 六、执行中发现的文档问题

核心流程（表格截图指引 + 解析函数）清晰可执行，本次任务无阻塞。记录以下非阻塞观察：

1. **百分比单位约定未说明**：解析函数把 `12.3%` 转成数值 `12.3`（百分数值而非小数 0.123），文档未写明该约定，后续做百分比运算的使用者需自行留意。
2. **Visualization/Export 节为沙箱环境写法**：中文字体路径 `/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc` 与输出路径 `/mnt/data/`、下载链接 `sandbox:` 均为 Linux 沙箱专属，Windows 本地执行不生效，需自行改路径（本次仅测表格提取，未触发该节）。
3. **Multi-Image Processing 节的 `read_image_and_extract(img)` 是伪函数**：实际语义是"调用方对每张图执行 Read 直读"，文档已有注释说明，可接受，但对新智能体存在歧义风险。
