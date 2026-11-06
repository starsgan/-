#!/usr/bin/env python3
"""按产品组官方模板（references/weekly-report-template.md）生成组员周报骨架。

用法：
  python member_report.py --week 2026-W44
  python member_report.py --range 2026-10-26 2026-11-01

事项维度分组依据 matters.json（数据库项目+内容前缀 → 事项名称/版本）。
工作内容与工时自动填充；本周进展/风险提示/下周计划留〔待填〕，由 Agent 结合上下文补全。
"""
import argparse, json, sqlite3, datetime, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DB = os.path.join(ROOT, 'work.db')
MATTERS = os.path.join(ROOT, 'matters.json')
NAME = '甘来杰'
GROUP = '产品组'


def week_range(week_str):
    year, wk = week_str.split('-W')
    year, wk = int(year), int(wk)
    d = datetime.date(year, 1, 4)
    monday = d - datetime.timedelta(days=d.isoweekday() - 1) + datetime.timedelta(weeks=wk - 1)
    return monday, monday + datetime.timedelta(days=6)


def fmt_h(minutes):
    h = minutes / 60.0
    return ('%g' % h) + 'h'


def strip_prefix(content, matter_name):
    for sep in ['：', ':']:
        p = matter_name + sep
        if content.startswith(p):
            return content[len(p):]
    return content


def match_log(project, content, cfg):
    """返回 (bucket, matter_dict)。bucket: matter/other/excluded/None"""
    c = content.strip()
    for m in cfg.get('excluded', []):
        if any(kw in c for kw in m.get('content_keywords', [])):
            return 'excluded', m
    for m in cfg.get('other_matters', []):
        if any(kw in c for kw in m.get('content_keywords', [])):
            return 'other', dict(m, version='—', status='confirmed')
    for m in cfg.get('matters', []):
        mt = m.get('match', {})
        if mt.get('project') and project != mt['project']:
            continue
        prefixes = mt.get('content_prefix', [])
        if prefixes:
            if any(c.startswith(p) or p in c for p in prefixes):
                return 'matter', m
        else:
            return 'matter', m
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--week', help='ISO周，如 2026-W44')
    ap.add_argument('--range', nargs=2, metavar=('START', 'END'), help='如 2026-10-26 2026-11-01')
    args = ap.parse_args()

    if args.range:
        start, end = datetime.date.fromisoformat(args.range[0]), datetime.date.fromisoformat(args.range[1])
        period = f'{start} ~ {end}'
    else:
        wk = args.week or f"{datetime.date.today().isocalendar()[0]}-W{datetime.date.today().isocalendar()[1]:02d}"
        start, end = week_range(wk)
        period = f'{start} ~ {end}（{wk}）'

    cfg = json.load(open(MATTERS, encoding='utf-8'))
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT w.date, p.name, w.content, w.duration_min FROM work_logs w "
        "JOIN projects p ON w.project_id=p.id WHERE w.date BETWEEN ? AND ? ORDER BY w.date, w.id",
        (start.isoformat(), end.isoformat())).fetchall()

    matters, others, excluded, unmapped = {}, {}, {}, {}
    for date, project, content, dur in rows:
        bucket, m = match_log(project, content, cfg)
        if bucket == 'excluded':
            if m['name'] not in excluded:
                excluded[m['name']] = [0, m.get('reason', '')]
            excluded[m['name']][0] += dur
            continue
        if bucket in ('matter', 'other'):
            key = (bucket, m['name'])
            info = {'version': m.get('version', '—'), 'status': m.get('status', 'confirmed'),
                    'items': [], 'minutes': 0, 'project': project}
            target = matters if bucket == 'matter' else others
            info = target.setdefault(m['name'], info)
            info['minutes'] += dur
            item = strip_prefix(content.strip(), m['name'])
            if item not in info['items']:
                info['items'].append(item)
        else:
            # 未映射：专用项目按项目名成事项；泛称「产品工作」标待确认
            if project == '产品工作':
                key = ('unmapped', '产品工作（泛称，需拆分真实事项名）')
                info = unmapped.setdefault(key[1], {'items': [], 'minutes': 0})
            else:
                key = ('matter', project)
                info = matters.setdefault(project, {'version': '—', 'status': 'confirmed',
                                                    'items': [], 'minutes': 0, 'project': project})
            info['minutes'] += dur
            if content.strip() not in info['items']:
                info['items'].append(content.strip())

    total = sum(m['minutes'] for m in matters.values()) + sum(m['minutes'] for m in others.values())

    out = []
    out.append(f'# 产品组员周报\n')
    out.append(f'**组别：** {GROUP}　**姓名：** {NAME}　**报告周期：** {period}\n')
    out.append('### 一、本周事项\n')
    out.append('| 事项名称 | 版本/期次 | 具体工作内容 | 人员与实际工时 | 本周进展 | 风险提示 | 下周计划 |')
    out.append('|---|---|---|---|---|---|---|')
    for name, m in matters.items():
        items = ' '.join(f'{i+1}. {t}' for i, t in enumerate(m['items']))
        flag = ' ⚠️待确认' if m.get('status') == '待确认' else ''
        out.append(f'| {name}{flag} | {m["version"]} | {items} | 本事项各项工作，{fmt_h(m["minutes"])}。 | 〔待填〕 | 〔无/待填〕 | 〔待填〕 |')
    out.append('\n### 二、其他事项\n')
    if others:
        out.append('| 事项名称 | 具体工作内容 | 人员与实际工时 | 本周进展 | 风险提示 | 下周计划 |')
        out.append('|---|---|---|---|---|---|')
        for name, m in others.items():
            items = ' '.join(f'{i+1}. {t}' for i, t in enumerate(m['items']))
            out.append(f'| {name} | {items} | 本事项工作，{fmt_h(m["minutes"])}。 | 〔待填〕 | 无。 | 〔—/待填〕 |')
    else:
        out.append('无')
    if unmapped:
        out.append('\n### ⚠️ 待映射记录（需补充 matters.json）\n')
        out.append('| 泛称记录 | 工作内容 | 工时 |')
        out.append('|---|---|---|')
        for name, m in unmapped.items():
            items = '；'.join(m['items'])
            out.append(f'| {name} | {items} | {fmt_h(m["minutes"])} |')
    if excluded:
        out.append('\n---')
        for name, (mins, reason) in excluded.items():
            out.append(f'\n*未计入：{name} {fmt_h(mins)}（{reason}）*')
    out.append(f'\n**合计 {fmt_h(total)}**')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
