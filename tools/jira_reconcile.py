"""Reconcile the Pioneer timesheet CSVs with a Jira AFDS pull and write a push plan.

READ-ONLY toward Jira: this only reads local files. Nothing is sent anywhere.

    python tools/jira_reconcile.py                 # latest jira/pulls/*.json
    python tools/jira_reconcile.py --pull jira/pulls/2026-09-29.json

Writes jira/plans/<pull-date>.json (the rows jira_push.js would send) and
jira/plans/<pull-date>.md (the report to review). See jira/README.md for the cycle.

Rules:
- Only Pioneer Transformer rows (client in _projects.csv), status done, dated after
  config.json coveredThrough (the catch-up period is already in Jira).
- A row whose marker "[WS-xxx <csv-stem>]" is already in the pull is skipped (already pushed).
- Hours are a union: on one day, a row that starts inside an earlier row is trimmed to
  begin where that row ends, and dropped if it is fully inside it. The row that keeps the
  time is the one that started first.
- Ticket: jira/overrides.csv (file,id,ticket) > the task the row names ("PT-109: ..." at the
  start of the workstream; the Pioneer task file's `jira` field, first named task that has one)
  > ticket-map.csv project line (rows of the FRM buckets) > ticket-map.csv epic line
  (Workflow-Automation rows by their epic column).
  A row with no ticket is listed as BLOCKED and left out of the plan.
"""
import argparse
import csv
import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path

TS = Path(__file__).resolve().parent.parent
JIRA = TS / "jira"
PIONEER_TASKS = TS.parent / "Clients" / "Pioneer Transformer" / "projects" / "workflow-automation" / "tasks"
COMMENT_MAX = 280


def task_tickets():
    """{PT-###: AFDS-###} from the Pioneer task files' front matter (only tasks with a jira value)."""
    out = {}
    for p in PIONEER_TASKS.glob("PT-*.md") if PIONEER_TASKS.is_dir() else []:
        head = p.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n---\n", 1)[0]
        m = re.search(r"^jira:\s*(AFDS-\d+)\s*$", head, re.M)
        if m:
            out[p.stem] = m.group(1)
    return out


def named_ticket(workstream, tickets):
    """The ticket of the first task named at the start of a workstream ("PT-013, PT-040: ...")."""
    lead = workstream.split(":", 1)[0] if ":" in workstream[:40] else ""
    for pt in re.findall(r"PT-\d{3,}", lead):
        if pt in tickets:
            return tickets[pt]
    return None


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def edt_offset(day):
    """-0400 between the second Sunday of March and the first Sunday of November, else -0500."""
    def nth_sunday(month, n):
        d = dt.date(day.year, month, 1)
        d += dt.timedelta(days=(6 - d.weekday()) % 7)
        return d + dt.timedelta(weeks=n - 1)
    return "-0400" if nth_sunday(3, 2) <= day < nth_sunday(11, 1) else "-0500"


def minutes(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[3:5])


