# work-tracker — 工时登记与周报系统

工作记录、周计划管理、周报/工时清单生成的一体化工具。数据存 SQLite，随 Hermes Agent 使用（Agent 解析自然语言登记，脚本落库并验证）。

## 仓库结构

```
work-tracker/
├── skill/                     # Hermes Agent Skill（work-tracker）
│   ├── SKILL.md               # Skill 主文档：触发条件、登记/查询/周报流程、铁律
│   └── references/
│       └── weekly-report-template.md  # 产品组官方周报模板（按事项填写规范）
├── scripts/                   # 可执行脚本
│   ├── init_db.py             # 初始化 SQLite（4表：projects/work_logs/weekly_plans/plan_progress）
│   ├── record.py              # 登记工时（--project/--content/--category/--duration/--date/--time）
│   ├── query.py               # 查询（--today/--week/--date/--range）
│   ├── plan.py                # 周计划管理（--add/--show/--update）
│   ├── report.py              # 自由格式周报
│   ├── timesheet.py           # 工时清单（按项目/类别/天汇总）
│   ├── member_report.py       # ★ 按产品组官方模板生成周报骨架（配合 matters.json）
│   ├── update_content.py      # 修改记录内容
│   └── update_status.py       # 更新记录状态（done/planned）
├── matters.json               # ★ 事项映射：数据库项目+内容前缀 → 周报事项名称/版本/状态
├── data/
│   └── work.db                # SQLite 数据库快照（113条工时，2026-08-17 ~ 2026-11-04，24个项目）
└── README.md
```

## 数据模型

**work.db（4 表）**

| 表 | 用途 | 关键字段 |
|---|---|---|
| projects | 项目表（id, name） | 24 个项目：产品工作、长航集团、中远绿色智能、token平台… |
| work_logs | 工时记录（id, date, time, project_id, task, content, category, duration_min, week_id, status） | 113 条，category ∈ 文档/开发/会议/沟通/调研/其他 |
| weekly_plans | 周计划 | JSON items |
| plan_progress | 计划进度 | — |

## 核心机制：事项映射（matters.json）

工时数据库按「项目」存储，产品组官方周报要求按「事项」填写且禁用「产品工作」等泛称。解决方案是**映射层**：

- 数据库项目名保持公司工时口径不动；
- 登记工时时内容开头带**事项前缀**（如「文鳐xxx」「AI智能机舱：xxx」），前缀即映射键；
- `member_report.py` 出周报时按 matters.json 把记录自动归到真实事项名（含版本/期次），泛称记录落入「待映射」警告区，例会走 excluded 不入周报。

```json
{
  "name": "文鳐大模型发布会演示", "version": "不分期",
  "match": {"project": "产品工作", "content_prefix": ["文鳐"]},
  "status": "confirmed"
}
```

## 快速上手

```bash
# 初始化数据库
python scripts/init_db.py

# 登记工时
python scripts/record.py --project "产品工作" --content "文鳐模型演示界面调整" \
  --category "开发" --duration 480 --date "2026-10-27"

# 查询
python scripts/query.py --today / --week / --date 2026-10-27 / --range A B

# 按产品组官方模板出周报（进展/风险/下周计划三列由 Agent 结合上下文填全）
python scripts/member_report.py --week 2026-W44
python scripts/member_report.py --range 2026-10-26 2026-11-01
```

## 维护铁律（摘自 SKILL.md）

1. **登记前必须 `date` 确认真实日期**——不靠上下文推算，历史上曾因此错登日期。
2. **记录后必须立即验证**（query 回查），不能假设成功——曾因 SQL 错误导致数据丢失未发现。
3. **项目不得随意新建**——录入前先查 projects 表，疑似已有项目先确认再落库。
4. **数据库项目名 ≠ 周报事项名**——周报口径走 matters.json 映射，禁用「产品工作」泛称。
5. 新事项首次登记时同步补 matters.json（status=待确认），组长确认后改 confirmed。

## 运维快照（2026-11-06）

- 数据库 113 条记录跨 2026-08-17 ~ 11-04，覆盖 W34 起各周工时；
- member_report.py 已用 W44/W45 双周验证：事项分组、工时汇总、例会排除均正确；
- gh token 曾于 2026-11-06 失效，推送通道改用 SSH（id_ed25519，GitHub 注册于 starsgan 账号）。
