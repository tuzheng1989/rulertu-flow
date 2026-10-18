# 性能故障模式

## 网络瀑布图：串行等待

若 B 请求并不依赖 A 的结果，却在 `await A` 后才开始，改为并发：

```ts
const [profile, permissions] = await Promise.all([
  loadProfile(userId),
  loadPermissions(userId),
]);
```

不能把存在数据依赖或有速率限制的请求机械并行。验证瀑布中开始时间变化以及服务端压力。

## 主线程：一次输入触发大计算

```ts
const deferredQuery = useDeferredValue(query);
const visibleRows = useMemo(
  () => expensiveFilter(rows, deferredQuery),
  [rows, deferredQuery],
);
```

只有性能 trace 证明计算昂贵且依赖稳定时才 memo。轻量计算加 `useMemo` 可能增加复杂度而没有收益；更重的纯计算考虑 Worker，并验证序列化成本。

## 列表：渲染量而非接口慢

先用组件分析证明重复渲染或 DOM 数量过大。虚拟化时必须保留稳定 key、键盘焦点、动态高度和滚动定位；不可只看帧率通过。

## 资源：图片尺寸和实际展示不匹配

```html
<img
  src="/cover-800.webp"
  srcset="/cover-400.webp 400w, /cover-800.webp 800w"
  sizes="(max-width: 640px) 100vw, 50vw"
  width="800"
  height="450"
  loading="lazy"
  alt=""
/>
```

首屏最大内容图片通常不能盲目 `lazy`；需按真实 LCP 元素决定优先级。显式尺寸用于避免布局偏移。

## 内存：订阅没有对称释放

```ts
useEffect(() => {
  const unsubscribe = store.subscribe(onChange);
  return unsubscribe;
}, [store, onChange]);
```

使用堆快照或监听器计数验证对象可被回收。仅在卸载时设布尔值，不能释放事件监听器、定时器或观察器。
