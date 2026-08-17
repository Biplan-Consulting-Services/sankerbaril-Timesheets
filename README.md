# Shift Console

A time-tracking system for consulting work spanning multiple clients and projects,
built to remove manual timesheet upkeep entirely: hours are captured automatically as
work happens, structured so parallel client work never collides, and surfaced through
an interactive reporting console designed to feed directly into an external timesheet
tool.

## Why it exists

Consulting work here runs across several independent client projects, sometimes
concurrently — a long-running task on one project while attention shifts to another,
or genuinely separate clients' work interleaved within the same day. Reconstructing
accurate hours after the fact from memory or commit history is slow and error-prone.
Shift Console instead treats time-logging as a first-class, automatic part of the
workflow, and gives that data a purpose-built interface for review and export.

## Features

**Automatic, structured logging**
Every distinct unit of work is logged with real start/end timestamps as it happens —
no manual timer, no end-of-day reconstruction. A lightweight session-boundary hook
also stamps session open/close times automatically, as a safety net for anything
missed mid-session.

**Collision-free parallel tracking**
Each project keeps its own independent log. Two clients' work — or two workstreams
within the same client — can be open at the same time without one overwriting the
other, a deliberate design choice to support working across multiple engagements
concurrently.

**A live project registry**
Clients and projects aren't hardcoded anywhere. A single registry file defines what
projects exist, which client they belong to, whether they're billable, and their
display color — adding a new client or project is a one-line change that the entire
system picks up automatically.

**An interactive reporting console**
Rather than a static report, hours are reviewed through a small interactive
application:
- **Today / This Week / Custom range** views, switchable instantly.
- **Client → Project drill-down filters** — pick which clients to look at, then
  narrow to specific projects within them — scoped automatically to whatever
  actually has entries in the selected date range, so the filter list never grows
  unwieldy as more clients and projects accumulate over time.
- **Timeline view** — a visual shift log per day, with real proportional start/end
  bars, a distinct look for work still in progress, and automatic flagging of any
  entry left open past its own day.
- **Table view** — the same data as a clean, plain data table (date, client,
  project, times, hours, status, description), built specifically to be selected
  and pasted straight into an external timesheet system.
- **At-a-glance summary metrics** — total hours, active days, and an hours-by-project
  breakdown for whatever is currently in view.
- Full light/dark theme support, and a colorblind-safe, validated color palette
  identifying each client project consistently throughout.

**Durable, auditable history**
All data lives in version-controlled, plain-text files — nothing proprietary, nothing
that requires this tool specifically to read. Every change has full git history.

## How it works

```
_projects.csv              registry: every client + project, billing status, color
<project>.csv              one append-only log per project (id, date, start, end,
                            status, description)
_internal.csv               non-billable/internal work, tracked the same way
_session-log.md              automatic session-boundary backstop
```

The Shift Console itself is a self-contained interactive page: all data is compiled
into it at publish time, so it opens instantly with no backend or live connection,
and is refreshed on request or automatically at the end of a work day.

## Screenshots

_Screenshots to be added — see the placeholders below._

**Today view**
_(placeholder — timeline view showing a single day's logged work)_

**This Week view with client/project filters**
_(placeholder — filters panel expanded, multiple projects visible)_

**Table view**
_(placeholder — plain-table display, ready to copy into another timesheet app)_

## Status

Actively used for day-to-day time tracking. Current scope: one client (Pioneer
Transformer, three projects) plus internal/tooling work; the registry-driven design
means additional clients and projects require no structural changes to add.
