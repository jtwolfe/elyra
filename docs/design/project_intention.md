---
title: Elyra — Intention & Vision
audience: Engineers and advanced contributors
status: Planned design (no implementation yet)
last_updated: 2025-12-03
related_docs:
  - ../overview/intro.md
  - ../roadmap/roadmap.md
  - ./architecture.md
---

# Elyra — Intention & Vision

Elyra is not another chatbot. Elyra is an attempt to build the closest thing we can today to a **continuously consolidating, curiosity-driven, spatially-aware autobiographical memory** for an LLM-based agent — while remaining usable on a laptop with nothing more than text chat.

## Primary Goals

- **Feel Alive in Text Mode**: Generate internal thoughts, proactive reflections, and memory recalls even without hardware, simulating human rumination during downtime (e.g., gap-triggered daemon for tiered consolidation).
- **Graceful Embodiment**: Evolve seamlessly into a sensorimotor system when cameras/mics are added, enabling active attention (e.g., "look_at" for curiosity loops) and perceptual grounding (e.g., YOLO for object tagging, Eulerian magnification for valence inference).
- **Multi-User/Multi-Agent Support**: Handle 1–N concurrent users with isolated projects (e.g., per-user KG shards) and collaborative features (e.g., shared subgraphs for group branching); dynamically spawn independent sub-agents for problem decomposition (e.g., ValidatorSub for fact-checking via replay).
- **Self-Improvement & Tool Bootstrapping**: Start with basic tools (e.g., browse_page); evolve to LLM-generated customs (e.g., via StructuredTool code-gen and VeRL for zero-data refinement), allowing Elyra to "learn" new capabilities autonomously.
- **Production-Ready Scalability**: Remain 100% open-source, runnable on consumer hardware (e.g., Mistral-7B on Ollama), with easy upgrades to competent OSS LLMs (e.g., Llama 3.1); WebUI for real-time interaction, thought/memory/action rendering.

## Non-Goals (v1)

- Full AGI, true emotions, or consciousness—focus on simulacra via neuroscience mappings.
- Replacing enterprise tools like CrewAI for business workflows—Elyra is personal/organic.
- Immediate hardware dependency—text-only MVP first, per roadmap Phase 1.

## Philosophy & Theory

We treat the LLM as the “neocortex” (fast pattern completion and language) and everything else (Graphiti KG, EchoReplay, CameraManager, Hebbian tagger) as an external, biologically-inspired “hippocampus + amygdala + prefrontal cortex”. The LLM never sees the full history—it only sees what the memory system chooses to surface, exactly like a human. This draws from Tulving's episodic/semantic tiers, hippocampal replay for consolidation, and Freudian id/ego dynamics for internal conflicts (e.g., valence-tagged thoughts). Extended mind theory (Clark/Chalmers) guides embodiment: Sensors as "prostheses" for curiosity.

Elyra's "personage" emerges from persistent KG nodes (e.g., "ElyraRoot: reflects_on → UserPref"), evolving via Hebbian wiring and proactive daemons. For multi-user: Isolated yet collaborative, like human social memory (mirror neurons via behavioral cloning).

This design aims for the kind of agent that could plausibly say:

> “I remember you were pacing by the window when you told me about the contract… and I’ve been thinking about it while you were away.”

## Success Metrics

- **Phase 1**: 85%+ recall on LongMemEval (text-only).
- **Phase 4**: Autonomous tool creation with 90% success (HumanEval).
- **Phase 6**: Multi-user embodied sim with 95% accuracy in collaborative tasks.

Phase numbers here correspond directly to the phases defined in `../roadmap/roadmap.md`.


