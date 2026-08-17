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
  A backstop for reconstructing a day's envelope if a workstream row was missed, not
  the primary record - don't treat it as billable data on its own.

## Row schema (per-project CSVs)
`id,date,start,end,status,workstream` - quote `workstream` if it contains a comma.
- `id` - sequential per file, e.g. `WS-014`. Multiple rows can be `in-progress` at
  once in the same file - always reference by id, never assume "the" open row.
- `status` - `in-progress` or `done`.
- `workstream` - short description; edited in place if scope shifts but it's still
  the same unit of work, or closed + a new row opened if the user pivots to something
  genuinely different.

## Reporting - the Shift Console
On request (or automatically at end-of-day, per the skill), an interactive artifact is
built from `_projects.csv` + all project CSVs and republished to the URL below. It
opens to today's entries, with a "This Week" view and a "Search a range" view; a
two-level Clients → Projects filter (each level with its own select-all/none); and a
Timeline/Table display toggle - Table is a plain HTML table meant for copy-pasting rows
directly into an external timesheet app. All data is embedded at publish time - it's a
snapshot, not a live feed.

**Current artifact URL:** https://claude.ai/code/artifact/41688985-c12f-4f44-a4fe-c4c9d4a83123
