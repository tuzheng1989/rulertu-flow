---
name: anydoc-to-md
description: EvoCenter 专用本地文档转 Markdown 技能。文本型文档（Word/PowerPoint/Excel/ODF/RTF/EPUB/CSV/PDF）用 anydoc 引擎（纯 Rust，亚 5ms/文档）；扫描版 PDF 自动路由到最佳 OCR 引擎（route_ocr.py 采样评分：现代横排印刷→Windows OCR 秒级/页；古籍竖排繁体/复杂版面→DeepSeek-OCR+llama.cpp；短文档≤8页→Claude 视觉直读），含循环检测/断点续传/版式整理。当用户说"把 docx/pdf/pptx/xlsx 转成 markdown"、"文档转 md"、"anydoc"、"转换文档"、"转成 md"、"扫描版 pdf 转文字"、"OCR 这本书/文档"时触发。默认输出位置由调用决定（工具型）；用于知识库导入时输出到 inbox/ 并加 frontmatter。
version: 3.0.0
metadata:
  openclaw:
    requires:
      anyBins:
        - anydoc
---

# anydoc to Markdown（EvoCenter 专用）

**多引擎路由**，按文档特征自动匹配最佳方法：

| 文档特征 | 引擎 | 速度 | 质量 |
|---------|------|------|------|
| 有文本层（Word/PPT/Excel/ODF/RTF/EPUB/CSV/文本型 PDF） | [anydoc](https://github.com/firecrawl/anydoc)（纯 Rust，14 种格式） | 亚 5ms/文档 | 完美 |
| 扫描版，页数 ≤ 8 | Claude 视觉逐页读图 | 即时 | 极高 |
| 扫描版，现代横排印刷（路由评分 ≥ 70） | Windows OCR（系统自带，`winocr.ps1`） | ~2s/页 | 正文高；美术字标题差 |
| 扫描版，古籍/竖排/繁体/复杂版面（评分 < 70） | DeepSeek-OCR + llama.cpp（`ocr_pdf.py`） | ~30s/页 | 最高（版面理解） |

扫描版 PDF **第一步先跑路由**：`python .claude/skills/anydoc-to-md/scripts/route_ocr.py "<PDF>"`，按输出的引擎建议走对应管线（详见 C 节）。

## 支持格式

| 格式 | 扩展名 | 管线 |
|------|--------|------|
| Word | `.doc` `.docx` `.docm` | anydoc |
| PowerPoint | `.ppt` `.pps` `.pot` `.pptx` `.pptm` `.ppsx` `.ppsm` | anydoc |
| Excel | `.xls` `.xlsx` `.xlsm` `.xlsb` | anydoc |
| OpenDocument | `.odt` `.ods` `.odp` | anydoc |
| RTF | `.rtf` | anydoc |
| EPUB | `.epub` | anydoc |
| CSV | `.csv` | anydoc |
| PDF（文本型） | `.pdf` | anydoc |
| PDF（扫描版） | `.pdf` | OCR 管线（见 C 节） |

anydoc 格式从文件**内容**自动检测（不看扩展名），CSV 等无签名的格式靠扩展名或 `--format` 指定。

## 用法

### A. 工具型（默认，anydoc）

转换单个文档，输出位置由调用决定。不加 frontmatter，保留 anydoc 原始干净输出。

```bash
anydoc <输入文件> -o <输出路径>
```

例：把 `output/exports` 下的公文转回 md：

```bash
anydoc "output/exports/关于项目立项的请示.docx" -o "workspace/关于项目立项的请示.md"
```

读取标准输入（管道场景）：

```bash
curl -s https://example.com/paper.pdf | anydoc -
```

### B. inbox 导入型（可选，用于知识库素材）

把外部文档导入知识库时，输出到 `inbox/` 并注入 frontmatter。遵守 CLAUDE.md「素材处理」规则。**两条管线通用此节。**

```bash
anydoc "<源文件>" -o "inbox/<文件名>.md"
```

转换完成后，用 Edit 在文件顶部注入 frontmatter：

```yaml
---
source_type: document
source_path: <源文件路径或来源说明>
imported: <YYYY-MM-DD>
status: inbox
---
```

落盘规则：
- `inbox/` 保持扁平，不建子目录。
- 中文文档原样保留，不翻译。
- 非中文文档触发翻译归一化（导入即转化为中文）。
- 原始附件（PDF 等）移至 `assets/files/` 存档，不视为过程产物。
- 是否消化进 wiki 由用户决定，不主动触发 /llm-wiki。

## anydoc 命令参考

```
anydoc <file> [options]
anydoc - [options] < file      从 stdin 读取
```

| 选项 | 说明 |
|------|------|
| `-o, --output <path>` | 输出到文件（默认输出到 stdout） |
| `-f, --format <fmt>` | 指定格式。一般不需要，自动检测 |
| `-h, --help` / `-V, --version` | 帮助 / 版本 |

退出码：`0` 成功；`1` 文档无法读取或转换；`2` 用法错误。

首次使用前确认 anydoc 可用（`anydoc --version`）；全局未安装则回退 `npx -y @firecrawl/anydoc <file> -o <out>`。
注意：Windows ARM64 上 npx 的 anydoc 无原生绑定会加载失败（npm optional deps bug + 无 win32-arm64 构建），此时 anydoc 不可用，文档类转换走 OCR 管线或其他工具。

---

## C. 扫描版 PDF → OCR（先路由，再选引擎）

### 第一步：路由决策（route_ocr.py）

```bash
python .claude/skills/anydoc-to-md/scripts/route_ocr.py "<扫描版.pdf>"
```

自动完成：文本层检测（有则提示改用 anydoc）→ 中段采样 3 页渲染 → Windows OCR 试跑 → 质量评分（字符密度/竖排碎行/同字连击/Latin 异常占比）→ 输出引擎建议与预估耗时。

- **评分 ≥ 70**（现代横排印刷）→ Windows OCR 引擎，加 `--run -o <输出.md>` 一键全书：
  ```bash
  python .claude/skills/anydoc-to-md/scripts/route_ocr.py "<书.pdf>" --run -o inbox/<书名>.md
  ```
- **评分 < 70**（古籍/竖排/繁体/复杂版面）→ DeepSeek-OCR 管线（下方 C2 节）
- **页数 ≤ 8** → 直接由 Claude 会话逐页读图转写，无需脚本（渲染出 pages/*.png 后逐张 Read）

**Windows OCR 引擎特性**（实战验证：189 页育儿手册，零失败，约 3 分钟）：
- ✅ 正文印刷体准确率高（专有名词/数字/标点均对），已内建 CJK 字间空格/书名号/小数点清理
- ✅ 零依赖零下载（系统自带，zh-Hans 语言包），断点续传与 DeepSeek 管线同语义
- ⚠️ **书法/美术字标题必崩**（如"常见病"→"常 见 柄"），封面/荐词页同理——此类页交给 Claude 视觉兜底：读 `*.ocr/pages/pageNNNN.png` 人工转写后替换对应 `pages-md/pageNNNN.md`，重跑合并
- ⚠️ 输出为纯文本流（换行保留），无 Markdown 标题/表格结构化；需要结构化成书时选 DeepSeek 管线

### C2. DeepSeek-OCR 管线（llama.cpp）

沉淀自《妇人大全良方》631 页全流程实战。纯本地 CPU 推理（骁龙 X Elite 约 2 页/分），中文简体横排印刷体识别质量接近人工校对。

### 环境准备（一次性）

工具与模型缓存于 `~/.cache/evo-ocr/`（可用 `OCR_HOME` 环境变量覆盖）：

```
~/.cache/evo-ocr/
├── llama-cpp/llama-server.exe        # llama.cpp win-cpu-arm64 构建
└── models/
    ├── DeepSeek-OCR-Q8_0.gguf        # 2.9GB，ggml-org 官方
    └── mmproj-DeepSeek-OCR-Q8_0.gguf # 427MB 视觉编码器
```

Python 依赖：`pip install pypdf pillow`。

缺工具时安装（hf-mirror 国内快；llama.cpp 从 GitHub Releases 选 `llama-bXXXXX-bin-win-cpu-arm64.zip`，务必选含 `llama-server.exe` 的包）：

```bash
mkdir -p ~/.cache/evo-ocr/models
curl -sL -C - "https://hf-mirror.com/ggml-org/DeepSeek-OCR-GGUF/resolve/main/DeepSeek-OCR-Q8_0.gguf" -o ~/.cache/evo-ocr/models/DeepSeek-OCR-Q8_0.gguf
curl -sL -C - "https://hf-mirror.com/ggml-org/DeepSeek-OCR-GGUF/resolve/main/mmproj-DeepSeek-OCR-Q8_0.gguf" -o ~/.cache/evo-ocr/models/mmproj-DeepSeek-OCR-Q8_0.gguf
```

### 标准用法

```bash
python .claude/skills/anydoc-to-md/scripts/ocr_pdf.py "<扫描版.pdf>" -o "<输出.md>"
```

脚本自动完成：文本层检测 → 逐页渲染 → 拉起 llama-server（复用已运行的）→ 串行 OCR → 合并清理（页眉/页码/半角标点/段落重建/标题去重）→ 质量报告。

**有页眉或侧边栏的书**（最高频故障源，见下方经验）加裁剪参数：

```bash
python .claude/skills/anydoc-to-md/scripts/ocr_pdf.py "<书.pdf>" -o inbox/<书名>.md \
  --crop-top 148 --crop-side "100,1390" --header-pattern "中医临床必读丛书"
```

| 参数 | 说明 |
|------|------|
| `--pages A-B` | 只处理页范围（1 起算），先小范围试跑验质量 |
| `--crop-top N` | 裁掉顶部 N px（页眉区。页眉艺术字会诱导 OCR 循环输出） |
| `--crop-side "左,右"` | 奇数书页的正文左/右像素界；偶数页自动镜像换算 |
| `--header-pattern RE` | 页眉清理正则 |
| `--workdir DIR` | 工作目录（默认 `<输出>.ocr/`），存逐页底稿，支持断点续传 |
| `--keep-server` | 结束后保留 server 供复用（批量多本时省 25s 加载） |

### 实战经验（踩坑清单，脚本已固化大部分）

| 坑 | 对策（脚本已内置的标 ✅） |
|----|--------------------------|
| 页眉艺术字/竖排边栏诱导循环输出（重复书名×200+） | ✅ 裁掉页眉边栏（`--crop-top`/`--crop-side`）；✅ 循环检测拦退化输出 |
| 裁剪后首行贴边被漏识 | ✅ 顶部自动加 60px 白边 |
| 奇偶页装订方向镜像，统一裁剪切掉行首字 | ✅ `--crop-side` 奇偶差异化；先各裁一奇一偶页目检正文边界 |
| 双请求并行挤爆 KV 池（HTTP 500） | ✅ 串行；✅ KV 池 16384 |
| 温度>0 引入幻觉（凭空生成「人物描写」等无关内容） | ✅ 温度 0 + top-k 1 |
| 中断/失败返工 | ✅ 逐页落盘断点续传，重跑自动跳过已完成页 |
| 顽固页 3 次重试仍循环 | ❌ 人工兜底：读该页原图（工作目录 `pages/pageNNNN.png`）逐字转录，写入 `pages-md/pageNNNN.md` 后重跑脚本合并 |
| 形近字误识（如 秦艽→秦芃） | ❌ 合并后词频抽查领域高频词，源页替换 |
| 每页顶部栏目名重复成标题（「导读」×3） | ✅ 栏目级短标题全书唯一化 |
| OCR 逐行输出导致段落碎片化 | ✅ 段落重建（非句末行并入下文，标题/目录条目/论名行保护） |

### 时长与规模预期

- 骁龙 X Elite（12 核 ARM64，纯 CPU）：约 **2 页/分**，100 页 ≈ 50 分钟，600 页 ≈ 5 小时（建议 `--pages` 分段后台跑）。
- 有 N 卡的机器可换 llama.cpp CUDA/Vulkan 构建放 `~/.cache/evo-ocr/llama-cpp/`，命令不变。

### 进阶清理（书籍级，人工复核）

通用合并只做「无损清理」。成书还需要：
- 卷/章结构：从目录页解析卷次起始页码，在正文对应位置插标题；
- 页眉变体：OCR 对艺术字页眉有十几种残缺形态（`必读从`/`中库临康`…），按字符集白名单清除；
- 索引区：扫描书常在末尾附带文本层索引页（超星格式），用 `pypdf.extract_text` 直接提取，无需 OCR。

参照实现：`workspace/fuliang-ocr/merge_book.py`（《妇人大全良方》合并脚本，含上述全部规则）。

## 不做（边界）

- 不做翻译归一化（那是 inbox 落盘后翻译流程与 /llm-wiki 的事，本技能只管转 md）。
- OCR 不追求全自动完美：顽固页人工转录兜底、形近字抽查是流程的一部分，不是脚本缺陷。
- 默认单文件转换；批量需求由调用方循环调用。
