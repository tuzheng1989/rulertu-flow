#!/usr/bin/env python3
"""
Deep Research Skill - State Manager

研究状态管理模块，负责：
1. 研究状态的创建、保存、加载
2. 来源去重和累积
3. 循环控制逻辑
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class ResearchState:
    """研究状态数据类"""

    # === 基础信息 ===
    research_topic: str              # 研究主题
    max_loops: int = 3               # 最大循环次数
    loop_count: int = 0              # 当前循环次数

    # === 研究简报（clarify + brief 阶段产出，v0.4.0 新增） ===
    research_brief: str = ""         # 研究简报：范围/受众/深度/必须覆盖的维度清单

    # === 查询与搜索 ===
    search_query: str = ""           # 兼容字段（单查询，旧路径使用）
    search_queries: List[str] = field(default_factory=list)  # 当前轮查询列表（多查询并行）
    search_results: List[Dict] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)

    # === 摘要与反思 ===
    running_summary: str = ""        # 累积摘要（可能经 compress 节点压缩）
    knowledge_gaps: List[str] = field(default_factory=list)

    # === 元数据 ===
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    session_id: str = field(default_factory=lambda: hashlib.md5(
        datetime.now().isoformat().encode()
    ).hexdigest()[:8])

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ResearchState":
        """从字典反序列化"""
        # 过滤掉额外的字段
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)

    def save(self, filepath: Optional[str] = None):
        """保存到文件"""
        if filepath is None:
            # 默认保存到用户目录下的 .claude/deep-research/checkpoints/
            checkpoint_dir = Path.home() / ".claude" / "deep-research" / "checkpoints"
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            filepath = str(checkpoint_dir / f"{self.session_id}.json")

        self.updated_at = datetime.now().isoformat()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return filepath

    @classmethod
    def load(cls, filepath: str) -> "ResearchState":
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def _normalize_url(self, url: str) -> Optional[str]:
        """
        标准化 URL 用于去重比较

        - 解析 URL
        - 转换为小写（域名部分）
        - 移除端口号（如果不是标准的 80/443）
        - 保留路径、查询参数和片段
        - 处理各种格式变体

        Returns:
            标准化的 URL，如果输入不是有效 URL 则返回 None
        """
        if not url or not isinstance(url, str):
            return None

        url = url.strip()

        # 移除常见的 URL 包裹字符
        for prefix in ["[", "(", "<"]:
            if url.startswith(prefix):
                url = url[1:]
        for suffix in ["]", ")", ">"]:
            if url.endswith(suffix):
                url = url[:-1]

        # 检查是否是有效的 URL
        if not url.startswith(("http://", "https://", "ftp://")):
            return None

        try:
            parsed = urlparse(url)
            # 重建 URL：标准化域名，保留其他组件
            netloc = parsed.netloc.lower()
            # 移除默认端口号
            if (parsed.scheme == "http" and netloc.endswith(":80")) or \
               (parsed.scheme == "https" and netloc.endswith(":443")):
                netloc = netloc.rsplit(":", 1)[0]

            # 重建 URL（不包含片段，因为通常指向同一页面）
            normalized = f"{parsed.scheme}://{netloc}{parsed.path}"
            if parsed.query:
                normalized += f"?{parsed.query}"
            return normalized
        except Exception:
            return None

    def _extract_url_from_source(self, source: str) -> Optional[str]:
        """
        从来源字符串中提取 URL

        支持多种格式：
        - "[标题](https://example.com) - 说明"
        - "https://example.com"
        - "标题 - (https://example.com)"
        - "[标题]https://example.com"
        - "标题 - https://example.com"

        Returns:
            提取并标准化的 URL，如果找不到则返回 None
        """
        if not source or not isinstance(source, str):
            return None

        # 尝试直接作为 URL 解析
        direct_url = self._normalize_url(source)
        if direct_url:
            return direct_url

        # 尝试从 Markdown 链接格式提取
        import re
        # 匹配 [标题](URL) 或 [标题](URL "说明")
        markdown_link = re.search(r'\[([^\]]+)\]\(([^)]+)\)', source)
        if markdown_link:
            url = markdown_link.group(2).split()[0]  # 取第一个空格前的部分
            return self._normalize_url(url)

        # 尝试从类似 "标题 - URL" 格式提取
        if " - " in source:
            parts = source.split(" - ")
            for part in reversed(parts):  # URL 通常在最后
                url = self._normalize_url(part.strip())
                if url:
                    return url

        # 尝试找到任何 http:// 或 https:// 开头的 URL
        urls = re.findall(r'https?://[^\s\)\]\}>"\' ]+', source)
        if urls:
            return self._normalize_url(urls[0])

        return None

    def add_sources(self, new_sources: List[str]) -> int:
        """
        添加新来源，自动去重

        使用 URL 作为唯一标识进行去重，支持多种来源格式。

        Returns:
            int: 实际添加的来源数量
        """
        # 收集现有来源的所有标准化 URL
        existing_urls: Set[str] = set()
        for source in self.sources:
            url = self._extract_url_from_source(source)
            if url:
                existing_urls.add(url)

        added_count = 0
        for source in new_sources:
            # 提取并标准化 URL
            url = self._extract_url_from_source(source)

            # 如果提取不到 URL，仍然添加来源（非 URL 类来源）
            if url is None:
                self.sources.append(source)
                added_count += 1
            # 如果是有效的 URL 且未重复
            elif url not in existing_urls:
                self.sources.append(source)
                existing_urls.add(url)
                added_count += 1

        return added_count

    def should_continue(self) -> bool:
        """判断是否应该继续研究"""
        return self.loop_count < self.max_loops

    def get_progress(self) -> str:
        """获取当前进度描述"""
        return f"{self.loop_count}/{self.max_loops}"

    def get_summary(self) -> Dict:
        """获取状态摘要"""
        return {
            "topic": self.research_topic,
            "progress": self.get_progress(),
            "sources_count": len(self.sources),
            "gaps_count": len(self.knowledge_gaps),
            "summary_length": len(self.running_summary),
        }


def create_state(research_topic: str, max_loops: int = 3) -> ResearchState:
    """创建新的研究状态"""
    return ResearchState(
        research_topic=research_topic,
        max_loops=max_loops
    )


def save_checkpoint(state: ResearchState) -> str:
    """保存检查点"""
    return state.save()


def load_latest_checkpoint() -> Optional[ResearchState]:
    """加载最新的检查点"""
    checkpoint_dir = Path.home() / ".claude" / "deep-research" / "checkpoints"
    if not checkpoint_dir.exists():
        return None

    checkpoints = list(checkpoint_dir.glob("*.json"))
    if not checkpoints:
        return None

    # 按修改时间排序，取最新的
    latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
    return ResearchState.load(str(latest))


def list_checkpoints() -> List[Dict]:
    """列出所有检查点"""
    checkpoint_dir = Path.home() / ".claude" / "deep-research" / "checkpoints"
    if not checkpoint_dir.exists():
        return []

    checkpoints = []
    for filepath in checkpoint_dir.glob("*.json"):
        try:
            state = ResearchState.load(str(filepath))
            checkpoints.append({
                "session_id": state.session_id,
                "topic": state.research_topic,
                "progress": state.get_progress(),
                "created_at": state.created_at,
                "updated_at": state.updated_at,
                "filepath": str(filepath),
            })
        except Exception:
            continue

    # 按创建时间倒序
    checkpoints.sort(key=lambda x: x["created_at"], reverse=True)
    return checkpoints


# CLI 接口
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "list":
            # 列出所有检查点
            checkpoints = list_checkpoints()
            if not checkpoints:
                print("没有找到任何检查点")
            else:
                print(f"找到 {len(checkpoints)} 个检查点:")
                for cp in checkpoints:
                    print(f"  [{cp['session_id']}] {cp['topic']} ({cp['progress']}) - {cp['updated_at']}")

        elif cmd == "load":
            # 加载最新检查点
            state = load_latest_checkpoint()
            if state:
                print(f"加载检查点: {state.session_id}")
                print(f"  主题: {state.research_topic}")
                print(f"  进度: {state.get_progress()}")
                print(f"  来源: {len(state.sources)} 个")
                print(f"  缺口: {len(state.knowledge_gaps)} 个")
            else:
                print("没有找到检查点")

        elif cmd == "clean":
            # 清理所有检查点
            checkpoint_dir = Path.home() / ".claude" / "deep-research" / "checkpoints"
            if checkpoint_dir.exists():
                for filepath in checkpoint_dir.glob("*.json"):
                    filepath.unlink()
                print(f"已清理 {len(list(checkpoint_dir.glob('*.json')))} 个检查点")
            else:
                print("检查点目录不存在")

        else:
            print(f"未知命令: {cmd}")
            print("可用命令: list, load, clean")
    else:
        print("Deep Research State Manager")
        print("用法: python state_manager.py <command>")
        print("命令:")
        print("  list  - 列出所有检查点")
        print("  load  - 加载最新检查点")
        print("  clean - 清理所有检查点")
