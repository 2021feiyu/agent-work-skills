# Agent Work Skills

**8 份"怎么让 Agent 把活干对"的作业手册。** 不是提示词合集，是带判据、带闸门、带踩坑记录的流程文件。

每个技能是一个 `SKILL.md`（YAML frontmatter + 正文），遵循 Agent Skills 的通用约定：Agent 只在描述命中时加载正文，从而按需占用上下文。

```
skills/
  skill-builder/            怎么造一个 skill（规范 + 10 条检查表）
  skill-maintenance/        怎么救一个被改烂的 skill（多轮追加后的结构重构）
  task-execution-framework/ 中大型任务的 8 步纪律与三道闸门
  massive-task-orchestrator/多 Agent 分片编排（DAG + 波次 + 独立验证）
  deep-research-report/     万字级长报告流水线（分片并行 + 编号重排 + 审计）
  h5-dashboard-dev/         单文件 H5 看板（视觉系统 + 图表 + 截图验收）
  output-path-guard/        产出物落盘治理（禁止写桌面 / 用户目录）
  question-scout/           提问脚手架（不替你想，逼你想清楚）
```

---

## 这些技能解决什么问题

大多数 Agent 任务失败，不是因为模型不够强，而是因为**流程缺闸门**：

| 常见失败 | 对应技能 | 它的做法 |
|---|---|---|
| 一上来就写代码，写完发现方向错 | `task-execution-framework` | 先定义"做成什么样"，找参照，再规划，最后动手；G0/G1/G2 三道闸门，不过不许往下走 |
| 几十个文件的大改造，改到一半乱掉 | `massive-task-orchestrator` | 拆 DAG、分波次、每个 Agent 只读不写、主线程统一集成 |
| 十万字报告写出来像流水账 | `deep-research-report` | 先定结构再填内容；分片并行后由主线程统一重排编号与口径 |
| 看板"代码都对，拼起来很丑" | `h5-dashboard-dev` | 视觉判断必须靠截图；配套 `audit_h5.py` 做 13 项自动校验 |
| 产出物写到桌面 / C 盘，交付找不到 | `output-path-guard` | 白名单路径 + 提交前审计脚本 |
| Skill 越改越厚，前后矛盾 | `skill-maintenance` | 识别"补丁式演进"的累积损伤，按使用顺序重排，合并重复段落 |
| 造出来的 skill 触发不到 / 触发错 | `skill-builder` | frontmatter 规范、description 写法、渐进加载、检查表 |
| 讨论浮在表面，问不出真问题 | `question-scout` | 把"提问"拆成可练的动作：问题源模式库 + 句式库 |

---

## 怎么用

### 方式一：装进支持 Agent Skills 的宿主

```bash
cp -r skills/* ~/.claude/skills/       # Claude Code
# 或
cp -r skills/* ~/.workbuddy/skills/    # WorkBuddy
```

宿主会在系统提示里只注入每个技能的 `name` 与 `description`，正文按需加载。

### 方式二：直接当文档读

不装也行。每个 `SKILL.md` 都是自包含的——`cat` 出来贴进对话，Agent 就能按里面的流程执行。

### 方式三：改成你自己的

这些文件里最有价值的部分是**判据**（什么算"过"、什么情况必须停下来问人），不是具体命令。建议保留判据、替换掉与你环境相关的路径与工具名。

---

## 关于跨技能引用

正文里会出现一些未随本仓库发布的技能名（如 `long-task-executor`、`skill-cross-machine-sync`、`enterprise-deep-research`）——它们来自同一套工作法的其他部分，本仓库只挑了通用性最强的 8 个。看到这类引用时按语义理解即可，不影响单独使用。

同样，文中 `~/.workbuddy/...` 是 WorkBuddy 的路径约定；换到 Claude Code 就把根目录换成 `~/.claude/`。

---

## 目录约定

每个技能目录的结构遵循同一规则：

```
<skill-name>/
  SKILL.md            入口：frontmatter（name / description）+ 正文
  references/         长参考资料，正文按需指向
  scripts/            可直接运行的脚本
  assets/             模板、主题、示例
```

`references/` 与 `scripts/` 不是必填——只有当正文确实需要"展开会太长"或"要跑一段代码"时才建。

---

## License

MIT
