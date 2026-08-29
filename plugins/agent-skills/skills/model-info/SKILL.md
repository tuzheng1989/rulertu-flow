---
name: model-info
description: AI 模型参数查询和对比工具。从 models.dev API 实时获取模型规格、定价、能力和限制信息。当用户需要：查询特定模型的参数信息、对比多个模型的差异、搜索符合条件的模型（价格、能力、提供商）、了解模型的技术规格时触发。
---

# Model Info

基于 [models.dev](https://models.dev) 开源数据库的 AI 模型信息查询工具。

## 快速开始

使用提供的脚本从 API 实时获取模型数据：

```bash
# 获取所有模型
python scripts/fetch_models.py

# 获取特定模型
python scripts/fetch_models.py --get anthropic/claude-3-5-sonnet-20241022

# 列出提供商的所有模型
python scripts/fetch_models.py --provider anthropic

# 列出所有提供商
python scripts/fetch_models.py --list-providers
```

## 核心功能

### 1. 查询模型信息

获取单个模型的完整规格：

```bash
python scripts/fetch_models.py --get <model_id>
```

返回模型的：
- 基本信息（名称、提供商、发布日期）
- 能力（工具调用、推理、文件附件、视觉支持）
- 定价（输入、输出、推理令牌价格）
- 限制（上下文窗口、最大输入/输出）
- 支持的模态（文本、图像、音频、视频）

### 2. 搜索和筛选

根据多个条件搜索模型：

```bash
# 基础搜索
python scripts/search_models.py --query "gpt"

# 高级筛选
python scripts/search_models.py \
  --provider openai \
  --min-context 100000 \
  --max-input-price 10 \
  --tools \
  --vision

# 排序
python scripts/search_models.py \
  --provider anthropic \
  --sort context  # name, context, input_price, output_price
```

**筛选选项：**
- `--query`: 在模型名称中搜索
- `--provider`: 按提供商过滤
- `--min-context`: 最小上下文窗口（令牌）
- `--max-input-price`: 最大输入价格（美元/百万令牌）
- `--max-output-price`: 最大输出价格
- `--vision/--no-vision`: 视觉支持
- `--tools/--no-tools`: 工具调用支持
- `--reasoning`: 推理支持
- `--open-weights`: 仅开源模型
- `--sort`: 排序方式
- `--format`: 输出格式（json/summary）

### 3. 对比模型

生成多个模型的详细对比：

```bash
# Markdown 表格
python scripts/compare_models.py \
  anthropic/claude-3-5-sonnet-20241022 \
  openai/gpt-4o \
  google/gemini-2.0-flash-exp \
  --format markdown

# JSON 数据
python scripts/compare_models.py \
  anthropic/claude-3-5-sonnet-20241022 \
  openai/gpt-4o \
  --format json

# 完整对比（JSON + Markdown 表格 + 摘要）
python scripts/compare_models.py \
  anthropic/claude-3-5-sonnet-20241022 \
  openai/gpt-4o
```

## 数据结构

模型数据包含以下字段：

**基本信息：**
- `name`: 显示名称
- `knowledge`: 知识截止日期
- `release_date`: 发布日期
- `last_updated`: 最后更新日期
- `open_weights`: 是否开源权重

**能力：**
- `tool_call`: 工具调用支持
- `reasoning`: 推理/思维链支持
- `attachment`: 文件附件支持
- `structured_output`: 结构化输出支持

**定价 (cost)：**
- `input`: 输入令牌价格（美元/百万）
- `output`: 输出令牌价格
- `reasoning`: 推理令牌价格（如适用）
- `cache_read`: 缓存读取价格
- `cache_write`: 缓存写入价格

**限制 (limit)：**
- `context`: 上下文窗口大小
- `input`: 最大输入令牌
- `output`: 最大输出令牌

**模态 (modalities)：**
- `input`: 输入模态数组（text、image、audio、video、pdf）
- `output`: 输出模态数组

## 常见用例

**查找支持视觉的模型：**
```bash
python scripts/search_models.py --vision --sort context
```

**查找最便宜的模型：**
```bash
python scripts/search_models.py --max-input-price 5 --sort input_price
```

**对比 Claude 和 GPT：**
```bash
python scripts/compare_models.py \
  anthropic/claude-3-5-sonnet-20241022 \
  openai/gpt-4o
```

**查找开源大上下文模型：**
```bash
python scripts/search_models.py --open-weights --min-context 100000
```

## Model ID 格式

Model ID 使用 AI SDK 标识符格式：`<provider>/<model-name>`

示例：
- `anthropic/claude-3-5-sonnet-20241022`
- `openai/gpt-4o`
- `google/gemini-2.0-flash-exp`
- `meta-llama/llama-3.1-405b-instruct`

## API 端点

数据来源：`https://models.dev/api.json`

提供商 Logo：`https://models.dev/logos/{provider}.svg`

## 脚本说明

- **fetch_models.py**: 数据获取，支持按 ID、提供商查询
- **search_models.py**: 高级搜索和筛选，多条件组合
- **compare_models.py**: 生成对比表格和摘要

所有脚本支持独立执行，无需加载到上下文中。
