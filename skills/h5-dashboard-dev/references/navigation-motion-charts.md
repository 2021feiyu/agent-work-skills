# 导航、动态图表与动效蓝图

本文定义可复用的交互逻辑。可复制实现位于 `assets/executive-h5-kit/`：`shell.js` 负责页签/抽屉，`motion.js` 负责动效偏好与最新任务，`chart-theme.js` 负责 ECharts 主题和更新动画。
代码是起点，不是绕过业务语义与截图验收的黑盒。

## 1. 状态模型：不要让函数互相抢 DOM

### 1.1 四种状态

```js
const state = {
  route: { pageId: 'overview', anchor: null },
  filters: { period: '2026-Q3', org: 'all' },
  drillPath: [],
  overlay: { type: null, id: null }
};
```

- route 决定当前页面与定位。
- filters 决定数据子集，不直接决定导航是否存在。
- drillPath 决定分析层级与返回路径。
- overlay 决定临时窗格，不改变底层 route。

页面是否可见由一个 selector/render 统一裁决。筛选函数只更新 filters，导航函数只更新 route，禁止各自写 `style.display` 后互相覆盖。

### 1.2 PageRegistry

```js
const pages = [
  {
    id: 'overview',
    nav: '经营总览',
    title: '增长仍在，但质量开始分化',
    shortTitle: '总览',
    charts: ['trend', 'exceptions'],
    scroll: 'preserve',
    print: true
  }
];
```

导航、页签、进度、移动抽屉、打印目录和图表懒加载都从 registry 读取。
若页面 H1 与导航必须一致，使用同一字段或构建断言；不要为了“生成导航”而引入另一份名称映射。

## 2. 可访问 Tabs

### 2.1 HTML 关系

```html
<div role="tablist" aria-label="经营分析页面">
  <button id="tab-overview" role="tab" aria-selected="true"
          aria-controls="panel-overview" tabindex="0">总览</button>
  <button id="tab-cost" role="tab" aria-selected="false"
          aria-controls="panel-cost" tabindex="-1">成本</button>
</div>
<section id="panel-overview" role="tabpanel" aria-labelledby="tab-overview">…</section>
<section id="panel-cost" role="tabpanel" aria-labelledby="tab-cost" hidden>…</section>
```

不额外加 `role=menu`。Tabs 是内容页签，menu 是命令菜单，两者键盘模型不同。

### 2.2 键盘策略

- 横向：Left/Right；垂直：Up/Down，并设置 `aria-orientation=vertical`。
- Home/End 到首尾；循环移动。
- 页面已预载且切换无明显延迟：焦点移动可自动激活。
- 页面需要重计算：方向键只移动焦点，Enter/Space 激活。
- 只有一个 tab `tabindex=0`，其余 `-1`；选中后同步 roving tabindex。

`shell.js` 提供该行为的参考实现。若页面只是锚点链接，保留原生链接行为，不强套 Tabs。

## 3. 抽屉与窗格

### 3.1 导航抽屉

打开时：保存触发按钮、设置 `aria-expanded=true`、移入第一个可交互项。
关闭时：恢复 `aria-expanded=false`、返回触发按钮；Escape 可关闭。
模态移动抽屉还需焦点约束与背景 `inert`；非模态桌面侧栏不使用焦点陷阱。

### 3.2 详情抽屉

详情抽屉的路由/筛选状态仍保留在底层。打开不应重置筛选，关闭不应滚回顶部。
内容更新时保留抽屉标题与来源；加载失败显示错误和重试，不把旧详情静默替换成空白。

### 3.3 滚动策略

按动作区分：

- 用户主动切页：若新页标题在视口外，将其定位到吸顶栈下方；已在视口内则不滚动。
- 打开详情：通常不滚动底层页面。
- 返回上一页：恢复原滚动位置。
- 回顶：用户明确点击才执行；减少动效时立即定位。

不要给所有切页统一 `scrollTo(0)`，也不要让全局 `scroll-behavior:smooth` 使大跨度切页缓慢滑行。

## 4. 页面过渡

### 4.1 默认路径：直接终态 + 短增强

页面先完成状态更新并立即可读，再执行视觉过渡。无 JS、无 View Transition、减少动效或动画被中断时，最终内容已经存在。

```js
function commitPage(next) {
  updateRoute(next);
  renderTabs();
  renderPanels();
  initVisibleCharts();
  syncFocusScrollAndUrl();
}

function go(next, motion) {
  if (motion.reduced || !document.startViewTransition) {
    commitPage(next);
    return;
  }
  document.startViewTransition(() => commitPage(next));
}
```

不要在 `startViewTransition` 回调里等待网络或长时间计算；新旧视图同时存在时还要注意焦点和读屏重复。
该 API 只做渐进增强，样式提供普通回退。

### 4.2 不要全页同时运动

页面过渡时，背景与导航尽量稳定，主内容做 4–12px 的短位移或淡变。
图表若保持同一份数据，无需重播；若数据也变化，选择“页面过渡”或“图表更新”其中一个作为主运动，避免两层互相遮挡。

