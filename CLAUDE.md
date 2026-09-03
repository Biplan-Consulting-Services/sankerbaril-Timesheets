# Timesheets

## What this is
The central log of billable/work hours across every client project in this workspace.
Not scoped to one client - see the `Clients/<Client>/<PROJECT-CODE>/` repos for the
actual project work; this repo only tracks *when* time was spent and on *what*, so
hours never have to be reconstructed from memory or commit-archaeology after the fact.

## Why it's separate from each project's own repo
Work happens across multiple clients/projects, sometimes in parallel (a background
agent grinding on one feature while the foreground conversation moves to another, or
literally two different clients' work interleaved in one day). A shared file can't
represent that without collisions, so each project gets its own independent CSV - see
the `timesheet-logging` skill (`~/.claude/skills/timesheet-logging/SKILL.md`) for the
full logging procedure.

## Files
- `_projects.csv` - the project registry: `file,client,project,billable,color_light,color_dark`.
  A project only exists to the skill/console because it has a row here. `client` is
  the actual client name (`Internal` for non-billable buckets) - the console's client
  filter drills down from this into individual projects. `billable` is `true`/`false`;
  non-billable rows leave the color columns blank and render neutral, outside the
  categorical color system on purpose.
- One CSV per project, named after its repo (`pioneer-transformer-frm10-12.csv`,
  `pioneer-transformer-frm09.csv`, `pioneer-transformer-workflow-automation.csv`), plus
  `_internal.csv` for non-billable/meta work (tooling, this workspace itself, etc.).
- `_session-log.md` - coarse session-open/session-close timestamps, written
  automatically by a SessionStart/SessionEnd hook (see `~/.claude/settings.json`).
  A backstop for reconstructing a day's envelope if a workstream row was missed, and
  the source of truth for which sessions have confirmed-ended (used by the stale-row
  detection below) - don't treat it as billable data on its own.

## Row schema (per-project CSVs)
`id,date,start,end,status,session_id,workstream` - quote `workstream` if it contains
a comma.
- `id` - sequential per file, e.g. `WS-014`. Multiple rows can be `in-progress` at
  once in the same file - always reference by id, never assume "the" open row.
- `status` - `in-progress` or `done`.
- `session_id` - the Claude Code session that opened the row; blank for
  historical/reconstructed rows. Lets a later session tell "still open in a
  currently-running sibling session" apart from "genuinely orphaned" - see the
  `timesheet-logging` skill's "Automatic stale-row and idle detection" section.
- `workstream` - short description; edited in place if scope shifts but it's still
  the same unit of work, or closed + a new row opened if the user pivots to something
  genuinely different.

## Reporting - the Shift Console
On request (or automatically at end-of-day, per the skill), the console's data gets
refreshed and republished to the URL below. It opens to today's entries, with a "This
Week" view and a "Search a range" view; a two-level Clients → Projects filter (each
level with its own select-all/none); and a Timeline/Table display toggle - Table is a
plain HTML table meant for copy-pasting rows directly into an external timesheet app.
All data is embedded at publish time - it's a snapshot, not a live feed.

**Source file: `shift-console.html`** (this repo, tracked in git). This is the actual
page - its own considered design (serif ledger aesthetic, horizontal time-of-day
timeline bars, stacked hours-by-project split bar), built once and refined since.
**Regenerating means editing this file's embedded `DATA` object only** (add/update rows
in `DATA.rows`, add project entries to `DATA.projects` if a new project was
scaffolded) **and republishing it as-is - never rebuild the page from scratch** from
this doc's description or the skill's behavioral notes. The design already exists;
treat it the same as any other piece of source code in this repo - read it, patch it,
don't rewrite it. If this file and the live published artifact ever disagree (e.g. this
file wasn't updated after some past redeploy), the file is authoritative - overwrite
the live artifact from it, not the other way around.

**Hours are a union, not a sum.** Parallel sessions are normal here, so rows in the
same file routinely overlap in time. Every total the console shows - the Total hours
tile, Avg / active day, and each day header in both views - merges overlapping spans
rather than adding them, because that time was only worked once. Row-level hours in
Table view stay each row's own span, since that view is meant for pasting into an
external timesheet app. Anything computing hours outside the console (an ad-hoc
range breakdown, an invoice figure) has to do the same merge, or it will overcount -
2026-09-01's rows sum to 13.1h against 9.9h actually worked.

**Current artifact URL:** https://claude.ai/code/artifact/41688985-c12f-4f44-a4fe-c4c9d4a83123
