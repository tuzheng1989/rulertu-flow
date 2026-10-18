# 框架实现模式

只读取与当前仓库技术栈一致的部分。代码展示的是关键控制项，不是可直接粘贴的业务模块。

## React：忽略过期响应

错误做法是每次参数变化都请求，并让最后返回的响应覆盖界面；慢的旧请求可能晚于新请求到达。

```tsx
useEffect(() => {
  const controller = new AbortController();
  let current = true;

  setView({ status: "loading" });
  fetchProjects(filters, { signal: controller.signal })
    .then((rows) => current && setView(
      rows.length ? { status: "ready", rows } : { status: "empty" },
    ))
    .catch((error) => {
      if (current && error.name !== "AbortError") {
        setView({ status: "error", message: toUserMessage(error) });
      }
    });

  return () => {
    current = false;
    controller.abort();
  };
}, [filters]);
```

若项目已使用 TanStack Query、SWR 或内部请求库，使用其取消、缓存键和错误模型，不另造一套 `useEffect` 请求层。

例如用户已经确认使用 TanStack Query 时，缓存键必须包含所有会改变结果的业务条件；用不同键隔离 workspace，并让请求函数接收 Query 提供的 `signal`：

```tsx
const membersQuery = useQuery({
  queryKey: ["workspace-members", workspaceId],
  enabled: Boolean(workspaceId),
  queryFn: ({ signal }) => memberApi.list(workspaceId, { signal }).then(toMembers),
});
```

视图从 `isPending`、`isError`、权限结果和 `data.length` 映射为互斥状态；不要用 `data ?? []` 把未请求、失败和真实空结果合并。竞态测试控制 A、B 两个 workspace 请求的完成顺序，先返回 B、再返回 A，并断言界面仍只显示 B 的成员。

## Vue 3：显式区分加载、空和失败

```ts
type ViewState<T> =
  | { kind: "loading" }
  | { kind: "ready"; data: T }
  | { kind: "empty" }
  | { kind: "error"; message: string };

const state = ref<ViewState<Project[]>>({ kind: "loading" });

async function load(signal?: AbortSignal) {
  state.value = { kind: "loading" };
  try {
    const rows = await projectApi.list({ signal });
    state.value = rows.length
      ? { kind: "ready", data: rows }
      : { kind: "empty" };
  } catch (error) {
    if (!isAbort(error)) state.value = { kind: "error", message: toUserMessage(error) };
  }
}
```

不要用 `items = []` 同时代表未请求、无数据和请求失败。

## DTO 只在边界转换

```ts
type ProjectDTO = { project_id: string; display_name?: string | null };
type Project = { id: string; name: string };

export function toProject(dto: ProjectDTO): Project {
  if (!dto.project_id) throw new ContractError("project_id 缺失");
  return {
    id: dto.project_id,
    name: dto.display_name?.trim() || "未命名项目",
  };
}
```

默认文案只能处理业务允许为空的字段。必填字段缺失应进入错误状态或监控，不得用 `|| "-"` 静默吞掉契约错误。

## 写操作保留失败现场

```ts
async function submit(input: FormValue) {
  if (saving) return;
  setSaving(true);
  setSubmitError(null);
  try {
    const saved = await api.save(input);
    setForm(toFormValue(saved));
    announce("保存成功");
  } catch (error) {
    setSubmitError(toUserMessage(error)); // 不清空 input
  } finally {
    setSaving(false);
  }
}
```

保存按钮的禁用、`aria-busy`、错误焦点与成功提示应来自同一提交状态，而不是各自维护布尔值。

## 响应式不是等比例缩小

窄屏优先保留用户任务：主操作常驻、次操作进入菜单、表格改为字段分组或水平滚动。隐藏字段前确认它不是完成任务的必要信息。断点应由内容开始拥挤的位置决定，不由某个设备型号决定。
