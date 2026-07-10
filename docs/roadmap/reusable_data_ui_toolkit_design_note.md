# Design Note: Reusable Data UI Toolkit (seeded from Curator)

**Status:** Idea capture only — not scheduled, not designed in detail.
**Origin:** Arose from extracting `bidirectional-filter.js` out of
`_tab_identities.html` on 2026-06-30, recognizing the pattern as something
that will recur in every future database-backed web UI, not just this one
use in Curator.

---

## The idea

A form is a form. Across any database-backed web UI — Curator or
whatever comes after it — the same handful of interaction patterns show
up repeatedly, just wired to different tables, columns, and colors. Rather
than re-solving "how do I build a detail form / a cross-reference list /
an inline-edit grid" from scratch in every new project, build a small,
generic toolkit of data-UI components, seeded from the pieces already
emerging in Curator, and grow it opportunistically as new patterns prove
themselves.

Loosely inspired by what MS Access got right (drag a table's fields onto
a form, get working CRUD) without trying to recreate Access itself —
Curator's pieces are declarative-config-driven web components, not a
desktop RAD tool.

## Pieces that already exist and qualify

These weren't designed as a toolkit up front — they were each solved once
for a real Curator need, and only afterward recognized as reusable shapes:

- **`forms.yaml` + `formkit.py`** — declarative button/action config.
  Define a button once (label, type, class, tooltip), reference it by
  name from any preset. No hardcoded button markup per form.
- **`datasheet.js` + `_datasheet_with_header.html`** — generic inline-edit
  Tabulator grid. Column definitions and save/add URLs are passed in;
  the dirty-row/save-dialog machinery doesn't know or care what entity
  it's editing.
- **`bidirectional-filter.js`** — generic two-listbox cross-reference
  widget (select in one list, filter the other, shared selection readout,
  dblclick-to-detail, add button). Config-driven: two listbox ids, two
  entity names, one selection-box id. No knowledge of what the two
  entities actually are.

## The bigger version of this idea (not being built now)

The natural extension — explicitly **not** being designed yet — is a
schema-aware form generator: point it at a table's columns, get a
reasonable default form layout with the right widget per column type
(text input for varchar, dropdown for a FK lookup, textarea for text,
date picker for date, etc.), composed out of pieces like the three above
rather than hand-written per-entity Jinja2 branches (which is still how
`_detail_panel.html` works today — an `{% if entity == "..." %}` chain).

This is deliberately deferred. Extracting a generator's assumptions about
"what a form needs" requires having built several real forms by hand
first (Contacts, Tasks, whatever comes next) so the generator is grounded
in patterns actually encountered, not patterns guessed at in advance.
Building the generalized tool before the second or third real form exists
risks the same problem extracting `bidirectional-filter.js` early was
trying to avoid — guessing wrong about what needs to be configurable.

## Where this would eventually live

Not decided. Candidate homes, for whenever this becomes concrete:

- A new package in `dev-utils` (matching `dbkit`/`viewkit`/`menukit`),
  distinct in name from the existing `curator.formkit` (Python,
  button-config-specific) to avoid confusion between "the Python button
  config module in Curator" and "the general JS data-UI library in
  dev-utils."
- JS distribution mechanics aren't solved for dev-utils the way Python
  packaging is (`pip install -e`) — a shared JS library would need either
  a copy step (safer for eventual Docker/Hetzner deployment, where
  symlinking across repos at a fixed relative path is fragile) or actual
  npm packaging (likely overkill for a two-repo homelab setup). Punt
  until there's a second consuming project to design distribution
  against.

## Trigger to revisit

Come back to this once one of the following happens:
- A second Curator entity's detail form (Tasks, or whatever's next after
  Contacts) is built by hand and a third clearly-generalizable pattern
  emerges alongside the three above.
- A second project outside Curator needs any of these pieces, forcing the
  distribution-mechanics question to get a real answer instead of a
  deferred one.
- Curator's own Captain UI reaches a point where hand-writing another
  `{% if entity == ... %}` branch in `_detail_panel.html` feels like the
  wrong move — that's the signal the generator idea has enough grounding
  to sketch for real.
