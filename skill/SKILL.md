---
name: work-tracker
description: 工作记录与周报追踪。记录每日工作内容（关联项目），管理周计划，定时提醒汇报，生成周报和工时清单（飞书文档）。当用户说"今天做了XXX"、"记录工作"、"本周计划"、"查工作"时触发。
---

# work-tracker — 工作内容记录与周报追踪

## 触发条件

- 用户说"今天做了XXX" / "记录一下" / "刚才干了XXX"
- 用户说"本周计划" / "这周要做XXX"
- 用户问"我上周做了什么" / "查工作记录"
- cron定时触发（每日提醒 / 周报 / 工时清单）

## 数据库位置

`~/.hermes/work-tracker/work.db`（SQLite，4张表：projects / work_logs / weekly_plans / plan_progress）

## 核心操作

### 1. 记录工作

用户随意说，Agent解析后调用：
```bash
python ~/.hermes/work-tracker/scripts/record.py \
  --project "项目名称" \
  --content "工作内容" \
  --category "文档" \
  --duration 150 \
  --task "任务名（可选）" \
  --date "2026-08-17" \
  --time "2026-08-17 09:10:32"
```

**必须追问的字段**：
- 项目名：缺失则追问
- 工作内容：缺失则追问（具体做了什么、产出是什么）
- 工时：缺失则追问

**铁律 - 项目不得随意创建**：
录入前**先查询已有项目**（`SELECT id,name FROM projects`），把输入的项目名与已有项目比对。如果与某个已有项目重合/高度相关（如«园博苑»↔«园博苑无人游船»）：
1. 直接用已有项目，不新建；
2. 若拿不准（用户输入简写/别名，疑似对应已有项目），**先在记录前询问用户确认**，得到确认后再落库并挂到该已有项目；
3. 只有确认在已有项目里没有对应时，才允许 record.py 新建项目。

严禁 record.py 默认新建一个看似相关实则重复的项目。若误建，改 `work_logs.project_id` 指向正确项目并删除多余 projects 行（先确认无其他工单引用）。

**铁律 - 日期必须先获取**：
录入、查询、汇总任何涉及日期的操作前，**必须先执行 `date '+%Y-%m-%d %A %H:%M:%S'` 获取真实当前日期和星期**，绝不靠上下文、会话时间或记忆推算。实测曾把 8-17 错写成 8-18 引发用户困惑，也曾算错星期几。record.py 不传 --date 会自动取 date.today()，所以**默认不传 --date 即可**，仅当明确需要录入历史日期时才传。

**执行模板**：
```bash
# 第一步：获取当前时间（必须执行）
date '+%Y-%m-%d %A %H:%M:%S'
# 输出示例：2026-08-21 Thursday 10:30:45

# 第二步：基于真实日期执行操作
python ~/.hermes/work-tracker/scripts/query.py --today
```

**铁律 - 操作必须验证**：
记录工作后，**必须立即执行验证**，不能假设操作成功：
```bash
python ~/.hermes/work-tracker/scripts/query.py --date YYYY-MM-DD
```
验证输出中是否包含刚记录的内容。如果：
- 验证成功 → 报告"记录完成 ✅"并显示记录 ID
- 验证失败（记录未出现）→ 明确告知用户"❌ 记录失败"，并显示错误信息
- 工具返回错误 → 不要忽略，立即告诉用户具体错误（如 no such column、no such table 等）

**实测案例**：2026-08-20 两次记录都因 SQL 错误失败（`no such column: hours`、`no such table: weeks`），但 Assistant 错误地报告了"记录完成"，导致数据丢失。

**汇总只查数据库**：
做"今天/本周"汇总时只从 work.db 查，不引用 memory/hindsight 中可能已被清除的推测数据。

**可推断的字段**（除日期外）：
- 时长词（2小时/半天）→ duration_min
- 关键词 → category（文档/开发/会议/沟通/调研/其他）

**状态（status）**：
- `done`（默认）— 已完成的工作
- `planned` — 计划中/待完成的工作（如"下午要开会"）
- 完成后用 `update_status.py --id X --status done` 更新

**拆解规则**：
- 用户一句话包含多个子任务时，必须拆成多条记录
- 每条记录必须有具体的工作内容/产出描述
- 日期和工时可以推测，但内容必须明确

### 2. 查询工作

```bash
python ~/.hermes/work-tracker/scripts/query.py --today      # 今天
python ~/.hermes/work-tracker/scripts/query.py --week       # 本周
python ~/.hermes/work-tracker/scripts/query.py --date 2026-08-17
python ~/.hermes/work-tracker/scripts/query.py --range 2026-08-11 2026-08-15
```

