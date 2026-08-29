# Human-in-the-loop 详细示例

本文档包含 Human-in-the-loop (HITL) 的完整代码示例和详细说明。

## 基础配置示例

```python
from langchain.tools import tool
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

@tool
def delete_file(path: str) -> str:
    """删除文件"""
    return f"已删除 {path}"

@tool
def read_file(path: str) -> str:
    """读取文件"""
    return f"{path} 的内容"

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件"""
    return f"已发送邮件至 {to}"

# Checkpointer 是必需的！
checkpointer = MemorySaver()

agent = create_deep_agent(
    model=model,
    tools=[delete_file, read_file, send_email],
    interrupt_on={
        "delete_file": True,      # 默认：approve, edit, reject
        "read_file": False,       # 不需要中断
        "send_email": {
            "allowed_decisions": ["approve", "reject"]  # 不允许编辑
        }
    },
    checkpointer=checkpointer  # 必需！
)
```

## 按风险级别配置

```python
interrupt_on = {
    # 高风险：完全控制（approve, edit, reject）
    "delete_file": {
        "allowed_decisions": ["approve", "edit", "reject"]
    },
    "send_email": {
        "allowed_decisions": ["approve", "edit", "reject"]
    },

    # 中等风险：只允许批准或拒绝，不允许编辑
    "write_file": {
        "allowed_decisions": ["approve", "reject"]
    },

    # 低风险：不需要中断
    "read_file": False,
    "list_files": False,
}
```

## 处理中断 - 完整示例

```python
import uuid
from langgraph.types import Command

# 创建带 thread_id 的 config 用于状态持久化
config = {
    "configurable": {
        "thread_id": str(uuid.uuid4())
    }
}

# 调用 Agent
result = agent.invoke(
    {"messages": [{"role": "user", "content": "删除文件 temp.txt"}]},
    config=config,
    version="v2"
)

# 检查是否被中断
if result.interrupts:
    interrupt_value = result.interrupts[0].value
    action_requests = interrupt_value["action_requests"]
    review_configs = interrupt_value["review_configs"]

    # 创建工具名到配置的映射
    config_map = {
        cfg["action_name"]: cfg for cfg in review_configs
    }

    # 显示待处理操作
    for action in action_requests:
        review_config = config_map[action["name"]]
        print(f"工具: {action['name']}")
        print(f"参数: {action['args']}")
        print(f"允许的决策: {review_config['allowed_decisions']}")

    # 获取用户决策（每个 action_request 一个，按顺序）
    decisions = [
        {"type": "approve"}  # 用户批准删除
    ]

    # 使用决策恢复执行
    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=config,  # 必须使用相同的 config！
        version="v2"
    )

    # 处理最终结果
    print(result.value["messages"][-1].content)
```

## 多工具调用处理

```python
config = {
    "configurable": {
        "thread_id": str(uuid.uuid4())
    }
}

result = agent.invoke(
    {"messages": [{"role": "user", "content": "删除 temp.txt 并发送邮件到 admin@example.com"}]},
    config=config,
    version="v2"
)

if result.interrupts:
    interrupt_value = result.interrupts[0].value
    action_requests = interrupt_value["action_requests"]

    # 两个工具需要批准
    assert len(action_requests) == 2

    # 按 action_requests 的顺序提供决策
    decisions = [
        {"type": "approve"},    # 第一个工具：delete_file
        {"type": "reject"}      # 第二个工具：send_email
    ]

    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=config,
        version="v2"
    )
```

## 编辑工具参数

```python
if result.interrupts:
    interrupt_value = result.interrupts[0].value
    action_request = interrupt_value["action_requests"][0]

    # Agent 的原始参数
    print(action_request["args"])
    # {"to": "everyone@company.com", ...}

    # 用户决定编辑收件人
    decisions = [{
        "type": "edit",
        "edited_action": {
            "name": action_request["name"],  # 必须包含工具名称
            "args": {
                "to": "team@company.com",
                "subject": "...",
                "body": "..."
            }
        }
    }]

    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=config,
        version="v2"
    )
```

