# 分模式验证规则

所有模式先检查：叶子 Skill 目录名与 frontmatter `name` 一致；frontmatter 只有 `name` 和 `description`；不存在机器绝对路径；输出不超出用户允许的知识边界。

## Faithful

- `references/index.md` 和生成标记存在。
- 原书目标章节都有对应文件，没有异常编号缺口。
- 父子链接、数字顺序和相对路径正确。
- 父级不重复嵌入完整子章节。
- 开头、中部、结尾和复杂片段没有乱码、空白或错序。
- 至少 5 个检索问题定位到最具体章节。
- 至少 3 个任务正确处理例外、冲突和缺失信息。

运行：

```bash
python scripts/validate_references.py <target>/references
python scripts/validate_output.py <target> --mode faithful
```

## Knowledge

- `overview.md`、`chapters/`、`glossary.md`、`patterns.md`、`cheatsheet.md` 存在且非空。
- 每个章节文件标明来源章节。
- 抽查结论能回到来源，且没有把生成者解释写成作者原话。
- 关键前提、反例和局限没有因压缩而消失。
- glossary、patterns、cheatsheet 之间没有明显冲突。
- 至少 5 个主题、比较、概念或因果查询能定位到正确文件。

运行：

```bash
python scripts/validate_output.py <target> --mode knowledge
```

## Methods

- Pack 中至少一个叶子 Skill；每个都有 `SKILL.md`、`references/evidence.md` 和 `test-prompts.json`。
- 每个方法包含 R、I、A1、A2、E、B。
- 每个方法通过多语境证据、迁移能力、增量价值、可执行性和可区分性检查。
- 每个测试集至少 3 条正例、2 条诱饵、1 条边界，其中至少一条指向兄弟 Skill；单 Skill Pack 无兄弟时在报告中说明豁免。
- 诱饵全部通过，总通过率至少 80%；未通过 Skill 不进入 `INDEX.md`。

运行：

```bash
python scripts/validate_output.py <pack> --mode methods
```

## Hybrid

- `build-plan.json` 的模式为 hybrid，组件为 2–3 个不重复的有效值。
- 实际存在的组件与计划完全一致，不生成计划外目录。
- 每个组件分别通过自己的模式验证。
- faithful、knowledge、methods 的内容身份清晰，没有把衍生内容放入来源层。
- `PACK_INDEX.md` 只列真实存在且通过验证的叶子 Skill。
- 所有叶子 Skill 可独立安装，不依赖 Pack 内相对路径才能执行。

运行：

```bash
python scripts/validate_output.py <pack> --mode hybrid
```

无法自动验证的语义项必须人工抽查，并在交付说明中列出未完成项。结构脚本通过不等于语义质量通过。
