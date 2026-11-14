# Mermaid 语法参考

完整的 Mermaid 图表语法参考，用于在 Markdown 中创建各种类型的图表。

## 流程图 (Flowchart)

### 基础语法

```mermaid
flowchart TD
    A[开始] --> B[处理]
    B --> C{判断}
    C -->|是| D[结果1]
    C -->|否| E[结果2]
```

### 方向

- `TD` - 从上到下 (Top to Down)
- `DT` - 从下到上 (Down to Top)
- `LR` - 从左到右 (Left to Right)
- `RL` - 从右到左 (Right to Left)

### 节点形状

```mermaid
flowchart LR
    id1[方形]
    id2(圆角)
    id3([体育场形])
    id4[[子程序]]
    id5[(圆柱)]
    id6((圆形))
    id7{菱形}
    id8{{六边形}}
    id9[/平行四边形/]
    id10[\反向平行四边形\]
    id11[/梯形\]
    id12[\反向梯形/]
```

### 连接线样式

```mermaid
flowchart LR
    A -->|带文字| B
    B --> C
    C -.-> D
    D ==> E
    A --普通线--> F
    A --带文字线--> G
    A -.虚线带文字.-> H
    A ==>粗线带文字==> I
```

## 序列图 (Sequence Diagram)

```mermaid
sequenceDiagram
    participant 用户
    participant 系统
    participant 数据库

    用户->>系统: 发起请求
    系统->>数据库: 查询数据
    数据库-->>系统: 返回结果
    系统-->>用户: 显示响应

    rect rgb(240, 248, 255)
        Note over 用户,系统: 交互过程
    end

    alt 成功
        系统-->>用户: 成功消息
    else 失败
        系统-->>用户: 错误消息
    end
```

## 类图 (Class Diagram)

```mermaid
classDiagram
    class Animal {
        +String name
        +int age
        +eat()
        +sleep()
    }
    class Dog {
        +bark()
        +fetch()
    }
    class Cat {
        +meow()
        +scratch()
    }

    Animal <|-- Dog
    Animal <|-- Cat

    Dog --|> Cat : 关联
```

## 状态图 (State Diagram)

```mermaid
stateDiagram-v2
    [*] --> 待处理
    待处理 --> 处理中: 开始处理
    处理中 --> 已完成: 处理成功
    处理中 --> 失败: 处理失败
    失败 --> 待处理: 重试
    已完成 --> [*]
    失败 --> [*]: 放弃
```

## 实体关系图 (ER Diagram)

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains
    PRODUCT ||--o{ LINE_ITEM : "ordered in"
    CUSTOMER {
        string name
        string email
        int id PK
    }
    ORDER {
        int id PK
        date created
        int customer_id FK
    }
    PRODUCT {
        int id PK
        string name
        float price
    }
```

## 甘特图 (Gantt Chart)

```mermaid
gantt
    title 项目开发计划
    dateFormat  YYYY-MM-DD
    section 需求分析
    需求收集           :a1, 2024-01-01, 7d
    需求评审           :a2, after a1, 3d
    section 设计阶段
    系统设计           :b1, after a2, 10d
    数据库设计         :b2, after a2, 7d
    section 开发阶段
    后端开发           :c1, after b1, 20d
    前端开发           :c2, after b1, 15d
    section 测试阶段
    集成测试           :d1, after c1, 10d
    用户验收           :d2, after d1, 5d
```

## 饼图 (Pie Chart)

```mermaid
pie title 技术栈分布
    "JavaScript" : 40
    "Python" : 25
    "Java" : 20
    "Go" : 10
    "其他" : 5
```

## 用户旅程图 (User Journey)

```mermaid
journey
    title 用户购物旅程
    section 浏览
      浏览商品: 5: 用户
      查看详情: 4: 用户
    section 购买
      加入购物车: 5: 用户
      结算支付: 3: 用户
    section 售后
      收到商品: 5: 用户
      评价反馈: 2: 用户
```

## 关系图 (Relationship Diagram)

```mermaid
relationshipDiagram
    acme --> creates --> product
    acme --> employs --> person
    person --> buys --> product
```

## 需求图 (Requirement Diagram)

```mermaid
requirementDiagram
    requirement test_req {
        id: 1
        text: 测试需求
        risk: high
        verifyMethod: test
    }

    element test_entity {
        type: system
    }

    test_entity - satisfies -> test_req
```

## 样式定制

### 主题

在图表代码块前添加主题声明：

```mermaid
%%{init: {'theme':'base'}}%%
flowchart LR
    A --> B
```

可用主题：
- `default` - 默认主题
- `forest` - 森林主题
- `dark` - 暗色主题
- `neutral` - 中性主题
- `base` - 基础主题（可完全自定义）

### 自定义样式

```mermaid
flowchart LR
    id1(开始):::startStyle
    id2(处理):::processStyle
    id3(结束):::endStyle

    id1 --> id2 --> id3

    classDef startStyle fill:#90EE90,stroke:#333,stroke-width:2px
    classDef processStyle fill:#87CEEB,stroke:#333,stroke-width:2px
    classDef endStyle fill:#FFB6C1,stroke:#333,stroke-width:2px
```

### 子图

```mermaid
flowchart TB
    subgraph 子系统A
        A1[节点1]
        A2[节点2]
        A1 --> A2
    end

    subgraph 子系统B
        B1[节点3]
        B2[节点4]
        B1 --> B2
    end

    A2 --> B1
```

## 常见问题

### 中文支持

Mermaid 原生支持中文，只需确保在 PDF 渲染时使用正确的字体：

```css
body {
    font-family: "Microsoft YaHei", "SimSun", sans-serif;
}
```

### 图表过大

使用 `fit` 参数调整图表尺寸，或在 HTML 模板中设置最大宽度：

```css
.mermaid {
    max-width: 100%;
    overflow-x: auto;
}
```

### 复杂图表渲染慢

增加渲染超时时间：

```bash
python scripts/md_to_pdf.py input.md --timeout 120000
```

## 参考资源

- [Mermaid 官方文档](https://mermaid.js.org/intro/)
- [Mermaid 在线编辑器](https://mermaid.live/)
- [Mermaid GitHub](https://github.com/mermaid-js/mermaid)