### 3. 周计划

```bash
# 添加计划（JSON格式）
python ~/.hermes/work-tracker/scripts/plan.py --add --items '[{"text":"PRD编写","project":"渔船审图"}]'

# 显示计划
python ~/.hermes/work-tracker/scripts/plan.py --show

# 更新状态（0开始）
python ~/.hermes/work-tracker/scripts/plan.py --update --index 0 --status done
```

### 5. 生成周报

**主工具（产品组官方模板）：**
```bash
python ~/.hermes/work-tracker/scripts/member_report.py --week 2026-W45
python ~/.hermes/work-tracker/scripts/member_report.py --range 2026-10-26 2026-11-01
```
- 事项分组依据 `~/.hermes/work-tracker/matters.json`（项目+内容前缀 → 事项名称/版本）
- 脚本输出骨架：工作内容/工时自动填充，**本周进展/风险提示/下周计划为〔待填〕**，Agent 结合上下文补全后交付；下周计划必须含负责人+预期结果+日期
- 「⚠️待确认」标记=事项名待组长确认；「待映射记录」=泛称「产品工作」未带前缀的漏网记录，发现即补 matters.json

**matters.json 维护规则**：
- 新事项首次登记时，同步在 matters.json 加映射，status 标「待确认」；组长确认名称/归属后改「confirmed」
- 登记工时时内容前缀必须与 content_prefix 一致（跨周同名）；前缀即映射键，登记要规范（如「文鳐xxx」「AI智能机舱：xxx」）
- excluded=不入周报的例会；other_matters=独立工作归「其他事项」表

**旧工具 report.py**（自由格式周报，模板推行前可用）：

```bash
python ~/.hermes/work-tracker/scripts/report.py           # 本周
python ~/.hermes/work-tracker/scripts/report.py --week 2026-W34
```

输出Markdown，Agent拿到后：
1. 补充"下周计划/待协调/建议"（根据上下文归纳）
2. 用 lark-cli 创建飞书文档

### 5. 生成工时清单

```bash
python ~/.hermes/work-tracker/scripts/timesheet.py           # 本周
python ~/.hermes/work-tracker/scripts/timesheet.py --week 2026-W34
```

输出Markdown，Agent拿到后用 lark-cli 创建飞书文档

## Cron 定时任务

| 任务 | 时间 | 内容 |
|------|------|------|
| 每日提醒 | 周一~周五 20:00 | 飞书消息：计划进度 + 今日已汇报 + 提醒补充 |
| 周报 | 周五 21:00 | 生成周报 → 飞书文档 |
| 工时清单 | 周五 21:00 | 生成工时清单 → 飞书文档 |

## 每日提醒格式（飞书消息）

```
📋 本周计划进度（MM-DD ~ MM-DD）

完成 X/Y：
✅ 已完成项
⬜ 未完成项

————————
📝 今日已汇报（MM-DD）

YYYY-MM-DD HH:MM:SS【项目名】工作内容 [类别] X.Xh
...

今日合计：X.Xh

————————
💬 还有要补充的吗？
```

## 周报格式（2026-11-06 起按产品组官方模板）

**模板文件：references/weekly-report-template.md（产品组员周报填写要求与模板，用户 2026-11-06 提供）。生成周报前必须先读该文件。**

关键规则（与旧格式的差异）：
- **按事项填写，不按天流水账**。事项名称用实际项目/产品/商机名（如「文鳐大模型发布会演示」「AI智能机舱」），**禁用「产品工作」「其他」等泛称**——数据库挂「产品工作」的记录，周报里必须按内容前缀拆出真实事项名
- 表结构：事项名称 | 版本/期次（一期/二期/V1.1/不分期/—）| 具体工作内容（1、2、3分条，只写动作）| 人员与实际工时（本人承担内容，Xh）| 本周进展（成果+状态，区分已编制/已提交/已评审/客户确认/已上线）| 风险提示（无则填"无"）| 下周计划（负责人+工作+预期结果+日期）
- 独立工作（绩效考评、知识分享、资产沉淀等不属具体项目/产品/商机的）放「二、其他事项」表；已计入具体事项的不重复填
- 下周计划不得写"持续推进"；无后续填"—"
- 不重要零散小事仍可归并；**不写入周报的例会**：船舶海洋产品组会（内部例行组会，用户 2026-09-06 明确）
- 工时不重复计入多个事项

## 工时清单格式

4列表格：项目 | 所属任务 | 工作内容 | 工时
附按项目/类别/天的汇总

## 初始化

```bash
python ~/.hermes/work-tracker/scripts/init_db.py
```
