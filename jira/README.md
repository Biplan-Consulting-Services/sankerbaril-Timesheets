# Jira AFDS worklogs - the biweekly push

Pioneer Transformer hours are billed as worklogs on the Biplan Consulting Jira, project
**AFDS** (`biplan-consulting.atlassian.net`). The timesheet CSVs are the source; Jira gets a
copy about every 2 weeks. **Nothing is ever pushed without the user's OK in chat.**

Access is the user's own Chrome sign-in (claude-in-chrome, cookie auth). No token, and no
token ever goes through chat.

## The cycle

1. **Pull (read-only).** In a biplan-consulting.atlassian.net tab, run `tools/jira_pull.js`
   (set `window.JIRA_SINCE = "YYYY-MM-DD"` first to narrow it). Then read the parts:
   `jiraPart("days")`, `jiraPart("markers")`, `jiraPart("issues", 0|1)`. Save them as
   `jira/pulls/<today>.json` (same shape as `pulls/2026-09-29.json`).
2. **Reconcile (local).** `python tools/jira_reconcile.py` → `jira/plans/<pull>.md` (report)
   and `jira/plans/<pull>.json` (entries). Review the report: blocked rows, trimmed
   overlaps, weeks over the 40 h cap.
3. **Map.** Blocked rows need a ticket. Best: the row names its Pioneer task
   (`"PT-109: ..."`, the timesheet-logging rule since 2026-09-29) and that task has a `jira`
   value (`python tools/work.py set PT-109 jira=AFDS-176` in the Pioneer repo). Otherwise fill
   the epic's line in `ticket-map.csv`, or the row's `ticket` in `overrides.csv` (the
   `suggested` column is only a proposal, it is not used). Order: overrides > the named task's
   jira > project line > epic line. Rerun step 2 until nothing is blocked that should be billed.
4. **Dry run.** In the Jira tab: `window.JIRA_PLAN = <entries>; window.JIRA_APPLY = false;`
   then `tools/jira_push.js`. It re-reads each target issue and reports `would push` /
   `already there` per entry.
5. **Push, on the user's OK only.** Same, with `window.JIRA_APPLY = true`. Each worklog is
   read back. Then pull again (step 1): every pushed row now shows its marker, and the
   next reconcile skips it.

## Why nothing gets pushed twice

- **The client reads these worklogs in its reports.** The comment is only a concise,
  professional French description of the work (`comments.csv` / `fill.csv`): no markers,
  no mention of Claude, agents, breaks or anything internal (user, 2026-10-04).
- Every pushed worklog carries its marker `[WS-xxx <csv-stem>]` (or `[FILL-xxx jira-fill]`)
  in a hidden worklog property `biplan.timesheet`, not in the comment. (Before 2026-10-04
  the plan put it at the start of the comment; nothing was pushed that way.)
  (e.g. `[WS-107 pioneer-transformer-workflow-automation]`).
- The reconcile skips a row whose marker is in the pull.
- The push script checks the marker on the live issue again, right before each POST.
- Rows on or before `config.json` `coveredThrough` (2026-09-18) are never planned. That
  period went in through the September catch-up (`archive/Add-JiraWorklogs.ps1`, 40 h/week
  cap, reconstructed entries, no markers), so its Jira days differ from the timesheet on
  purpose.

## Hours rules

- Union, not sum: when rows overlap on one day, the first-started row keeps the
  overlapping time. A later row is trimmed to start where it ends, or dropped when it is
  fully inside it (e.g. WS-104 inside WS-103 on 09-29).
- Only `done` rows with an end time. Open rows wait for the next cycle.
- The 40 h/week cap is flagged (`OVER`), never cut automatically. The user decides.
- **Minimum entry length: 30 min for work, 15 min for meetings** (user, 2026-10-05). A shorter
  row is merged into a neighbouring entry or rounded up through `fill.csv` (`skip` in
  `overrides.csv`), taking the extra minutes off a fill entry in the same week.
- A billing week runs **Sunday to Saturday**, and weekend work counts toward it (user, 2026-10-04).
- The user works at least 40 h every week, often without Claude, so the logged rows fall short.
  Each cycle, ask what the unlogged days were spent on and add `fill.csv` entries
  (9:00-12:00 and 13:00-18:00, around the logged rows) until every week is exactly 40 h.

## Files

| file | what |
|---|---|
| `config.json` | site, project, client, `coveredThrough`, weekly cap |
| `ticket-map.csv` | epic → ticket and FRM project → ticket (`proposed; confirm` = not confirmed yet) |
| `overrides.csv` | one row → ticket, for rows without an epic or with an exception; `skip` leaves a few-minute row out because its time was merged into a neighbouring `fill.csv` entry |
| `comments.csv` | one row → the worklog text Jira shows (short, French, client-facing) instead of the internal workstream note; runs to the end of the line |
| `fill.csv` | time worked without a timesheet row, agreed with the user to bring a week to the cap (`id,date,start,end,ticket,comment`, marker `[FILL-### jira-fill]`). Jira only: the CSVs keep the real logged times |
| `pulls/<date>.json` | what Jira had on that date (days, markers, issues) |
| `plans/<date>.md/.json` | the reconcile output for that pull |
| `archive/` | the September catch-up tools (one-off, superseded by this cycle) |
