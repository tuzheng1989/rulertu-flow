#!/usr/bin/env python3
"""
Sitemap Generation Test Script
测试网站地图生成功能的独立脚本

Usage:
    python test_sitemap.py https://www.anthropic.com
    python test_sitemap.py https://www.bytedance.com --max-pages 30
"""

import json
import sys
import argparse
from datetime import datetime
from urllib.parse import urlparse, urljoin

# 模拟 Playwright 相关类（用于测试逻辑）
class MockPage:
    """Mock Playwright Page for testing"""
    def __init__(self, url, html_content):
        self.url = url
        self.content = html_content
        self.title = "Mock Page"

    async def goto(self, url):
        self.url = url

    async def wait_for_load_state(self, state):
        pass


def generate_company_slug(company_name):
    """生成标准化公司名称"""
    # 移除空格、特殊字符，转小写
    slug = company_name.lower()
    slug = slug.replace(' ', '-').replace('_', '-')
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')
    return slug


def categorize_url(url):
    """根据 URL 分类页面类型"""
    url_lower = url.lower()

    patterns = {
        'about': ['about', 'company', 'who-we-are', 'profile'],
        'product': ['product', 'service', 'solution'],
        'news': ['news', 'blog', 'press', 'media'],
        'contact': ['contact', 'reach-us'],
        'careers': ['career', 'job', 'hiring', 'join-us'],
        'investors': ['investor', 'ir', 'stock']
    }

    for category, keywords in patterns.items():
        if any(kw in url_lower for kw in keywords):
            return category

    return 'other'


def build_test_sitemap(base_url, max_pages=50, max_depth=3):
    """
    构建测试用网站地图

    Args:
        base_url: 网站 URL
        max_pages: 最大页面数
        max_depth: 最大深度

    Returns:
        dict: 网站地图结构
    """
    parsed = urlparse(base_url)
    domain = parsed.netloc

    # 模拟发现的链接
    test_links = [
        # Priority 1: Must visit
        {'url': urljoin(base_url, '/about'), 'text': 'About Us', 'category': 'about'},
        {'url': urljoin(base_url, '/products'), 'text': 'Products', 'category': 'product'},
        {'url': urljoin(base_url, '/company'), 'text': 'Company', 'category': 'about'},

        # Priority 2: Important
        {'url': urljoin(base_url, '/news'), 'text': 'News', 'category': 'news'},
        {'url': urljoin(base_url, '/contact'), 'text': 'Contact', 'category': 'contact'},
        {'url': urljoin(base_url, '/solutions'), 'text': 'Solutions', 'category': 'product'},

        # Priority 3: Optional
        {'url': urljoin(base_url, '/careers'), 'text': 'Careers', 'category': 'careers'},
        {'url': urljoin(base_url, '/pricing'), 'text': 'Pricing', 'category': 'product'},
        {'url': urljoin(base_url, '/blog'), 'text': 'Blog', 'category': 'news'},
    ]

    # 限制数量
    test_links = test_links[:max_pages - 1]  # -1 for homepage

    # 构建网站地图
    sitemap = {
        'url': base_url,
        'title': f'{domain} Homepage',
        'type': 'homepage',
        'visited': True,
        'visited_at': datetime.now().isoformat(),
        'children': []
    }

    # 添加子页面
    for link in test_links[:10]:  # 模拟访问前 10 个
        child_node = {
            'url': link['url'],
            'text': link['text'],
            'type': link['category'],
            'visited': True,
            'visited_at': datetime.now().isoformat(),
            'children': []
        }

        # 为部分页面添加子链接 (深度 2)
        if link['category'] in ['about', 'product']:
            for i in range(2):
                child_child_url = f"{link['url']}/subpage-{i+1}"
                child_node['children'].append({
                    'url': child_child_url,
                    'text': f'Subpage {i+1}',
                    'type': link['category'],
                    'visited': False,
                    'discovered_from': link['url']
                })

        sitemap['children'].append(child_node)

    # 添加未访问的页面
    for link in test_links[10:]:
        sitemap['children'].append({
            'url': link['url'],
            'text': link['text'],
            'type': link['category'],
            'visited': False,
            'children': []
        })

    # 添加元数据
    sitemap['metadata'] = {
        'total_pages': count_total_pages(sitemap),
        'visited_pages': count_visited_pages(sitemap),
        'max_depth': calculate_max_depth(sitemap),
        'generated_at': datetime.now().isoformat(),
        'domain': domain
    }

    return sitemap


