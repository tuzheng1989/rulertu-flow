# 浏览器验收代码模式

## 断言用户结果

```ts
test("保存失败后保留输入并可重试", async ({ page }) => {
  await page.route("**/api/profile", async (route) => {
    await route.fulfill({ status: 503, body: JSON.stringify({ message: "temporary" }) });
  });
  await page.getByLabel("显示名称").fill("新的名称");
  await page.getByRole("button", { name: "保存" }).click();
  await expect(page.getByRole("alert")).toContainText("请稍后重试");
  await expect(page.getByLabel("显示名称")).toHaveValue("新的名称");
});
```

不要只断言 toast 出现；还要验证失败后的业务状态。

## 用真实无障碍名称定位

优先顺序通常为 `getByRole`、`getByLabel`、`getByText`、稳定的 `getByTestId`。避免 `.ant-modal > div:nth-child(2)` 等实现结构。找不到无障碍名称本身可能是产品缺陷，不应立即补脆弱选择器绕过。

## 等待状态，不等待时间

```ts
await Promise.all([
  page.waitForResponse((r) => r.url().endsWith("/api/projects") && r.ok()),
  page.getByRole("button", { name: "刷新" }).click(),
]);
await expect(page.getByRole("row", { name: /示例项目/ })).toBeVisible();
```

禁止用 `waitForTimeout(3000)` 让测试“看起来稳定”。如果产品没有可观察的完成状态，应先补产品状态或网络断言。

模拟慢接口也不能在测试或路由处理器里写固定睡眠。使用可控 Promise/闸门决定响应何时释放：

```ts
let releaseResponse!: () => void;
const responseGate = new Promise<void>((resolve) => { releaseResponse = resolve; });

await page.route("**/api/profile", async (route) => {
  await responseGate;
  await route.fulfill({ status: 200, body: JSON.stringify(savedProfile) });
});

await page.getByRole("button", { name: "保存" }).click();
await expect(page.getByRole("button", { name: "保存" })).toBeDisabled();
releaseResponse();
await expect(page.getByRole("status")).toHaveText("保存成功");
```

这样测试等待的是可观察状态和显式释放，不依赖机器快慢。`waitForTimeout` 只能用于人工调试，不能进入验收代码。

## 写操作验证持久化

写操作成功后刷新页面或从服务端重新读取，确认状态不是只停留在前端内存。生产环境不得为验收随意创建或删除真实数据；使用沙箱、测试租户或已授权的可逆记录。

## 键盘路径

从页面首个交互元素开始使用 Tab/Shift+Tab，检查焦点可见、顺序合理、弹窗焦点被约束且关闭后回到触发元素。不要只检查元素有 `tabindex`。
