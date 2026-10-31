# 真实浏览器验证：工程坑与假阳性识别

> **适用**：用 Playwright / playwright-cli 做真实浏览器验收（主文档 §9.1「浏览器交互」「视觉截图」两栏的具体落地）。
> **层级**：P1 可用性门禁——**验证本身失败而没被察觉，等于拿假证据下结论**，比不验证更危险。
> **来源**：本地《H5开发手册》§11 实测坑 13 条 + 后续补的截面纪律。

---

## 0. 一条前提

**自查不算验证。** 三条线必须分开跑，任何一条都不能替代另一条：

| 线 | 工具 | 只能证明 |
|---|---|---|
| 结构 | 标签配对 + `node --check`（**不要用括号计数**，正则字面量会骗过它） | 语法没过不去 |
| 渲染 | Playwright 起真实浏览器，量 `scrollWidth`、数 canvas、抓 console | 浏览器里实际长什么样 |
| 数据 | 独立脚本重读源文件，与页面取值对账 | 数字对得上 |

---

## 1. 环境类坑（报错信息完全不指向真因）

| # | 现象 | 真因 | 解法 |
|---|---|---|---|
| 1 | 页面被拦截，导航失败 | `file://` 协议被 playwright 拒绝 | 起本地 HTTP 服务（`python -m http.server`）再访问 |
| 2 | `ERR_NAME_NOT_RESOLVED` | 中文文件名被当成域名解析 | 对文件名做 URL 编码 |
| 3 | `ERR_FILE_NOT_FOUND`，路径看不出问题 | `Path.as_uri()` **已经编码过**，再 `quote` 一遍成了双重编码（`%25E6…`） | `file://` 场景下 `page.goto(pathlib.Path(f).as_uri())` 到此为止，不要再编码 |
| 4 | `Cannot find module`，路径里出现奇怪盘符（如 `d:\c\Users\...`） | shim 把路径拼到了当前 cwd 的盘符上 | 改用 node 直调绝对路径 |
| 5 | `dirname: command not found` / `ls: command not found` / `cp` 同类 | Git Bash 的 PortableGit 命令集从 PATH 丢失 | 每条命令前显式加 PATH（**shell state 不跨调用持久，必须每次带**）；或用 Python 的 `shutil` 替代 shell 工具链 |
| 6 | `ERR_PACKAGE_PATH_NOT_EXPORTED` | playwright-cli 0.1.0 与新版 playwright 不兼容（`require('playwright/lib/mcp/terminal/program')` 在 1.5x 已不导出） | 改用自写 node 脚本调 playwright |
| 7 | 工具突然找不到 | managed node 的**版本目录名会变**（如 `22.22.2` → `22.22.2-3`），而 `@playwright/cli` 不随之迁移 | 先 `ls <binaries>/node/versions/` 确认真实目录名；缺失则重装，再用绝对路径调用 |

---

## 2. 时序类坑（会产生「数据错了」的假结论）

| # | 现象 | 真因 | 解法 |
|---|---|---|---|
| 8 | `canvas` 数 = 0，判为图表没渲染 | Tab 懒加载走 RAF 延迟 init，同步查询拿到的是 init 之前的状态 | `eval` 必须 `async/await` 等待后再断言，不能同步查 |
| 9 | 截图截到布局错乱 | 页面开了 `html{scroll-behavior:smooth}`，`scrollTo` 后立即截图 = 平滑滚动**中间态** | `sleep ≥1.2s` 再截图 |
| 10 | 断言拿到空字符串 / 无输出 | `eval` 多行脚本会丢输出 | 包成单行 IIFE 返回字符串 |

---

## 3. 会话类坑（多页/多视口时最容易串页）

| # | 现象 | 真因 | 解法 |
|---|---|---|---|
| 11 | 报 `Browser 'xxx' is not open` | playwright-cli 会话**不跨 Bash 调用持久**（每次调用是新 shell，daemon 随会话结束） | `open / console / eval / screenshot` 必须链在**同一条命令**内（`;` 或 `&&` 串联） |
| 12 | **假溢出误报**：明明没问题却报横向溢出 | 共享浏览器实例中，`goto` 打开的页面与"当前页"不同步，`eval` 作用到了另一个页面 | 每档视口用**独立会话** `-s=<name>`；`eval` 内加 `document.title` 断言防串页 |
| 13 | 截图目录找不到 | screenshot 保存在**创建会话时 cwd** 的 `.playwright-cli/`，与当前 shell cwd 可能不一致 | 用绝对路径指定输出目录 |

> **第 12 条是最贵的一条**：它让你以为布局坏了，然后去改本来正确的 CSS。凡是"报了溢出但肉眼看不出"的情况，先确认 `eval` 作用在哪个页面上。

---

## 4. 截图纪律

- **先看整页联系表，再看局部原尺寸。** 整页用于判断构图、节奏、重心；局部用于判断标签、边缘、对齐。两者不可互相替代。
- **移到 390px 也必须真截**，不能只用 device emulation 推断。除了 `scrollWidth`，还要看：正文字号、图表有效绘图区、轴标签碰撞、触控目标、抽屉焦点、表格可读性。
- **截图要绑定成品哈希**（见主文档 §9.2 manifest）。旧截图即使内容相近，也不能算当前版本的验收证据。
- **改完再截同一位置对比**，不要凭记忆判断"改好了"。

---

## 5. 两条容易被当成"小问题"的硬指标

### 5.1 控制台 0 错误

`console` 里有任何 error 都算未通过，不要因为"页面看起来正常"而放过。
最常见的无害报错是 favicon 404 —— 用 **data URI** 内嵌 favicon 消除它：

```html
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><rect width='16' height='16' fill='%231A365D'/></svg>">
```

### 5.2 数据文件带缓存戳

外链数据文件每次交付更新版本戳，否则浏览器缓存会让"改了没生效"：

```html
<script src="temp_data.json?v=YYYYMMDDHHMM"></script>
```

> 版本戳用**构建时间**生成，不要手填——手填会忘，忘了就表现为"线上还是旧数据"。

---

## 6. 验收清单（eval 一行流）

单条命令内链式执行，避免会话失效：

```bash
open -s=v1 "http://localhost:8765/page.html" \
  && eval -s=v1 "JSON.stringify({title:document.title,sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth,canvas:document.querySelectorAll('canvas').length})" \
  && screenshot -s=v1 --full-page -o ./qa/full.png
```

断言条件：`sw <= cw`（无横向溢出）、`canvas > 0`（图表已渲染）、`console` 无 error。
