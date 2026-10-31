---
name: skill-builder
description: >
  按 WorkBuddy 官方规范创建和审查 Skill。Use when user asks to create, build, audit, review,
  or improve a skill/SKILL.md. Covers frontmatter fields, directory structure, description
  writing, progressive loading, and 10-point quality checklist.
  Do NOT use for general coding tasks, config file editing, or non-skill documentation.
  **既有 skill 的多轮追加损伤重构、跨 skill 职责重叠审计**走 `skill-maintenance`；
  **跨机传输 / 回传合并 / 判定两版谁更优**走 `skill-cross-machine-sync`（见下方「与相邻技能的分工」）。
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, WebFetch
agent_created: true
---

# Skill 创建器（WorkBuddy 官方规范）

按 WorkBuddy 官方文档 + 社区最佳实践创建、审查、优化 Skill。

## 与相邻技能的分工

本 skill 与 `skill-maintenance`、`skills-security-check`、`skill-cross-machine-sync` 都涉及「skill」，
但管的是**不同阶段**。先对号入座再动手：

| 场景 | 用哪个 |
|------|--------|
| 新建一个 skill | **本 skill** |
| 审查某个 skill 的内容质量 / 10 项检查 | **本 skill** |
| 给 skill 追加 1—2 条新规则 | **直接追加**（任何 skill 都不必调用） |
| skill 已累计多轮更新、结构混乱（顺序错乱 / 主题散落 / 兜底章节） | `skill-maintenance` |
| 多个 skill 职责重叠、抢同一触发词、互相禁止使用对方 | `skill-maintenance` 的跨技能审计 |
| 审查 skill 的安全性（供应链投毒、脚本风险） | `skills-security-check` |
| 把 skill 发到另一台机器 / 接收回传 / 判定合并谁更优 | `skill-cross-machine-sync` |
| 只是「文件名写错 / frontmatter 损坏」这类加载故障 | 直接修，不必调用任何 skill |

> **边界提示**：本 skill 的职责是「让 skill 符合规范、能被正确加载与匹配」；
> `skill-maintenance` 的职责是「让 skill 在累计多轮修改后仍然找得到该找的东西」；
> `skill-cross-machine-sync` 的职责是「判定哪些该跨机传、以及合并时谁更新」。
> **判断口诀：新建与质量看本 skill，结构与重叠看 skill-maintenance，跨机看 skill-cross-machine-sync。**

## 工作流程

### Step 1: 理解需求
向用户确认：
- Skill 解决什么问题？（单一职责）
- 什么场景触发？（关键词 / 用户意图）
- 输出什么？（文件 / 报告 / 代码修改）
- 需要什么工具权限？

### Step 2: 创建目录结构

```
~/.workbuddy/skills/<skill-name>/     # 用户级（个人用）
.codebuddy/skills/<skill-name>/       # 项目级（团队共享）
├── SKILL.md                          # 必须 — 核心操作手册
├── scripts/                          # 可选 — 确定性执行脚本
├── references/                       # 可选 — 按需加载的参考文档
└── assets/                           # 可选 — 模板 / 配置等资源
```

- `name` 全小写 + 连字符，1-64 字符
- 用 `scripts/init_skill.py`（位于技能创建器内置 skill 中）初始化目录
- 不使用的空目录不要保留

### Step 3: 编写 SKILL.md

#### Frontmatter（YAML）

```yaml
---
name: <skill-name>                  # 小写+连字符, 1-64 字符
description: >                      # 核心——决定 AI 何时触发
  <触发条件 + 能力边界 + 负面案例>
allowed-tools: <tool1, tool2>       # 工具白名单（最小权限原则）
agent_created: true                 # 必须 — 允许 skill_manage 管理
---
```

**description 模板**：
```
Use when [触发条件/关键词] to [目标行动].
Do NOT use when [排除场景].
```

#### Body 结构

```markdown
# <Skill 标题>

## 工作流程
1. 步骤 1 — 做什么
2. 步骤 2 — 做什么

## 使用方式
<代码示例 — 用代码而非纯文字描述>

## ⚠️ Gotchas
- <AI 容易犯的错 1>
- <AI 容易犯的错 2>

## 输出规范
<返回值 / 文件格式 / 报告结构>
```

### Step 4: 填充 resources

- **scripts/** — 需要确定性执行的操作写成脚本（如 `check_deps.py`），不要靠 AI 每次自由发挥
- **references/** — 详细的参考文档（如 API 文档、编码规范），AI 按需加载
- **assets/** — 模板文件、配置文件（如 `config.yaml`），AI 复制后使用

### Step 5: 执行 10 项质量检查

对参照表 `assets/audit-checklist.md` 逐项检查，所有项通过才算完成。

## Frontmatter 字段完整参考

| 字段 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `name` | 是 | 小写+连字符，1-64字符 | `pdf-editor` |
| `description` | 是 | 决定 AI 何时触发，<1024字符，含触发条件+排除场景 | 见上方模板 |
| `allowed-tools` | 推荐 | 工具白名单，支持模式匹配 `Bash(git:*)` | `Read, Write, Bash(python *)` |
| `agent_created` | 是 | 固定 `true`，允许 skill_manage 管理 | `true` |
| `context` | 可选 | `fork` 在隔离子代理中运行 | `fork` |
| `agent` | 可选 | 指定子代理类型（仅 context:fork 时有效） | `Explore` |
| `user-invocable` | 可选 | `false` 从 / 菜单隐藏，仅 AI 内部用 | `false` |
| `disable-model-invocation` | 可选 | `true` 仅手动触发，不出现在 Skill 工具中 | `true` |

## 渐进式加载模型

```
L1: name + description       ← 始终在上下文 (~100 tokens)
L2: SKILL.md body            ← 触发时加载 (<5K tokens, <500行)
L3: scripts/ references/     ← 按需加载 (<5K tokens/文件)
```

**设计约束**：SKILL.md body 不要超过 500 行。详细信息放 references。

## 5 个编写技巧

1. **description 是灵魂** — 含触发条件 + 能力边界 + 负面案例。写差了 AI 根本不会触发
2. **先调研再写** — 让 AI 搜索最佳实践再设计结构，质量翻倍
3. **单一职责** — 超过 500 行就拆分。不要做一个"万能 Skill"
4. **代码优于文字** — `grep -rn "password" src/` 比"搜索硬编码密钥"更准确
5. **Gotchas 防翻车** — 专门写 AI 容易犯的错，ROI 最高的一段

## 变量占位符

SKILL.md 中可用的自动替换变量：

| 占位符 | 替换为 |
|--------|--------|
| `${CODEBUDDY_SKILL_DIR}` | SKILL.md 所在目录绝对路径 |
| `${CODEBUDDY_SESSION_ID}` | 当前会话 ID |
| `${MY_ENV_VAR}` | 环境变量值 |
| `${MY_ENV_VAR:-默认值}` | 环境变量，缺失时用默认值 |

## ⚠️ Gotchas

- **不要跳过 10 项质量检查** — 写完必须逐项自查
- **description 不要超过 1024 字符** — 太长 AI 匹配效率低
- **allowed-tools 必须是最小权限** — 不要给 Bash 全权限
- **空目录不要保留** — references/ assets/ 没用就删
- **脚本不要靠 AI 现场写** — 确定性操作用 scripts/ 预置
- **WorkBuddy 用 `.workbuddy` 前缀** — 不是 `.codebuddy` 也不是 `.claude`
