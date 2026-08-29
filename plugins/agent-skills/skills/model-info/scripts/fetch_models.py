#!/usr/bin/env python3
"""
从 models.dev API 获取模型数据
"""
import json
import sys
from urllib.request import urlopen
from urllib.error import URLError


def fetch_models(api_url: str = "https://models.dev/api.json") -> dict:
    """
    从 models.dev API 获取所有模型数据

    返回展平后的模型数据，键为 "provider/model_id" 格式

    Args:
        api_url: API 端点 URL

    Returns:
        包含所有模型数据的字典

    Raises:
        URLError: 当网络请求失败时
        json.JSONDecodeError: 当 JSON 解析失败时
    """
    try:
        from urllib.request import Request
        req = Request(api_url)
        req.add_header('User-Agent', 'model-info-skill/1.0')
        with urlopen(req, timeout=10) as response:
            raw_data = json.loads(response.read().decode('utf-8'))

        # 展平数据结构: { "provider/model_id": model_data }
        flattened = {}
        for provider_id, provider_data in raw_data.items():
            if isinstance(provider_data, dict) and "models" in provider_data:
                for model_id, model_data in provider_data["models"].items():
                    full_id = f"{provider_id}/{model_id}"
                    flattened[full_id] = model_data

        return flattened
    except URLError as e:
        print(f"错误: 无法连接到 models.dev API - {e}", file=sys.stderr)
        raise
    except json.JSONDecodeError as e:
        print(f"错误: 无法解析 JSON 响应 - {e}", file=sys.stderr)
        raise


def get_model_by_id(model_id: str, data: dict = None) -> dict | None:
    """
    根据 Model ID 获取特定模型信息

    Args:
        model_id: 模型 ID (例如: "anthropic/claude-3-5-sonnet-20241022")
        data: 可选的预加载数据，如果为 None 则从 API 获取

    Returns:
        模型信息字典，如果未找到则返回 None
    """
    if data is None:
        data = fetch_models()

    return data.get(model_id)


def list_models_by_provider(provider_id: str, data: dict = None) -> list[dict]:
    """
    列出指定提供商的所有模型

    Args:
        provider_id: 提供商 ID (例如: "anthropic", "openai")
        data: 可选的预加载数据，如果为 None 则从 API 获取

    Returns:
        该提供商的模型列表
    """
    if data is None:
        data = fetch_models()

    prefix = f"{provider_id}/"
    return [
        {**model_data, "id": model_id}
        for model_id, model_data in data.items()
        if model_id.startswith(prefix)
    ]


def main():
    """CLI 入口点"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list-providers":
            # 列出所有提供商
            data = fetch_models()
            providers = set(model_id.split('/')[0] for model_id in data.keys())
            print("\n".join(sorted(providers)))
        elif sys.argv[1] == "--get":
            # 获取特定模型
            if len(sys.argv) < 3:
                print("用法: --get <model_id>", file=sys.stderr)
                sys.exit(1)
            model = get_model_by_id(sys.argv[2])
            if model:
                print(json.dumps(model, indent=2, ensure_ascii=False))
            else:
                print(f"未找到模型: {sys.argv[2]}", file=sys.stderr)
                sys.exit(1)
        elif sys.argv[1] == "--provider":
            # 列出提供商的所有模型
            if len(sys.argv) < 3:
                print("用法: --provider <provider_id>", file=sys.stderr)
                sys.exit(1)
            models = list_models_by_provider(sys.argv[2])
            print(json.dumps(models, indent=2, ensure_ascii=False))
        else:
            print("未知命令", file=sys.stderr)
            sys.exit(1)
    else:
        # 输出所有数据
        print(json.dumps(fetch_models(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
