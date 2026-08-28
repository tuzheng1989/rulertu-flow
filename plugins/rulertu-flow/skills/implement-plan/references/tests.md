# 好测试与坏测试

## 好测试

**集成式测试**：通过真实接口观察行为，不 mock 内部组成部分。

```typescript
// 好：验证可观察行为
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});
```
特征：

- 验证用户或调用方关心的行为；
- 只通过公开接口操作；
- 内部重构后仍然成立；
- 描述“做什么”，而不是“怎么做”；
- 每个测试只表达一个逻辑断言。

## 坏测试

**实现细节测试**：与内部结构耦合。

```typescript
// 坏：验证内部调用细节
test("checkout calls paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});
```

危险信号：

- mock 内部协作者；
- 测试私有方法；
- 断言调用次数或顺序；
- 行为未变，仅重构就导致测试失败；
- 测试名描述“怎么做”而不是“做什么”；
- 绕过接口从外部渠道验证结果。

```typescript
// 坏：绕过接口验证
test("createUser saves to database", async () => {
  await createUser({ name: "Alice" });
  const row = await db.query("SELECT * FROM users WHERE name = ?", ["Alice"]);
  expect(row).toBeDefined();
});

// 好：通过接口验证
test("createUser makes user retrievable", async () => {
  const user = await createUser({ name: "Alice" });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe("Alice");
});
```

**同义反复测试**：期望值重复实现算法，因此测试按构造必然通过。

```typescript
// 坏：期望值与实现采用同一种计算方式
test("calculateTotal sums line items", () => {
  const items = [{ price: 10 }, { price: 5 }];
  const expected = items.reduce((sum, i) => sum + i.price, 0);
  expect(calculateTotal(items)).toBe(expected);
});

// 好：期望值来自独立、已知的字面量
test("calculateTotal sums line items", () => {
  expect(calculateTotal([{ price: 10 }, { price: 5 }])).toBe(15);
});
```
