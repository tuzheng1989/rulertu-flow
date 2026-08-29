#!/usr/bin/env python3
"""
对比多个模型
"""
import json
import sys
from typing import Any
from fetch_models import fetch_models, get_model_by_id


def format_price(value: float) -> str:
    """格式化价格"""
    if value == 0:
        return "免费"
    return f"${value:.2f}"


def format_number(value: int) -> str:
    """格式化数字"""
    return f"{value:,}"


def compare_models(model_ids: list[str], data: dict = None) -> dict:
    """
    对比多个模型

    Args:
        model_ids: 要对比的模型 ID 列表
        data: 可选的预加载数据

    Returns:
        包含对比结果的字典
    """
    if data is None:
        data = fetch_models()

    models = []
    for model_id in model_ids:
        model = get_model_by_id(model_id, data)
        if model:
            models.append({**model, "id": model_id})
        else:
            print(f"警告: 未找到模型 {model_id}", file=sys.stderr)

    return models


def generate_comparison_table(models: list[dict]) -> str:
    """
    生成 Markdown 格式的对比表格

    Args:
        models: 模型列表

    Returns:
        Markdown 表格字符串
    """
    if not models:
        return "无模型可对比"

    # 表头
    headers = ["属性", *[m.get("name", m["id"]) for m in models]]

    # 构建行数据
    rows = []

    # 基本信息
    rows.append(["模型 ID", *[m["id"] for m in models]])

    # 能力
    rows.append([
        "工具调用",
        *["✅" if m.get("tool_call") else "❌" for m in models]
    ])
    rows.append([
        "推理",
        *["✅" if m.get("reasoning") else "❌" for m in models]
    ])
    rows.append([
        "文件附件",
        *["✅" if m.get("attachment") else "❌" for m in models]
    ])
    rows.append([
        "结构化输出",
        *["✅" if m.get("structured_output") else "❌" for m in models]
    ])

    # 模态
    def format_modalities(m):
        modalities = m.get("modalities", {})
        input_modes = modalities.get("input", [])
        output_modes = modalities.get("output", [])
        return f"输入: {', '.join(input_modes)}\n输出: {', '.join(output_modes)}"

    rows.append(["支持模态", *[format_modalities(m) for m in models]])

    # 价格
    def format_cost(m):
        cost = m.get("cost", {})
        parts = []
        if "input" in cost:
            parts.append(f"输入: {format_price(cost['input'])}")
        if "output" in cost:
            parts.append(f"输出: {format_price(cost['output'])}")
        if "reasoning" in cost:
            parts.append(f"推理: {format_price(cost['reasoning'])}")
        return "\n".join(parts)

    rows.append(["价格 (每百万令牌)", *[format_cost(m) for m in models]])

    # 限制
    def format_limits(m):
        limit = m.get("limit", {})
        parts = []
        if "context" in limit:
            parts.append(f"上下文: {format_number(limit['context'])}")
        if "input" in limit:
            parts.append(f"最大输入: {format_number(limit['input'])}")
        if "output" in limit:
            parts.append(f"最大输出: {format_number(limit['output'])}")
        return "\n".join(parts)

    rows.append(["令牌限制", *[format_limits(m) for m in models]])

    # 其他信息
    rows.append([
        "开源权重",
        *["✅" if m.get("open_weights") else "❌" for m in models]
    ])

    knowledge_dates = [m.get("knowledge", "未知") for m in models]
    rows.append(["知识截止日期", *knowledge_dates])

    release_dates = [m.get("release_date", "未知") for m in models]
    rows.append(["发布日期", *release_dates])

    # 构建 Markdown 表格
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")

    for row in rows:
        # 处理换行符，替换为 <br>
        formatted_row = [str(cell).replace("\n", "<br>") for cell in row]
        lines.append("| " + " | ".join(formatted_row) + " |")

    return "\n".join(lines)


def generate_summary(models: list[dict]) -> str:
    """
    生成对比摘要

    Args:
        models: 模型列表

    Returns:
        摘要字符串
    """
    if not models:
        return "无模型可对比"

    lines = []
    lines.append("# 模型对比摘要\n")

    # 找出最佳选项
    best_input_price = min(models, key=lambda m: m.get("cost", {}).get("input", float('inf')))
    best_output_price = min(models, key=lambda m: m.get("cost", {}).get("output", float('inf')))
    best_context = max(models, key=lambda m: m.get("limit", {}).get("context", 0))

    lines.append(f"## 💰 最便宜输入价格: {best_input_price.get('name')}")
    lines.append(f"${best_input_price.get('cost', {}).get('input', 0):.2f} / 百万令牌\n")

    lines.append(f"## 💸 最便宜输出价格: {best_output_price.get('name')}")
    lines.append(f"${best_output_price.get('cost', {}).get('output', 0):.2f} / 百万令牌\n")

    lines.append(f"## 📏 最大上下文: {best_context.get('name')}")
    lines.append(f"{best_context.get('limit', {}).get('context', 0):,} 令牌\n")

    # 能力对比
    tools_models = [m.get("name") for m in models if m.get("tool_call")]
    reasoning_models = [m.get("name") for m in models if m.get("reasoning")]
    vision_models = []
    for m in models:
        modalities = m.get("modalities", {}).get("input", [])
        if "image" in modalities or "video" in modalities:
            vision_models.append(m.get("name"))

    if tools_models:
        lines.append(f"## 🔧 支持工具调用: {', '.join(tools_models)}\n")
    if reasoning_models:
        lines.append(f"## 🧠 支持推理: {', '.join(reasoning_models)}\n")
    if vision_models:
        lines.append(f"## 👁️ 支持视觉: {', '.join(vision_models)}\n")

    return "\n".join(lines)


def main():
    """CLI 入口点"""
    if len(sys.argv) < 2:
        print("用法: compare_models.py <model_id1> <model_id2> ... [--format json|markdown|both]",
              file=sys.stderr)
        sys.exit(1)

    model_ids = sys.argv[1:]
    format_type = "both"

    # 移除格式选项
    if "--format" in model_ids:
        idx = model_ids.index("--format")
        if idx + 1 < len(model_ids):
            format_type = model_ids[idx + 1]
        model_ids = model_ids[:idx] + model_ids[idx + 2:]

    if not model_ids:
        print("错误: 必须提供至少一个模型 ID", file=sys.stderr)
        sys.exit(1)

    # 对比模型
    models = compare_models(model_ids)

    if not models:
        print("错误: 未找到任何有效的模型", file=sys.stderr)
        sys.exit(1)

    if format_type in ["json", "both"]:
        if format_type == "both":
            print("# JSON 数据\n")
        print(json.dumps(models, indent=2, ensure_ascii=False))
        if format_type == "both":
            print("\n")

    if format_type in ["markdown", "both"]:
        if format_type == "both":
            print("# 对比表格\n")
        print(generate_comparison_table(models))
        print("\n")
        if format_type == "both":
            print(generate_summary(models))


if __name__ == "__main__":
    main()
