# Deep Research Skill - 安装指南

## 快速安装

### 方法 1: 安装到用户目录（推荐）

```bash
# 复制到用户 skill 目录
cp -r deep-research ~/.claude/skills/
```

### 方法 2: 安装到全局 skill 目录

```bash
# 复制到 skillResearch 目录
cp -r deep-research /path/to/skillResearch/skills/
```

## 依赖确认

### 必需 MCP 工具

本项目全局规则强制使用以下 MCP 工具进行网络访问（禁止内置 WebSearch / WebFetch）：

| 工具 | 用途 |
|------|------|
| **mcp__web-search-prime__web_search_prime** | 网络搜索（参数：search_query / content_size / location / search_recency_filter） |
| **mcp__web-reader__webReader** | 网页全文抓取（参数：url / return_format） |

这两个工具由项目 MCP 配置提供，无需额外安装，也不依赖 Playwright 或 meta-search skill。

## 验证安装

### 1. 检查文件结构

```bash
ls -la ~/.claude/skills/deep-research/
```

应该看到：
```
SKILL.md
README.md
config.json
agents/
scripts/
docs/
```

### 2. 测试状态管理

```bash
cd ~/.claude/skills/deep-research/scripts
python state_manager.py list
```

预期输出：
```
没有找到任何检查点
```

### 3. 运行测试套件

```bash
cd ~/.claude/skills/deep-research/scripts
python test_state_manager.py
```

预期输出：31/31 测试通过

## 首次使用

### 在 Claude Code 中

```
用户: 帮我深入研究"人工智能在医疗诊断中的应用"
```

### 命令行测试

```bash
cd ~/.claude/skills/deep-research/scripts

# 运行简单测试
python orchestrator.py "测试主题" --loops 1
```

## 故障排查

### 问题 1: Skill 未触发

**症状**: 说"深入研究XX"没有响应

**解决方案**:
1. 确认 SKILL.md 在正确位置
2. 检查 SKILL.md 中的触发条件格式
3. 重启 Claude Code

### 问题 2: 搜索失败

**症状**: 报告"搜索失败"或 MCP 工具不可用

**解决方案**:
1. 确认 MCP 工具 `mcp__web-search-prime__web_search_prime` 已在本项目配置
2. 确认 MCP 工具 `mcp__web-reader__webReader` 已配置
3. 在会话中单独调用搜索工具，排查 MCP 连接状态

### 问题 3: 状态保存失败

**症状**: 报告"无法保存检查点"

**解决方案**:
```bash
# 创建检查点目录
mkdir -p ~/.claude/deep-research/checkpoints
mkdir -p ~/.claude/deep-research/reports
```

### 问题 4: Python 脚本无法运行

**症状**: "ModuleNotFoundError"

**解决方案**:
```bash
# 确认 Python 3.8+
python --version

# 安装依赖（如果需要）
pip install dataclasses
```

## 卸载

```bash
# 删除 skill
rm -rf ~/.claude/skills/deep-research

# 清理数据（可选）
rm -rf ~/.claude/deep-research
```

## 更新

```bash
# 备份配置
cp -r ~/.claude/skills/deep-research ~/deep-research-backup

# 删除旧版本
rm -rf ~/.claude/skills/deep-research

# 安装新版本
cp -r /path/to/new/deep-research ~/.claude/skills/

# 恢复配置（如果需要）
# cp ~/deep-research-backup/config.json ~/.claude/skills/deep-research/
```

## 下一步

安装完成后，建议阅读：
- [README.md](README.md) - 使用方法和示例
- [SKILL.md](SKILL.md) - 触发条件和执行流程
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - 架构设计