def load_rows(projects, epic_keys):
    """Same parsing as build_console_data.js: workstream runs to the end of the line, except
    a trailing field that is empty or a real epic key (old rows have unquoted commas)."""
    rows = []
    for p in projects:
        stem = Path(p["file"]).stem
        lines = read_csv(TS / p["file"])
        has_epic = bool(lines) and lines[0][-1:] == ["epic"]
        for f in lines[1:]:
            if len(f) < 7 or not f[0].startswith("WS-"):
                continue
            rest, epic = f[6:], ""
            if has_epic and len(rest) > 1 and (rest[-1] == "" or rest[-1] in epic_keys):
                epic = rest.pop()
            rows.append({"file": p["file"], "stem": stem, "project": p["project"], "id": f[0],
                         "date": f[1], "start": f[2], "end": f[3], "status": f[4],
                         "workstream": ",".join(rest).strip(), "epic": epic})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", help="pull snapshot (default: newest in jira/pulls)")
    a = ap.parse_args()

    cfg = json.loads((JIRA / "config.json").read_text(encoding="utf-8"))
    pull_path = Path(a.pull) if a.pull else sorted((JIRA / "pulls").glob("*.json"))[-1]
    pull = json.loads(pull_path.read_text(encoding="utf-8"))
    pushed = {m.split("@")[0] for m in pull.get("markers", [])}
    covered = cfg["coveredThrough"]

    projects = [p for p in csv.DictReader(open(TS / "_projects.csv", encoding="utf-8-sig"))
                if p["client"] == cfg["client"]]
    epic_keys = {e["key"] for e in csv.DictReader(open(TS / "_epics.csv", encoding="utf-8-sig"))}
    tmap = {(m["scope"], m["key"]): m["ticket"].strip()
            for m in csv.DictReader(open(JIRA / "ticket-map.csv", encoding="utf-8-sig"))}
    overrides = {}
    if (JIRA / "overrides.csv").exists():
        overrides = {(o["file"], o["id"]): o["ticket"].strip()
                     for o in csv.DictReader(open(JIRA / "overrides.csv", encoding="utf-8-sig"))}

    rows = load_rows(projects, epic_keys)
    tickets = task_tickets()
    skipped, blocked, plan = defaultdict(list), [], []

    # Union per day across all Pioneer files: first-started row keeps overlapping time.
    by_day = defaultdict(list)
    for r in rows:
        if r["date"] <= covered:
            skipped["in the catch-up period (<= %s)" % covered].append(r)
        elif r["status"] != "done" or not r["end"]:
            skipped["still open"].append(r)
        elif f"{r['id']} {r['stem']}" in pushed:
            skipped["already in Jira (marker found)"].append(r)
        else:
            by_day[r["date"]].append(r)

    for day in sorted(by_day):
        reach = -1
        for r in sorted(by_day[day], key=lambda r: (minutes(r["start"]), -minutes(r["end"]))):
            s, e = minutes(r["start"]), minutes(r["end"])
            if e <= s:
                skipped["zero or negative span"].append(r)
                continue
            if e <= reach:
                skipped["inside another row's span (union rule)"].append(r)
                continue
            s2 = max(s, reach)
            reach = max(reach, e)
            ticket = (overrides.get((r["file"], r["id"]))
                      or named_ticket(r["workstream"], tickets)
                      or (tmap.get(("project", r["project"])) if r["project"] != "Workflow-Automation" else None)
                      or tmap.get(("epic", r["epic"])))
            r = dict(r, pushStart="%02d:%02d" % divmod(s2, 60), seconds=(e - s2) * 60, ticket=ticket or "")
            if not ticket:
                blocked.append(r)
                continue
            marker = f"[{r['id']} {r['stem']}]"
            text = r["workstream"]
            if len(text) > COMMENT_MAX:
                text = text[:COMMENT_MAX - 3].rstrip() + "..."
            plan.append({"marker": marker, "ticket": ticket, "date": day,
                         "started": f"{day}T{r['pushStart']}:00.000{edt_offset(dt.date.fromisoformat(day))}",
                         "timeSpentSeconds": r["seconds"], "comment": f"{marker} {text}",
                         "trimmed": r["pushStart"] != r["start"]})

    # Weekly totals: what Jira already has + what the plan adds, against the cap.
    week = lambda d: dt.date.fromisoformat(d) - dt.timedelta(days=dt.date.fromisoformat(d).weekday())
    wk = defaultdict(lambda: [0.0, 0.0])
    for d, h in pull.get("days", {}).items():
        wk[week(d)][0] += h
    for p in plan:
        wk[week(p["date"])][1] += p["timeSpentSeconds"] / 3600

    out = JIRA / "plans"
    out.mkdir(exist_ok=True)
    stamp = pull_path.stem
    (out / f"{stamp}.json").write_text(json.dumps({
        "generatedAt": dt.datetime.now().isoformat(timespec="seconds"), "pull": pull_path.name,
        "coveredThrough": covered, "entries": plan}, ensure_ascii=False, indent=1), encoding="utf-8")

    L = [f"# Jira push plan - pull {stamp}", "",
         f"Pull: `{pull_path.name}` ({pull.get('worklogs', '?')} worklogs of mine, {pull.get('first')} -> {pull.get('last')}, "
         f"{len(pushed)} [WS] markers). Catch-up covered through **{covered}**. Nothing has been sent.", "",
         f"## To push: {len(plan)} worklogs, {sum(p['timeSpentSeconds'] for p in plan) / 3600:.2f} h", "",
         "| marker | ticket | started | hours | note |", "|---|---|---|---:|---|"]
    for p in plan:
        L.append(f"| {p['marker']} | {p['ticket']} | {p['started'][:16].replace('T', ' ')} | "
                 f"{p['timeSpentSeconds'] / 3600:.2f} | {'trimmed (overlap)' if p['trimmed'] else ''} |")
    L += ["", f"## Blocked - no ticket: {len(blocked)} rows, {sum(r['seconds'] for r in blocked) / 3600:.2f} h", ""]
    if blocked:
        L += ["Fix: fill the epic's ticket in `jira/ticket-map.csv` or add a line to `jira/overrides.csv`.", "",
              "| row | date | hours | epic | workstream |", "|---|---|---:|---|---|"]
        L += [f"| {r['id']} {r['stem']} | {r['date']} | {r['seconds'] / 3600:.2f} | {r['epic'] or '(none)'} | "
              f"{r['workstream'][:90].replace('|', '/')} |" for r in blocked]
    L += ["", "## Weeks (Monday)", "", f"| week | in Jira | plan adds | total | cap {cfg['weeklyCapHours']} h |",
          "|---|---:|---:|---:|---|"]
    for w, (j, add) in sorted(wk.items()):
        if add or w >= week(covered):
            flag = "OVER" if j + add > cfg["weeklyCapHours"] + 1e-9 else ""
            L.append(f"| {w} | {j:.2f} | {add:.2f} | {j + add:.2f} | {flag} |")
    L += ["", "## Skipped", ""]
    for why, rs in skipped.items():
        after = [r for r in rs if r["date"] > covered]
        L.append(f"- {why}: {len(rs)} rows" + (": " + ", ".join(f"{r['id']} {r['stem']}" for r in after) if after else ""))
    (out / f"{stamp}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
