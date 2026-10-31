---
name: output-path-guard
description: 产出物落盘路径审计与治理。当任务会生成文件（报告/看板/图片/JSON/文档）时，用来自查产出物是否被写到用户桌面/用户目录/C盘；也用于排查已存在的路径污染（expanduser("~")/Desktop 硬编码）并批量修复。Use when (1) 准备生成或交付文件产出物，(2) 用户反馈文件被放错位置，(3) 代码审查时排查输出路径，(4) 复盘"文件为什么跑到桌面/下载文件夹"类问题。
agent_created: true
---

# 产出物落盘路径治理

## 为什么有这条规则

**绝对红线：任何产出物只能写入当前项目工作空间，严禁写入用户桌面、用户目录、C 盘任何位置。**

**事故来源（真实案例，2026-09-14）**：某自动化监测项目的 `runner.py` 从早期 Word 报告阶段继承了「优先写桌面 → 再复制归档」的双份策略。某次从 Word 改 H5 交付时**只替换了文件格式，没有清理路径设计**，导致看板连续 5 个月被写入 `C:\Users\<用户名>\Desktop\`，累积 **113 个文件**，长期未被发现。

**为什么长期没被发现**：脚本日志把桌面路径打印成 `[OK] 看板已生成: C:\...\Desktop\...`，每一步都显示成功。当时只验证了「文件是否生成、MD5 是否一致」，**从未校验「生成的位置对不对」**。教训：验证结果 ≠ 验证约束。

## 三类典型缺陷形态

| 形态 | 代码特征 | 危险度 |
|:---|:---|:---:|
| **硬编码用户路径** | `"C:/Users/xxx/Desktop/..."`、`"C:/Users/xxx/Documents/..."` | 🔴 最高 |
| **运行时拼接用户目录** | `os.path.expanduser("~")` + `"Desktop"` / `"Downloads"` | 🔴 最高 |
| **双份输出策略** | 先写用户可见位置（桌面/下载）"方便查看"，再复制到归档 | 🟠 高（会持续累积） |
| **构建产物混入交付物**（2026-09-23 新增） | `__pycache__/`、`*.pyc`、临时 `.py` 探针、`_probe/` 快照目录、编辑器备份文件被一起打包/归档 | 🟡 中（污染交付物，**且会让"文件数比对"这类自检判据失真**） |

**「构建产物混入交付物」的两个真实后果**（人力看板实战）：
1. 跑一次 `py_compile` 校验语法，就在 `tools/` 下留下 `__pycache__` → **归档清单里 tools 由 4 个文件变 7 个**，而归档工具自身的"源目录 vs 快照 文件数一致"判据随之失真
2. 探针脚本、注册表备份、截图中间态的**临时产物**容易跟着进交付目录

**处置**：
- 归档/打包工具显式忽略：`shutil.ignore_patterns("__pycache__", "*.pyc")`（或 `.gitignore` / 打包排除规则）
- **每类产物界定"读者"**：给人看的交付物 / 过程证据（放固定过程目录）/ 构建产物（不进任何归档）
- 归档后的自检判据要**同时比对"文件数"与"逐文件哈希"** —— 只比文件数会在产物混入时给出"通过"的假象

## 标准处置流程

### Step 1 — 扫描（只读，不改动任何文件）

```bash
python <skill_dir>/scripts/audit_paths.py "<项目根目录>"
```

脚本会输出：命中文件、行号、命中片段、危险等级。**先把结果给用户看，不要直接改。**

### Step 2 — 分类判断

对每处命中问三个问题：
1. 这是**输出路径**，还是只读的资源查找路径？（如字体查找 `~/Library/Fonts` → 无害，放行）
2. 这是**产出物**，还是**状态/缓存文件**？（如 `~/.workbuddy/sync-states` → 可接受，但优先挪进工作空间）
3. 是否已经产生过实际污染？（查用户目录里有没有对应文件）

### Step 3 — 清理已有污染（严格按安全规则）

**⚠️ 桌面/用户目录属于个人文件目录，操作前必须：**
- 先全量 zip 备份 → 确认备份可读 → 再迁移
- 逐文件 MD5 前后校验
- 每批 ≤10 个文件
- **移动**而非删除；删除走回收站（Windows 用 `SHFileOperationW`，见下方坑）
- 禁止 `rm -rf` / `del /S /Q` / `shutil.rmtree()` 作用于用户目录

### Step 4 — 修复代码，只留一个输出目标

```python
# ❌ 修改前：双目标，桌面优先
DESKTOP_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
output_path = os.path.join(DESKTOP_DIR, name)
generate(output_path)
shutil.copy2(output_path, archive_dir)          # 归档是"附属"

# ✅ 修改后：单目标直接写入工作空间
REPORT_DIR = os.path.join(PROJECT_ROOT, "每日分析报告")
target_dir = output_dir or REPORT_DIR            # 白名单内
os.makedirs(target_dir, exist_ok=True)
output_path = os.path.join(target_dir, name)     # 失败再回退项目目录
generate(output_path)
```

要点：**回退路径也必须在工作空间内**；不要保留任何"写桌面"的分支。

### Step 5 — 固化到三处（否则会复燃）

1. **代码注释**：在输出路径常量上方写明 vX 路径治理 + 禁止桌面
2. **skill / 任务 prompt**：写入路径白名单表 + 红线清单 + 自检要求
3. **记忆文件置顶横幅**：历史记录里若有「桌面+归档」等旧表述，必须在文件顶部声明**已作废**

> ⚠️ 第 3 点最易被忽略：自动化任务会读取自己的历史 memory。若历史里写着"交付：桌面+归档"，模型会把旧行为当范例照做，**污染复燃**。

### Step 6 — 验证（必须验证"落点"，不只是"存在"）

```python
# 断言产出物不在用户目录
assert not os.path.exists(os.path.join(os.path.expanduser("~"), "Desktop", name))
# 断言产出物在工作空间白名单内
assert os.path.abspath(out).startswith(os.path.abspath(PROJECT_ROOT))
```

## 已知坑

| 坑 | 表现 | 解法 |
|:---|:---|:---|
| `send2trash` 中文路径失效 | `FileNotFoundError: ... 8.3 短文件名` | 改用 ctypes 调 `SHFileOperationW`（`FOF_ALLOWUNDO \| FOF_NOCONFIRMATION \| FOF_SILENT \| FOF_NOERRORUI`） |
| Bash 转义污染横幅 | 用 `bash -c "python -c '...'"` 写含反斜杠的文本 → `\\\\` 被折叠成 `//` 或内容丢失 | **写成 `.py` 文件再执行**，别用 `-c` 内联长文本 |
| 横幅写入非幂等 | 重复执行 → 文件出现双横幅 | 剥离逻辑要"删除所有横幅块再重建"，不要假定只有一块 |
| 剥离锚点选错 | 原文没有 `# ` 一级标题时剥离失败 | 锚点用**横幅标记行**，不要用 `# ` 标题 |
| Git Bash PATH 异常 | `dirname: command not found` / `cp: command not found` | 用 Python 的 `shutil`/`os` 替代 shell 工具链 |

## 交付方式

展示产出物一律用 `present_files` 工具指向工作空间内的绝对路径 —— **不是**先把文件复制到桌面"方便用户看"。这一步是污染的主要入口，务必守住。
