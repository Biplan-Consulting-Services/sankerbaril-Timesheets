# Timesheets

## What this is
The central log of billable/work hours across every client project in this workspace.
Not scoped to one client - see [[../Clients/...]] repos for the actual project work;
this repo only tracks *when* time was spent and on *what*, so hours never have to be
reconstructed from memory or commit-archaeology after the fact.

## Why it's separate from each project's own repo
Work happens across multiple clients/projects, sometimes in parallel (a background
agent grinding on one feature while the foreground conversation moves to another, or
literally two different clients' work interleaved in one day). A shared file can't
represent that without collisions, so each project gets its own independent table -
see `timesheet-logging` skill (`~/.claude/skills/timesheet-logging/SKILL.md`) for the
full logging procedure.

## Files
- `pioneer-transformer-frm10-12.md`, `pioneer-transformer-frm09.md`,
  `pioneer-transformer-workflow-automation.md` - one table per project repo.
- `_internal.md` - non-billable/meta work (tooling, this workspace itself, etc.).
- `_session-log.md` - coarse session-open/session-close timestamps, written
  automatically by a SessionStart/SessionEnd hook (see `~/.claude/settings.json`).
  This is a backstop for reconstructing a day's envelope if a workstream row was
  missed, not the primary record - don't treat it as billable data on its own.

## Row schema (per-project files)
`| ID | Date | Start | End | Status | Workstream |`
- `ID` - sequential per file, e.g. `WS-014`. Multiple rows can be `in-progress` at
  once in the same file - always reference by ID, never assume "the" open row.
- `Status` - `in-progress` or `done`.
- `Workstream` - short description; edited in place if scope shifts but it's still
  the same unit of work, or closed + a new row opened if the user pivots to something
  genuinely different.

## Reporting
On request (or automatically at end-of-day, per the skill), a weekly/rolling time-log
artifact is built from these files and republished to the URL recorded below.

**Current artifact URL:** _(not yet published from this repo's data - update here once
the first report is generated)_
