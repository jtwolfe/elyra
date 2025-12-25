---
title: Embodiment – Sensors, Vision, and Audio
audience: Engineers and researchers
status: Planned design (no implementation yet)
last_updated: 2025-12-03
related_docs:
  - ../design/architecture.md
  - ./memory-architecture.md
---
> **Legacy (superseded)**: This document is preserved for reference only. The canonical Braid v2 docs live in `docs/v2/`.



## Goals

Embodiment extends Elyra from pure text into **sensorimotor** contexts:

- cameras (RGB video),
- microphones (audio),
- and optionally simulated robots or environments.

The design aims for **graceful embodiment**:

- text-only systems remain functional,
- sensors can be added later without major architecture changes.

## CameraManager

The `CameraManager` module coordinates:

- multiple camera sources (e.g., office cams, user webcam),
- active attention (deciding which camera to “look at”),
- and pre-processing for memory and valence.

Responsibilities:

- maintain a registry of cameras with metadata (location, purpose),
- expose actions like:
  - `look_at(camera_id)` – focus on a specific camera,
  - `look_around()` – scan a set of cameras for interesting events,
- stream frames to processing pipelines:
  - object detection (YOLO-style),
  - motion and micro-expression analysis (Eulerian magnification or similar),
  - scene summarisation.

## Vision Pipeline

High-level flow:

1. **Capture**
   - Pull frames from `CameraManager` at a configurable rate.

2. **Detection & Tagging**
   - Apply an object detector (e.g., YOLO-family model) to obtain:
     - bounding boxes,
     - class labels,
     - confidence scores.

3. **Motion & Valence**
   - Use motion analysis or magnification techniques to infer:
     - intensity of movement,
     - possible emotional cues (very approximate),
     - interesting events (e.g., someone entering the frame).

4. **Episodic Encoding**
   - Convert raw detections into:
     - KG nodes/edges (entities, relations, time),
     - vector embeddings (e.g., CLIP-style).
   - Store them in HippocampalSim’s episodic buffer and long-term stores.

## Audio & Speech

- **Whisper-style STT**
  - Convert audio segments into text, with timestamps and speaker labels where possible.
  - Feed transcripts as episodes into memory, potentially linked to video frames by time.

- **Prosody Analysis**
  - Extract basic prosodic features:
    - pitch, volume, tempo,
    - abrupt changes.
  - Map to coarse valence/arousal tags and store alongside episodes.

## Multimodal Fusion

Fusion happens primarily in the memory layer:

- episodes can contain:
  - text (dialogue or transcripts),
  - image/frame references,
  - audio/prosody summaries,
  - tool outputs.

Correlation mechanisms:

- temporal alignment (timestamps),
- shared entities in the KG (e.g., “User A”, “whiteboard”),
- shared embeddings in the vector store.

This enables queries like:

- “What did we discuss last time we were at the whiteboard in the office?”
- “Show me the last meeting where people looked confused.”

## Multi-Agent and Embodiment

- Sub-agents can specialise on different modalities:
  - a “Perception” agent focusing on sensor data,
  - a “Diary” agent summarising days into visual/textual highlights.

- The root agent:
  - decides when to ask for visual/audio context,
  - integrates multimodal summaries into its responses,
  - and decides when to surface or hide raw sensor details from users.

Embodiment is optional; all of the above should be disabled or stubbed when running Elyra in text-only mode.