## 5. ECharts 动态策略

### 5.1 决策表

| 场景 | 默认 |
|---|---|
| 首次打开页面 | 可见后 init；一次短 enter，或按静态模式直接终态 |
| 筛选数据变化 | 复用实例，`setOption`；220–360ms update |
| 同图下钻/聚合 | 稳定 id/groupId 时考虑 universal transition |
| 切换图型 | 仅当形态关系有助理解时 morph；否则明确替换 |
| 仅切换页面、数据未变 | 不重播；必要时 resize |
| 实时刷新 | 节流，短更新或直接终态；不排队播放 |
| 用户点击“重播” | 可选 replay，提供恢复与错误记录 |
| reduced-motion | `animation:false`，直接最终数据 |

### 5.2 稳定身份

ECharts 数据 diff 依赖名称等身份。筛选前后保持 series id/name 与 data name 稳定，否则同一对象会被当成删除+新增，动画无法表达真实变化。
universal transition 还需要正确的 series id；拆分/聚合下钻需要 groupId/dataGroupId。没有稳定语义关系时，不为了炫技强行 morph。

### 5.3 enter 与 update 分开

```js
const motion = window.H5Motion.preference();
const option = {
  animation: !motion.reduced,
  animationDuration: motion.reduced ? 0 : 520,
  animationEasing: 'cubicOut',
  animationDurationUpdate: motion.reduced ? 0 : 280,
  animationEasingUpdate: 'cubicOut',
  animationThreshold: 1500
};
chart.setOption(option);
```

`animationThreshold` 是起始预算，不是性能保证。根据实际图形复杂度与设备测试调整。
偏好运行时变化时，更新既有实例的 animation 配置；不能只读取一次。

### 5.4 replay 的隔离

显式重播封装为独立函数，不混入普通筛选：

1. 从业务配置重建最终 option，或验证缓存的完整配置。
2. 记录当前任务序号；新任务到来时旧任务失效。
3. 若确需 `clear()`，随后立即恢复；异常时重新 init 或 setOption 回退，并记录错误。
4. 不让 replay 阻止导航和筛选。
5. 测试切页往返后的 series、markLine、formatter、渐变和数据是否一致。

`getOption()` 是规范化后的配置，不应默认视为无损源码。

## 6. 动效管理

### 6.1 一份偏好输入

```js
const media = matchMedia('(prefers-reduced-motion: reduce)');
function onMotionChange() {
  document.documentElement.dataset.motion = media.matches ? 'reduced' : 'full';
  updateAllChartMotion(media.matches);
}
media.addEventListener('change', onMotionChange);
```

旧 WebView 可用 `addListener/removeListener` 回退。页面还可提供用户级“减少动效”开关；用户显式选择优先于默认，但不应与系统偏好冲突。

### 6.2 最新任务优先

每次筛选或切页递增序号。异步返回、rAF 和定时器执行前检查序号；不匹配就只清理，不提交旧状态。
能用 AbortController 取消请求时同时取消，但序号仍需防止不可取消的回调回写。

避免用固定 1.4s 全局锁解决连点。若某段动画确实不可中断，按所有 delay 的最大值加 duration 计算预算，并把清理定时器独立注册。

### 6.3 数字滚动

- 只动画视觉文本，最终 `aria-label` 直接写最终值。
- 保存并取消上一帧动画；新值到来从当前值插值到最新值。
- 结束强制调用原格式器输出精确值。
- reduced-motion 直接终态；不在 aria-live 中逐帧更新。

## 7. CSS 动效与降级

```css
.page-enter { animation: page-in 320ms cubic-bezier(.2,0,0,1); }
@keyframes page-in {
  from { opacity: .72; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
  }
}
```

这段 CSS 只是最后保险，仍要在 JS/ECharts 中明确关闭动画。内容类不要写默认 `opacity:0`；若确有 reveal，采用增强类门控并提供终态兜底。

## 8. 专项验收

### 8.1 键盘

只用键盘完成：进入 tablist、前后切换、Home/End、打开筛选、打开详情、Escape、返回触发点。
检查焦点不丢、不进入隐藏页、不被抽屉吞掉，选中状态与视觉一致。

### 8.2 连续操作

快速执行“切页 12 次 + 筛选 10 次 + 抽屉开合 6 次”：最终页面和数据必须等于最后一次输入；控制台无错误；无永久锁、空白图和旧内容回写。

### 8.3 减少动效

分别验证：首次载入、数据更新、切页、数字变化、回顶、抽屉、无限状态灯。
不能只记录 `clear()` 次数。截图或浏览器探针要证明实际 `animation:false`/时长为 0、JS 不调用 smooth、最终值正确。

### 8.4 图表截图

普通模式等待 `rendered` 后截图；或减少动效/测试模式关闭动画后截图。
对“动画发生过”的断言先在已知有缺陷版本上确认会失败，避免写一个永远通过的探针。
