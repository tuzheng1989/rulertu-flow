#!/usr/bin/env python3
"""
安装脚本 - MD to PDF Skill

自动安装所有依赖项，包括 Python 包和 Playwright 浏览器。
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """运行命令并显示进度"""
    print(f"\n{'='*60}")
    print(f"正在执行: {description}")
    print(f"命令: {' '.join(cmd)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"错误: {e}", file=sys.stderr)
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return False


def install_python_packages():
    """安装 Python 依赖包"""
    print("\n📦 安装 Python 依赖包...")

    requirements_file = Path(__file__).parent.parent / "requirements.txt"

    if requirements_file.exists():
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]
    else:
        # 直接安装核心依赖
        cmd = [
            sys.executable, "-m", "pip", "install",
            "playwright>=1.40.0",
            "markdown2>=2.4.12",
            "pygments>=2.17.2"
        ]

    return run_command(cmd, "安装 Python 包")


def install_playwright_browsers():
    """安装 Playwright 浏览器"""
    print("\n🌐 安装 Playwright 浏览器...")

    # 安装 chromium 浏览器
    cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
    return run_command(cmd, "安装 Chromium 浏览器")


def verify_installation():
    """验证安装是否成功"""
    print("\n✅ 验证安装...")

    try:
        # 检查 Python 包
        import playwright
        import markdown2
        import pygments

        print(f"✓ playwright {playwright.__version__}")
        print(f"✓ markdown2 {markdown2.__version__}")
        print(f"✓ pygments {pygments.__version__}")

        # 检查浏览器
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
            print("✓ Chromium 浏览器可用")

        return True

    except ImportError as e:
        print(f"✗ 导入错误: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ 验证错误: {e}", file=sys.stderr)
        return False


def create_test_output():
    """创建测试输出目录"""
    output_dir = Path(__file__).parent.parent / "assets" / "test_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 测试输出目录: {output_dir}")
    return str(output_dir)


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║           MD to PDF Skill - 安装向导                      ║
║                                                           ║
║           Markdown 转 PDF，完美支持 Mermaid 流程图        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # 检查 Python 版本
    if sys.version_info < (3, 8):
        print(f"✗ 错误: 需要 Python 3.8 或更高版本，当前版本: {sys.version}")
        sys.exit(1)

    print(f"✓ Python 版本: {sys.version}")

    # 安装 Python 包
    if not install_python_packages():
        print("\n✗ Python 包安装失败", file=sys.stderr)
        print("\n💡 提示: 您可以手动运行以下命令安装：")
        print("   pip install playwright markdown2 pygments")
        sys.exit(1)

    # 安装 Playwright 浏览器
    if not install_playwright_browsers():
        print("\n✗ Playwright 浏览器安装失败", file=sys.stderr)
        print("\n💡 提示: 您可以手动运行以下命令安装：")
        print("   python -m playwright install chromium")
        sys.exit(1)

    # 验证安装
    if not verify_installation():
        print("\n✗ 安装验证失败", file=sys.stderr)
        sys.exit(1)

    # 创建测试输出目录
    test_dir = create_test_output()

    # 显示成功信息
    print(f"""
{'='*60}
✅ 安装完成！

📚 快速开始:

  # 转换单个文件
  python scripts/md_to_pdf.py assets/example.md -o {test_dir}/example.pdf

  # 使用自定义样式
  python scripts/md_to_pdf.py input.md --style assets/custom.css --toc

  # 批量转换
  python scripts/md_to_pdf.py ./docs --batch --output-dir ./pdfs

📖 更多信息请参阅: SKILL.md

{'='*60}
    """)


if __name__ == "__main__":
    main()
