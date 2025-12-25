## Elyra (v2 direction: Braid)

Elyra is being redesigned around a **Braid** architecture: an append-only stream of **deltas** with periodic immutable checkpoints (**knots**) and overlapping narrative/topic groupings (**episodes**).

In v2, Elyra becomes primarily a **composition layer** over two external components:

- **LargeMemoryModel (LMM)**: episodic/semantic/procedural memory, beads, consolidation, retrieval/ribbon building
- **LargeCognitiveModel (LCM)**: knot processing (think/speak), microagents, tests, fork detection

### Documentation

- Canonical docs (Braid v2): `docs/v2/README.md`
- External discussion imports (inputs): `docs/discussions/README.md`
- Legacy v1-era docs (superseded): `docs/legacy/README.md`

### Current repo status

This repository currently contains a Phase 1 MVP implementation (FastAPI + WebSocket chat + UI) plus design docs.

The v2 Braid architecture is a **docs-first redesign** and will be implemented via a strip-out-and-rebuild process.


