---
title: Contributing to Elyra Documentation
audience: Contributors and maintainers
status: Active
last_updated: 2025-12-03
related_docs:
  - ../README.md
---

### Purpose

This document explains how to **extend and maintain** Elyra’s documentation so that it stays coherent, accurate, and useful as the project evolves.

### Folder layout (docs/)

- `README.md` – Entry point and navigation for the documentation set.
- `overview/` – High-level overview and conceptual quickstart.
- `design/` – Core design specs (intention, architecture, theory of mind, modules).
- `roadmap/` – Roadmap and milestone planning.
- `tech/` – Deep dives into subsystems (memory, orchestration, tools, embodiment, evaluation).
- `reference/` – Glossary and API reference.
- `meta/` – Docs about docs (this file, future style guides, etc.).

### Style guidelines

- **Audience first**  
  Assume readers are technically literate (engineers/researchers) but not necessarily familiar with every library or paper you reference. Prefer short, precise explanations over jargon.

- **Front-matter**  
  All new docs should start with a YAML front-matter block including at least:
  - `title`
  - `audience`
  - `status` (e.g., “Planned design”, “In progress”, “Implemented”, “Deprecated”)
  - `last_updated` (YYYY-MM-DD)
  - `related_docs` (relative paths)

- **Headings**  
  Use `##` and `###` headings (avoid top-level `#` for new sections inside existing docs unless it’s the page title).

- **Code blocks**  
  - Use fenced code blocks with language tags for examples (e.g., ` ```python `, ` ```bash `).
  - Clearly label **pseudocode** or conceptual examples so readers don’t assume they run as-is.

- **Planned vs implemented**  
  Be explicit about what exists today versus what is planned:
  - Mention status in front-matter.
  - Use short callouts like “**Note: design only, not implemented yet.**”.

### Making changes

1. **Small fixes (typos, minor clarifications)**  
   - Make the edit.
   - Add a brief note in the PR description, e.g., “Fix typo in `design/architecture.md`.”

2. **Substantial content changes (new sections, new files)**  
   - Update front-matter (status, last_updated).
   - Ensure related docs are linked (e.g., from `overview/intro.md` or `README.md`).
   - If you introduce new terminology, add it to `reference/glossary.md`.

3. **New technical deep dives**  
   - Place them under `tech/`.
   - Start with context: what problem the subsystem solves and how it fits into the overall architecture.
   - Include diagrams or sequence flows when appropriate (PlantUML or textual).

### Review expectations

- Prefer **smaller, focused PRs** over large, multi-topic changes.
- For complex changes (new modules, architecture shifts), reference design discussions or issues in the PR description.
- Ask a maintainer to review major conceptual changes (e.g., altering the roadmap, changing key architecture assumptions).

### When in doubt

If you’re unsure where something belongs:

- Start a draft in `meta/` or `tech/` with a short **“Open Questions”** section.
- Tag a maintainer or open an issue proposing the structure you have in mind.