## 子代理中断配置

```python
agent = create_deep_agent(
    tools=[delete_file, read_file],
    interrupt_on={
        "delete_file": True,
        "read_file": False,
    },
    subagents=[{
        "name": "file-manager",
        "description": "管理文件操作",
        "system_prompt": "你是一个文件管理助手。",
        "tools": [delete_file, read_file],
        "interrupt_on": {
            # 覆盖：此子代理中读取也需要批准
            "delete_file": True,
            "read_file": True,  # 与主代理不同！
        }
    }],
    checkpointer=checkpointer
)
```

## 工具调用内部的中断

```python
from langgraph.types import Command, interrupt

@tool(description="在继续操作前请求人工批准。")
def request_approval(action_description: str) -> str:
    """使用 interrupt() 原语请求人工批准"""
    # interrupt() 暂停执行并返回传递给 Command(resume=...) 的值
    approval = interrupt({
        "type": "approval_request",
        "action": action_description,
        "message": f"请批准或拒绝: {action_description}"
    })

    if approval.get("approved"):
        return f"操作 '{action_description}' 已被批准。继续执行..."
    else:
        return f"操作 '{action_description}' 被拒绝。原因: {approval.get('reason', '未提供原因')}"
```

## 完整的子代理中断示例

```python
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain.messages import HumanMessage
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt
from deepagents.graph import create_deep_agent
from deepagents.middleware.subagents import CompiledSubAgent

@tool(description="在继续操作前请求人工批准。")
def request_approval(action_description: str) -> str:
    """请求人工批准使用 interrupt() 原语"""
    approval = interrupt({
        "type": "approval_request",
        "action": action_description,
        "message": f"请批准或拒绝: {action_description}"
    })

    if approval.get("approved"):
        return f"操作 '{action_description}' 已被批准。继续执行..."
    else:
        return f"操作 '{action_description}' 被拒绝。原因: {approval.get('reason', '未提供原因')}"

def main():
    checkpointer = InMemorySaver()
    model = ChatAnthropic(
        model_name="claude-sonnet-4-6",
        max_tokens=4096,
    )

    compiled_subagent = create_agent(
        model=model,
        tools=[request_approval],
        name="approval-agent",
    )

    parent_agent = create_deep_agent(
        checkpointer=checkpointer,
        subagents=[
            CompiledSubAgent(
                name="approval-agent",
                description="一个可以请求批准的代理",
                runnable=compiled_subagent,
            )
        ],
    )

    thread_id = "test_interrupt_directly"
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    print("调用 agent - 子代理将使用 request_approval 工具...")
    result = parent_agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content="使用 task 工具启动 approval-agent 子代理。"
                    "告诉它使用 request_approval 工具请求批准 '部署到生产环境'。"
                )
            ]
        },
        config=config,
        version="v2",
    )

    # 检查中断
    if result.interrupts:
        interrupt_value = result.interrupts[0].value
        print(f"\n收到中断！")
        print(f"  类型: {interrupt_value.get('type')}")
        print(f"  操作: {interrupt_value.get('action')}")
        print(f"  消息: {interrupt_value.get('message')}")
        print("\n使用 Command(resume={'approved': True}) 恢复...")

        result2 = parent_agent.invoke(
            Command(resume={"approved": True}),
            config=config,
            version="v2",
        )

        if not result2.interrupts:
            print("\n执行完成！")
            # 查找工具响应
            tool_msgs = [
                m for m in result2.value.get("messages", [])
                if m.type == "tool"
            ]
            if tool_msgs:
                print(f"  工具结果: {tool_msgs[-1].content}")
        else:
            print("\n发生另一个中断")
    else:
        print("\n没有中断 - 模型可能没有调用 request_approval")

if __name__ == "__main__":
    main()
```

## 最佳实践总结

1. **始终使用 checkpointer** - HITL 必需
2. **使用相同的 thread_id** - 恢复时必须一致
3. **决策顺序匹配** - decisions 顺序必须与 action_requests 匹配
4. **按风险配置** - 高风险操作允许编辑，低风险操作不中断
