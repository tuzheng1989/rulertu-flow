# 何时使用测试替身

只在**系统边界**使用 mock（测试替身）：

- 外部 API，例如支付、邮件；
- 数据库，但能使用测试数据库时优先使用测试数据库；
- 时间和随机数；
- 文件系统，且仅在确有必要时。

不要 mock：

- 自己编写的类或模块；
- 内部协作者；
- 任何完全由本项目控制的实现。

## 为可替换性设计

在系统边界上，接口应易于替换。

### 1. 使用依赖注入

从外部传入依赖，不要在函数内部创建：

```typescript
// 易于 mock
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// 难以 mock
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

### 2. 优先使用 SDK 式接口，而不是通用请求器

为每个外部操作提供明确函数，不要把条件分支塞进一个通用函数：

```typescript
// 好：每个函数都可独立替换
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};

// 坏：mock 内部必须复刻条件分支
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```

SDK 式接口的收益：

- 每个 mock 只返回一种明确形状；
- 测试准备不需要条件逻辑；
- 一眼可见测试涉及哪些端点；
- 每个端点都能获得独立类型安全。
