# deepeval 桥接指南

本 skill 的 Prompt-based 评测与 deepeval 的代码化评测互补而非互斥。
本文说明何时及如何将两者结合使用。

---

## 决策树：何时使用 deepeval

```
需要 CI/CD 自动化回归测试？
├── 是 → 使用 deepeval（Pytest 集成）
└── 否
    ├── 需要确定性决策树检查（如格式合规、枚举值校验）？
    │   ├── 是 → 使用 deepeval DAG Metric
    │   └── 否
    │       ├── 需要合成数据生成？
    │       │   ├── 是 → 使用 deepeval Synthesizer
    │       │   └── 否 → 使用本 skill（Prompt 驱动）
    │       └── 仅需要语义质量评估？
    │           └── 使用本 skill（Prompt 驱动）
```

**简单原则**:
- **语义理解类指标**（正确性、连贯性、创意性）→ Prompt 驱动
- **确定性检查类指标**（格式合规、JSON schema、工具调用序列）→ deepeval
- 两者可以同时使用，各负责自己擅长的部分

---

## 指标映射表

| 本 skill 指标 | deepeval 对应指标 | 适合由谁负责 |
|--------------|------------------|-------------|
| Correctness | GEval (criteria="correctness") | Prompt（需要语义理解） |
| Completeness | GEval (criteria="completeness") | Prompt（需要语义理解） |
| Coherence | GEval (criteria="coherence") | Prompt（需要语义理解） |
| Safety | Toxicity + 自定义 DAG | deepeval（确定性检查更可靠） |
| ToolCorrectness | ToolCorrectnessMetric | deepeval（原生支持工具调用评估） |
| ToolSelection | ToolCorrectnessMetric | deepeval |
| ParameterAccuracy | ToolCorrectnessMetric (strict) | deepeval |
| InstructionAdherence | PromptAlignmentMetric | 混合（Prompt 评估语义，deepeval 检查格式） |
| FormatCompliance | JSONCorrectnessMetric | deepeval（确定性检查） |
| ConstraintFollowing | DAG 自定义 | deepeval（决策树更精确） |

---

## 集成方式 1: 互补评测

Prompt-based 评测负责语义质量，deepeval 负责确定性检查。

```python
# test_agent.py
import pytest
from deepeval import assert_test
from deepeval.metrics import (
    ToolCorrectnessMetric,
    JSONCorrectnessMetric,
    TaskCompletionMetric,
)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

# deepeval 负责：确定性检查
def test_tool_correctness():
    metric = ToolCorrectnessMetric(
        should_exact_match=True,
        should_consider_ordering=True,
    )
    test_case = LLMTestCase(
        input="查北京天气",
        actual_output="北京今天晴天，25度",
        expected_output="晴天，25度",
        tools_called=["get_weather"],
        expected_tools=["get_weather"],
    )
    assert_test(test_case, [metric])

def test_json_format():
    metric = JSONCorrectnessMetric()
    test_case = LLMTestCase(
        input="返回JSON格式",
        actual_output='{"city": "北京", "temp": 25}',
        expected_output='{"city": "string", "temp": "number"}',
    )
    assert_test(test_case, [metric])

# Prompt-based 评测由本 skill 生成的 evaluator-prompt.md 承担
# 负责：正确性、完整性、连贯性等语义指标
```

运行:
```bash
# 确定性检查（deepeval）
deepeval test run test_agent.py

# 语义质量评估（Prompt 驱动，由本 skill 的阶段 4 执行）
# 两份报告合并即为完整评测
```

---

## 集成方式 2: deepeval 承载 Prompt 评测

将本 skill 生成的评估提示词嵌入 deepeval 的 GEval 指标中，
利用 deepeval 的执行引擎和报告系统。

```python
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

# 将本 skill 阶段 3 生成的评估标准转化为 GEval criteria
correctness = GEval(
    name="Correctness",
    criteria="""评估输出的正确性:
- 5分: 完全正确，事实无误，精准匹配用户意图
- 4分: 基本正确，有微小偏差但不影响实际使用
- 3分: 部分正确，有明显偏差但核心信息无误
- 2分: 大部分不正确，核心信息有误
- 1分: 完全不正确或与用户意图无关""",
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.5,  # 对应 3 分及以上
)

completeness = GEval(
    name="Completeness",
    criteria="评估输出是否充分覆盖了用户需求的所有方面...",
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.5,
)

test_case = LLMTestCase(
    input="用户输入",
    actual_output="Agent 实际输出",
    expected_output="参考答案",
)

correctness.measure(test_case)
print(f"Score: {correctness.score}, Reason: {correctness.reason}")
```

---

## 集成方式 3: 合成数据生成

使用 deepeval Synthesizer 生成评测数据集，然后用本 skill 的 Prompt 模板进行评估。

```python
from deepeval.synthesizer import Synthesizer

synthesizer = Synthesizer()

# 从文档生成评测数据
synthesizer.generate_goldens_from_docs(
    document_paths=["path/to/agent_docs/"],
    max_goldens_per_document=5,
)

# 保存为 JSON，可转换为 dataset.json 格式
synthesizer.save_as(file_path="synthetic_dataset.json", type="json")
```

然后将生成的数据转换为本 skill 的 dataset.json 格式，
再使用本 skill 的评估提示词进行质量评估。

---

## 安装和配置

```bash
# 安装 deepeval
pip install deepeval

# 登录 Confident AI（可选，用于平台管理）
deepeval login

# 运行评测
deepeval test run test_agent.py
```

---

## CI/CD 门禁配置

```yaml
# .github/workflows/agent-eval.yml
name: Agent Evaluation
on: [push, pull_request]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install deepeval
      - run: deepeval test run test_agent.py
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

## 两套报告合并

| 报告来源 | 覆盖范围 | 格式 |
|---------|---------|------|
| 本 skill 报告 (report.md) | 语义质量（正确性、连贯性等） | Markdown |
| deepeval 报告 | 确定性检查（格式、工具调用等） | 终端输出 / Confident AI 平台 |

合并策略:
1. 将 deepeval 的通过率添加到本 skill 报告的"总体评分"表中
2. 将 deepeval 发现的格式/工具问题添加到"关键发现"中
3. 综合两份报告给出最终评估结论
