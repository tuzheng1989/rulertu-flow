# 前端故障代码模式

## 缓存键没有包含筛选条件

```ts
// 错：不同 workspace 共享同一份缓存
useQuery({ queryKey: ["members"], queryFn: () => listMembers(workspaceId) });

// 对：所有影响结果的输入进入 key
useQuery({
  queryKey: ["members", { workspaceId, role, page }],
  queryFn: ({ signal }) => listMembers({ workspaceId, role, page, signal }),
});
```

回归测试：先加载 A，再切 B；B 的首次渲染不能显示 A 的成员，晚到的 A 响应不能覆盖 B。

## 默认值掩盖契约错误

```ts
// 错：接口把 data.rows 改成 data.items 后，页面只显示“暂无数据”
const rows = response.data?.rows ?? [];

// 对：在适配边界验证契约
function parseRows(input: unknown): Row[] {
  if (!isObject(input) || !Array.isArray(input.rows)) {
    throw new ContractError("响应缺少 rows 数组");
  }
  return input.rows.map(parseRow);
}
```

可选字段可以给默认值；决定页面主行为的必填字段不能静默补默认值。

## 旧闭包覆盖新状态

```tsx
// 错：并发完成时都基于各自捕获的 items
setItems([...items, saved]);

// 对：基于提交时的最新状态更新
setItems((current) => upsertById(current, saved));
```

若数据由查询缓存拥有，应更新或失效该缓存，不要再维护一份组件副本。

## 乐观更新没有失败回滚

```ts
const previous = queryClient.getQueryData(key);
queryClient.setQueryData(key, (current) => applyChange(current, patch));
try {
  await api.update(patch);
} catch (error) {
  queryClient.setQueryData(key, previous);
  throw error;
} finally {
  await queryClient.invalidateQueries({ queryKey: key });
}
```

生产实现还应处理并发 mutation；如果库提供 `onMutate/onError/onSettled`，遵循项目已有封装。

## 点击无效不是只有事件没绑定

依次验证：元素实际可点击区域、遮罩与 `pointer-events`、disabled 来源、父层阻止冒泡、表单默认提交、事件是否读到旧状态、路由是否被权限守卫重定向。只在 DOM 上补一个 `onClick` 往往会制造第二条执行路径。

## 超时、断网和取消不是同一种失败

- 断网：浏览器通常没有 HTTP 响应；保留输入，展示可重试状态并避免写成服务端拒绝。
- 超时：记录客户端与网关各自预算；请求可能仍在服务端执行，写操作重试前确认幂等。
- 主动取消：筛选或路由变化导致的旧请求取消通常不应展示错误 toast。

React Query/SWR 使用其 error、signal 和缓存所有权；Vue Query 同理。若 Vue 项目由 Pinia 管理请求状态，检查 action 的并发身份和 store 重置；若 React 项目由组件本地状态管理，检查 effect 清理与函数式更新。框架只是定位状态所有者的线索，根因仍由运行证据决定。
