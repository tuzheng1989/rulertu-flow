"""copyright-skills 脚本测试共享设施（B3）。

职责：
1. 提供脚本路径与按文件路径加载模块的 fixture（scripts/ 目录不是包）；
2. 提供 CLI subprocess 运行器；
3. 提供迷你仓库构造器；
4. autouse 隔离 git：测试仓库一律按"非 git 目录"处理，保证 fixtures 不依赖
   外层工作区是否恰好存在 .git（经 2026-09-03 实测，ceiling 目录生效时
   `git ls-files` 以 exit 128 失败，脚本捕获后返回 None）。

本批不测 soffice 渲染、不依赖网络。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CN_SCRIPTS = PLUGIN_ROOT / "skills" / "software-copyright-cn" / "scripts"
REVIEW_SCRIPTS = PLUGIN_ROOT / "skills" / "copyright-code-review" / "scripts"

# 1x1 透明 PNG，供 build_manual_docx 的 add_picture 使用
TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c63000100000500010d0a2db40000"
    "000049454e44ae426082"
)


@pytest.fixture(autouse=True)
def _isolate_git(monkeypatch, tmp_path):
    """让所有子进程 git 调用把 tmp_path 视为顶层，稳定命中"非 git 目录"分支。"""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))


@pytest.fixture(scope="session")
def scripts() -> SimpleNamespace:
    """六个被测脚本的绝对路径。"""
    return SimpleNamespace(
        inventory_repo=CN_SCRIPTS / "inventory_repo.py",
        build_source_docx=CN_SCRIPTS / "build_source_docx.py",
        build_manual_docx=CN_SCRIPTS / "build_manual_docx.py",
        registration_form=CN_SCRIPTS / "registration_form.py",
        scan_source=REVIEW_SCRIPTS / "scan_source.py",
        similarity_check=REVIEW_SCRIPTS / "similarity_check.py",
    )


@pytest.fixture()
def load_module():
    """按文件路径加载脚本目录下的模块（目录不是包）。

    先注册进 sys.modules 再 exec，因此 similarity_check.py 内的
    `from scan_source import ...` 也能解析（需先加载 scan_source）。
    """

    def _load(name: str, directory: Path):
        if name in sys.modules:
            return sys.modules[name]
        spec = importlib.util.spec_from_file_location(name, directory / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    return _load


@pytest.fixture()
def run_cli(tmp_path):
    """以 subprocess 方式运行脚本 CLI，返回 CompletedProcess（text 模式）。"""

    def _run(script: Path, *args: str):
        return subprocess.run(
            [sys.executable, str(script), *[str(a) for a in args]],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=tmp_path,
        )

    return _run


@pytest.fixture()
def write_tree(tmp_path):
    """在 tmp_path/repo 下按 {相对路径: 内容} 构造文件，返回仓库根目录。

    str 内容按 utf-8 写入；bytes 内容原样写入（用于 GB18030 等非 utf-8 样本）。
    """

    def _write(mapping: dict, base: Path | None = None) -> Path:
        root = base if base is not None else tmp_path / "repo"
        for rel, content in mapping.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            data = content.encode("utf-8") if isinstance(content, str) else content
            target.write_bytes(data)
        return root

    return _write


@pytest.fixture()
def tiny_png() -> bytes:
    return TINY_PNG


@pytest.fixture()
def make_lines():
    """生成 n 行文本（可控制是否带尾换行），行内容互不相同。"""

    def _make(count: int, *, trailing_newline: bool = True, prefix: str = "line") -> str:
        body = "\n".join(f"{prefix}_{i:04d}" for i in range(1, count + 1))
        return body + ("\n" if trailing_newline else "")

    return _make
