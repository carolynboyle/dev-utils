# Roadmap: dev-utils Docker Container

## The Idea

Package all dev-utils tools into a single Docker image so the end-user
path is:

```bash
git clone https://github.com/carolynboyle/dev-utils
cd dev-utils
docker compose up -d
docker compose run --rm tools treekit <infile> <dest>
```

No venv, no setupkit, no pip, no activation step.

---

## Current Path (for comparison)

1. `git clone dev-utils`
2. Understand setupkit
3. `setupkit init treekit`
4. Activate venv
5. `treekit <infile> <dest>`

The container path removes steps 2–4 entirely.

---

## Design

A single `tools` service in a `docker-compose.yml` at the repo root.
All dev-utils packages installed into the image at build time.
Run any tool on demand:

```bash
docker compose run --rm tools treekit <infile> <dest>
docker compose run --rm tools sniffkit <dir>
docker compose run --rm tools viewkit <file>
```

Shell aliases can reduce this further:

```bash
alias treekit='docker compose run --rm tools treekit'
```

Then: `treekit <infile> <dest>` — identical to the venv experience.

---

## Relationship to setupkit

setupkit, fletcher, and the doc-gen pipeline remain developer machine
tools — they manage the dev-utils repo itself and are not end-user
facing. They are not included in the container image.

The setupkit registry yaml files become internal artifacts — used
during development, not needed by end users.

---

## Implementation Notes

- Base image: `python:3.12-slim`
- Install packages via pip from local source (`COPY . /src` +
  `pip install /src/python/treekit` etc.) rather than from GitHub,
  since the user already has the repo cloned
- Tag releases before building — container image version should match
  dev-utils release version
- Publish to GitHub Container Registry (ghcr.io) once stable so
  `git clone` is optional for end users who just want the tools

---

## Dev.to Post Angle

"From venv hell to one command" — before/after story showing the
reduction in friction for a new user. Practical, relatable, real tools.

Fits alongside the designing-gemma post as a separate "reduce friction"
theme targeting a different audience (tool users vs. LLM experimenters).
