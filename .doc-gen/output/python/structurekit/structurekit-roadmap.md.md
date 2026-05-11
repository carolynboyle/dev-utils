# structurekit-roadmap.md

**Path:** python/structurekit/structurekit-roadmap.md
**Syntax:** markdown
**Generated:** 2026-05-11 15:11:09

```markdown
# structurekit — Roadmap

## What It Is

Filesystem structure documentation agent.

Walks a project's directory tree and compares it against a `PROJECT_STRUCTURE.md`
documentation file. Flags drift in both directions: new filesystem entries not yet
documented, and documented entries that no longer exist on disk. Designed to run on
a cron schedule as a quiet background agent — no interaction required, just a report
when something has changed.

## Durin Observatory Integration

Intended as a component of the Durin Observatory package, which will provide a
read-only filesystem explorer built on doc-gen manifests. structurekit is the
drift-detection layer: Durin sees the tree as it is, structurekit knows what it's
supposed to look like, and the diff between the two is the signal.

## Gemma Lab Integration

Feed the drift report to a local LLM and get a plain-English summary of what changed
and what needs to be documented. Candidate for a standing cron-triggered experiment
in the Gemma Lab webapp.

## Status

Planned. Not yet started. Roadmap captured 2026-05-09.

```
