#!/usr/bin/env python3
"""
搜索和过滤模型
"""
import json
import sys
from typing import Any
from fetch_models import fetch_models


def search_models(
    data: dict,
    query: str = None,
    provider: str = None,
    min_context: int = None,
    max_price_input: float = None,
    max_price_output: float = None,
    supports_vision: bool = None,
    supports_tools: bool = None,
    supports_reasoning: bool = None,
    open_weights: bool = None,
) -> list[dict]:
    """
    根据多个条件搜索和过滤模型

    Args:
        data: 模型数据字典
        query: 在模型名称中搜索的文本
        provider: 按提供商过滤
        min_context: 最小上下文窗口大小（令牌）
        max_price_input: 最大输入价格（美元/百万令牌）
        max_price_output: 最大输出价格（美元/百万令牌）
        supports_vision: 是否支持视觉输入
        supports_tools: 是否支持工具调用
        supports_reasoning: 是否支持推理
        open_weights: 是否开源权重

    Returns:
        匹配的模型列表
    """
    results = []

    for model_id, model_data in data.items():
        # 添加模型 ID 到结果中
        model_info = {**model_data, "id": model_id}

        # 提供商过滤
        if provider:
            model_provider = model_id.split('/')[0]
            if model_provider != provider:
                continue

        # 名称搜索
        if query:
            name = model_data.get("name", "").lower()
            if query.lower() not in name:
                continue

        # 上下文窗口过滤
        if min_context:
            context = model_data.get("limit", {}).get("context", 0)
            if context < min_context:
                continue

        # 价格过滤
        if max_price_input:
            input_price = model_data.get("cost", {}).get("input", float('inf'))
            if input_price > max_price_input:
                continue

        if max_price_output:
            output_price = model_data.get("cost", {}).get("output", float('inf'))
            if output_price > max_price_output:
                continue

        # 能力过滤
        if supports_vision is not None:
            modalities = model_data.get("modalities", {})
            input_modes = modalities.get("input", [])
            has_vision = "image" in input_modes or "video" in input_modes
            if has_vision != supports_vision:
                continue

        if supports_tools is not None:
            if model_data.get("tool_call", False) != supports_tools:
                continue

        if supports_reasoning is not None:
            if model_data.get("reasoning", False) != supports_reasoning:
                continue

        if open_weights is not None:
            if model_data.get("open_weights", False) != open_weights:
                continue

        results.append(model_info)

    return results


def sort_models(models: list[dict], sort_by: str = "name") -> list[dict]:
    """
    对模型列表排序

    Args:
        models: 模型列表
        sort_by: 排序字段 (name, context, input_price, output_price)

    Returns:
        排序后的模型列表
    """
    if sort_by == "name":
        return sorted(models, key=lambda m: m.get("name", ""))
    elif sort_by == "context":
        return sorted(models, key=lambda m: m.get("limit", {}).get("context", 0), reverse=True)
    elif sort_by == "input_price":
        return sorted(models, key=lambda m: m.get("cost", {}).get("input", float('inf')))
    elif sort_by == "output_price":
        return sorted(models, key=lambda m: m.get("cost", {}).get("output", float('inf')))
    else:
        return models


def format_model_summary(model: dict) -> str:
    """
    格式化单个模型的简要信息

    Args:
        model: 模型数据

    Returns:
        格式化的字符串
    """
    name = model.get("name", "Unknown")
    model_id = model.get("id", "Unknown")

    # 能力标记
    capabilities = []
    if model.get("tool_call"):
        capabilities.append("🔧")
    if model.get("reasoning"):
        capabilities.append("🧠")
    if model.get("attachment"):
        capabilities.append("📎")

    modalities = model.get("modalities", {})
    input_modes = modalities.get("input", [])
    if "image" in input_modes:
        capabilities.append("👁️")

    caps_str = " ".join(capabilities) if capabilities else ""

    # 定价
    cost = model.get("cost", {})
    input_price = cost.get("input", 0)
    output_price = cost.get("output", 0)

    # 上下文
    limit = model.get("limit", {})
    context = limit.get("context", 0)

    return (
        f"• {name} ({model_id}) {caps_str}\n"
        f"  价格: ${input_price:.2f}/${output_price:.2f} (输入/输出, 每百万令牌)\n"
        f"  上下文: {context:,} 令牌"
    )


def main():
    """CLI 入口点"""
    import argparse

    parser = argparse.ArgumentParser(description="搜索和过滤 AI 模型")
    parser.add_argument("--query", "-q", help="在模型名称中搜索")
    parser.add_argument("--provider", "-p", help="按提供商过滤")
    parser.add_argument("--min-context", type=int, help="最小上下文窗口")
    parser.add_argument("--max-input-price", type=float, help="最大输入价格")
    parser.add_argument("--max-output-price", type=float, help="最大输出价格")
    parser.add_argument("--vision", action="store_true", help="仅支持视觉的模型")
    parser.add_argument("--no-vision", action="store_true", help="仅不支持视觉的模型")
    parser.add_argument("--tools", action="store_true", help="仅支持工具调用的模型")
    parser.add_argument("--no-tools", action="store_true", help="仅不支持工具调用的模型")
    parser.add_argument("--reasoning", action="store_true", help="仅支持推理的模型")
    parser.add_argument("--open-weights", action="store_true", help="仅开源模型")
    parser.add_argument("--sort", choices=["name", "context", "input_price", "output_price"],
                       default="name", help="排序方式")
    parser.add_argument("--format", choices=["json", "summary"], default="summary",
                       help="输出格式")

    args = parser.parse_args()

    # 加载数据
    data = fetch_models()

    # 构建过滤参数
    filters = {"data": data}

    if args.query:
        filters["query"] = args.query
    if args.provider:
        filters["provider"] = args.provider
    if args.min_context:
        filters["min_context"] = args.min_context
    if args.max_input_price:
        filters["max_price_input"] = args.max_input_price
    if args.max_output_price:
        filters["max_price_output"] = args.max_output_price

    # 处理布尔标志
    supports_vision = None
    if args.vision:
        supports_vision = True
    elif args.no_vision:
        supports_vision = False
    if supports_vision is not None:
        filters["supports_vision"] = supports_vision

    supports_tools = None
    if args.tools:
        supports_tools = True
    elif args.no_tools:
        supports_tools = False
    if supports_tools is not None:
        filters["supports_tools"] = supports_tools

    if args.reasoning:
        filters["supports_reasoning"] = True

    if args.open_weights:
        filters["open_weights"] = True

    # 搜索
    results = search_models(**filters)

    # 排序
    results = sort_models(results, args.sort)

    # 输出
    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        if not results:
            print("未找到匹配的模型")
        else:
            print(f"找到 {len(results)} 个模型:\n")
            for model in results:
                print(format_model_summary(model))
                print()


if __name__ == "__main__":
    main()
