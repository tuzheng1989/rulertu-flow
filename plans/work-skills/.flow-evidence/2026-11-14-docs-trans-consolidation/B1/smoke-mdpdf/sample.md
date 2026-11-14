# 冒烟测试文档

这是一段中文正文，用于验证 Markdown 转 PDF 管线。

## 流程图

```mermaid
flowchart TD
    A[输入文档] --> B{类型判断}
    B -->|文本型| C[anydoc 引擎]
    B -->|扫描版| D[OCR 路由]
```

## 结尾

转换完成标志段。