def count_total_pages(node):
    """递归计算总页面数"""
    count = 1
    if 'children' in node:
        for child in node['children']:
            count += count_total_pages(child)
    return count


def count_visited_pages(node):
    """递归计算已访问页面数"""
    count = 1 if node.get('visited', False) else 0
    if 'children' in node:
        for child in node['children']:
            count += count_visited_pages(child)
    return count


def calculate_max_depth(node, current_depth=0):
    """递归计算最大深度"""
    if 'children' not in node or not node['children']:
        return current_depth

    max_child_depth = current_depth
    for child in node['children']:
        child_depth = calculate_max_depth(child, current_depth + 1)
        max_child_depth = max(max_child_depth, child_depth)

    return max_child_depth


def validate_sitemap(sitemap):
    """验证网站地图结构"""
    errors = []
    warnings = []

    # 检查必需字段
    required_fields = ['url', 'type', 'visited']
    for field in required_fields:
        if field not in sitemap:
            errors.append(f"Missing required field: {field}")

    # 检查元数据
    if 'metadata' not in sitemap:
        errors.append("Missing metadata section")
    else:
        metadata = sitemap['metadata']

        # 验证统计数据
        total = count_total_pages(sitemap)
        visited = count_visited_pages(sitemap)
        depth = calculate_max_depth(sitemap)

        if metadata.get('total_pages') != total:
            errors.append(f"Metadata total_pages mismatch: {metadata.get('total_pages')} != {total}")

        if metadata.get('visited_pages') != visited:
            errors.append(f"Metadata visited_pages mismatch: {metadata.get('visited_pages')} != {visited}")

        if metadata.get('max_depth') != depth:
            errors.append(f"Metadata max_depth mismatch: {metadata.get('max_depth')} != {depth}")

        # 警告
        if total > 50:
            warnings.append(f"Total pages ({total}) exceeds recommended limit of 50")

        if depth > 3:
            warnings.append(f"Max depth ({depth}) exceeds recommended limit of 3")

        if total < 10:
            warnings.append(f"Total pages ({total}) is below minimum recommended (10)")

    return errors, warnings


def print_sitemap_summary(sitemap):
    """打印网站地图摘要"""
    metadata = sitemap.get('metadata', {})

    print(f"\n{'='*60}")
    print(f"  SITEMAP GENERATION TEST RESULTS")
    print(f"{'='*60}")
    print(f"Domain:        {metadata.get('domain', 'N/A')}")
    print(f"Total Pages:   {metadata.get('total_pages', 0)}")
    print(f"Visited Pages: {metadata.get('visited_pages', 0)}")
    print(f"Max Depth:     {metadata.get('max_depth', 0)}")
    print(f"Generated At:  {metadata.get('generated_at', 'N/A')}")
    print(f"{'='*60}\n")

    # 打印页面分类统计
    categories = {}
    def count_categories(node):
        if 'type' in node:
            categories[node['type']] = categories.get(node['type'], 0) + 1
        if 'children' in node:
            for child in node['children']:
                count_categories(child)

    count_categories(sitemap)

    print("Page Categories:")
    for category, count in sorted(categories.items()):
        print(f"  {category:15} {count:3} pages")


def main():
    parser = argparse.ArgumentParser(
        description='Test sitemap generation functionality'
    )
    parser.add_argument('url', help='Website URL to test')
    parser.add_argument('--max-pages', type=int, default=50,
                       help='Maximum pages to discover (default: 50)')
    parser.add_argument('--max-depth', type=int, default=3,
                       help='Maximum depth to crawl (default: 3)')
    parser.add_argument('--output', '-o', help='Output JSON file path')

    args = parser.parse_args()

    print(f"\n🔍 Testing sitemap generation for: {args.url}")
    print(f"   Max pages: {args.max_pages}, Max depth: {args.max_depth}")

    # 生成网站地图
    sitemap = build_test_sitemap(
        args.url,
        max_pages=args.max_pages,
        max_depth=args.max_depth
    )

    # 验证
    errors, warnings = validate_sitemap(sitemap)

    # 打印摘要
    print_sitemap_summary(sitemap)

    # 显示警告和错误
    if warnings:
        print("\n⚠️  Warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print("\n❌ Errors:")
        for error in errors:
            print(f"  - {error}")
        return 1

    # 保存到文件
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(sitemap, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Sitemap saved to: {args.output}")

    print("\n✅ All tests passed!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
