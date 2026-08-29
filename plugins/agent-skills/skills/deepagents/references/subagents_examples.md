# Subagents 详细示例

本文档包含 Subagents 的完整代码示例和详细说明。

## 基础配置

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model=model,
    subagents=[
        {
            "name": "researcher",
            "description": "负责信息搜集和研究的助手",
            "system_prompt": "你是一个专业的研究助手，擅长搜索和分析信息。"
        },
        {
            "name": "coder",
            "description": "负责代码编写和调试",
            "system_prompt": "你是一个资深的开发工程师，擅长多种编程语言。"
        }
    ]
)
```

## 完整配置示例

```python
from deepagents import create_deep_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver

@tool
def code_analyzer(code: str) -> str:
    """分析代码质量"""
    return "代码分析结果..."

@tool
def search_web(query: str) -> str:
    """搜索网络信息"""
    return f"搜索结果: {query}"

checkpointer = MemorySaver()

agent = create_deep_agent(
    model=model,
    tools=[code_analyzer, search_web],
    subagents=[
        {
            "name": "security-auditor",
            "description": "安全审计专家，检查代码安全漏洞",
            "system_prompt": """你是安全审计专家。
            你的任务是：
            1. 检查 SQL 注入风险
            2. 检查 XSS 漏洞
            3. 验证输入验证
            4. 报告安全问题""",
            "tools": [code_analyzer],
            "interrupt_on": {
                "write_file": True  # 子代理级别的中断配置
            }
        },
        {
            "name": "performance-optimizer",
            "description": "性能优化专家",
            "system_prompt": "你是性能优化专家，专注于代码效率和资源使用。",
            "tools": [code_analyzer]
        },
        {
            "name": "research-assistant",
            "description": "研究助手",
            "system_prompt": "你擅长信息搜集和分析。",
            "tools": [search_web]
        }
    ],
    checkpointer=checkpointer
)
```

## 子代理中断配置覆盖

```python
agent = create_deep_agent(
    tools=[delete_file, write_file],
    interrupt_on={
        "delete_file": False,  # 主代理不需要批准
        "write_file": False,
    },
    subagents=[{
        "name": "file-manager",
        "system_prompt": "你管理文件操作",
        "tools": [delete_file, write_file],
        "interrupt_on": {
            # 覆盖主代理设置，此子代理需要批准
            "delete_file": True,
            "write_file": True
        }
    }]
)
```

## 完整的代码审计场景

```python
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver

@tool
def scan_security(code: str) -> str:
    """扫描代码安全问题"""
    # 实际实现中这里会调用安全扫描工具
    return f"安全扫描完成，发现 {len([c for c in code if 'TODO' in c])} 个待办事项"

@tool
def measure_performance(code: str) -> str:
    """测量代码性能指标"""
    return "性能测量：时间复杂度 O(n)，空间复杂度 O(1)"

@tool
def check_style(code: str) -> str:
    """检查代码风格"""
    return "代码风格检查通过"

# 创建主 Agent
checkpointer = MemorySaver()

agent = create_deep_agent(
    name="code-review-agent",
    model=ChatOpenAI(
        base_url="https://open.bigmodel.cn/api/coding/paas/v4/",
        api_key="你的API密钥",
        model="glm-4.7",
    ),
    tools=[scan_security, measure_performance, check_style],
    subagents=[
        {
            "name": "security-expert",
            "description": "安全专家，专注于识别安全漏洞",
            "system_prompt": """你是安全专家。
            专注于识别：
            - SQL 注入
            - XSS 攻击
            - CSRF 漏洞
            - 输入验证问题
            整理发现并提供建议。""",
            "tools": [scan_security],
            "interrupt_on": {
                "scan_security": False
            }
        },
        {
            "name": "performance-expert",
            "description": "性能专家，优化代码效率",
            "system_prompt": """你是性能专家。
            评估：
            - 时间复杂度
            - 空间复杂度
            - 算法选择
            - 资源使用
            提供优化建议。""",
            "tools": [measure_performance]
        },
        {
            "name": "style-reviewer",
            "description": "代码风格审查员",
            "system_prompt": """你是代码风格专家。
            检查：
            - 命名规范
            - 代码格式
            - 注释质量
            - 可读性
            确保符合团队标准。""",
            "tools": [check_style]
        }
    ],
    checkpointer=checkpointer,
    system_prompt="""你是一个代码审查协调员。
    当收到代码审查请求时：
    1. 调用相应的子代理进行分析
    2. 综合各专家的反馈
    3. 提供清晰的总结报告"""
)

# 使用
config = {"configurable": {"thread_id": "review-session-1"}}
result = agent.invoke(
    {
        "messages": [{
            "role": "user",
            "content": """请审查以下代码：

def get_user_data(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return db.execute(query)

请从安全、性能和代码风格三个方面进行分析。"""
        }]
    },
    config=config,
    version="v2"
)

print(result["messages"][-1].content)
```

## 上下文隔离示例

```python
# 主 Agent 处理高层任务
main_agent = create_deep_agent(
    name="project-manager",
    model=model,
    system_prompt="你是项目经理，协调各个专家团队。",
    subagents=[
        {
            "name": "data-analyst",
            "system_prompt": "你是数据分析师，专注于数据处理和统计。",
            # 数据分析师有自己专门的上下文
        },
        {
            "name": "ui-designer",
            "system_prompt": "你是 UI 设计师，专注于用户体验和界面设计。",
            # UI 设计师有自己专门的上下文
        }
    ]
)

# 每个子代理的对话历史是隔离的，保持主 Agent 上下文清洁
```

## 子代理工具链

```python
@tool
def fetch_data(source: str) -> str:
    """从数据源获取数据"""
    return f"从 {source} 获取的数据"

@tool
def process_data(data: str) -> str:
    """处理数据"""
    return f"处理后的数据: {data}"

@tool
def visualize_data(data: str) -> str:
    """可视化数据"""
    return f"图表: {data}"

# 数据处理管道子代理
data_pipeline = {
    "name": "data-processor",
    "system_prompt": """你是数据处理专家。
    工作流程：
    1. fetch_data - 获取原始数据
    2. process_data - 清洗和转换数据
    3. visualize_data - 生成可视化""",
    "tools": [fetch_data, process_data, visualize_data]
}

agent = create_deep_agent(
    model=model,
    subagents=[data_pipeline]
)
```

## Async Subagents

对于长时间运行的任务、并行工作流，或需要中途调整和取消的情况，参见 [Async subagents](https://docs.langchain.com/oss/python/deepagents/async-subagents)。

## 子代理最佳实践

1. **明确职责** - 每个子代理应该有清晰的职责范围
2. **专门工具** - 为子代理配置专门的工具集
3. **系统提示** - 为每个子代理提供专门的系统提示
4. **上下文隔离** - 利用子代理隔离不同任务的上下文
5. **中断控制** - 子代理可以有自己的中断配置
