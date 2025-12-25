## Elyra Development Setup (Bluefin + venv)

This document describes how to set up a local development environment for Elyra on **Fedora Bluefin** (or other Linux distros) using a **Python virtual environment**.

### Note on v2 (Braid) direction

Elyra is being redesigned around a **Braid** architecture (see `docs/v2/README.md`).

The long-term v2 direction composes two external repositories:
- `LargeMemoryModel` (LMM)
- `LargeCognitiveModel` (LCM)

Submodules cannot be pinned until those repositories have at least one commit; see `submodules/README.md` for the current status and commands.

### 1. Prerequisites

- Python 3.14 (or your system default Python 3.x)
- `git`
- `podman` or `docker` (recommended for Redis/Neo4j/Qdrant)
- Node.js 20+ and `npm` (for the React/Tailwind UI)

On Bluefin, prefer installing tools via **toolbx** or user-level packages, not system-wide RPMs on the immutable base image.

### 2. Create and activate the Python virtual environment

From the project root:

```bash
cd /var/home/jim/workspace/elyra
python3 -m venv .venv
source .venv/bin/activate
```

Your shell prompt should now indicate that `.venv` is active. All Python dependencies are installed into this directory, leaving the system Python untouched.

To deactivate:

```bash
deactivate
```

### 3. Install Python dependencies

With the venv active:

```bash
pip install --upgrade pip
git submodule update --init --recursive
pip install -r requirements.txt
```

This installs:

- FastAPI + Uvicorn (API gateway)
- LangGraph + LangChain Core (orchestration and message types)
- HTTPX, Pydantic, APScheduler (infra)
- Redis / Neo4j / Qdrant clients (for future HippocampalSim backends)
- Pytest (tests)
- **LMM/LCM editable installs** from `submodules/` (Braid v2 skeleton)

### 4. Containers for Redis / Neo4j / Qdrant (optional in early development)

For the initial MVP, `HippocampalSim` ships with **in-memory stubs**, so you do **not** need Redis/Neo4j/Qdrant to start coding.

When you are ready to integrate real backends, use `podman` or `docker` from your user space (or a `toolbox`) to run them via the provided `docker-compose.yml`:

```bash
podman-compose up -d        # or: docker compose up -d
```

All data will live under your home directory; the Bluefin base image remains unchanged.

### 5. Running backend and UI (conceptual)

Once dependencies are installed and the code is in place, the typical dev workflow will be:

```bash
# Backend (inside venv)
uvicorn elyra_backend.core.app:app --reload

# Frontend (from ./ui)
npm install
npm run dev
```

The backend exposes a WebSocket endpoint at `/chat/{user_id}/{project_id}`; the React/Tailwind UI connects to it and renders chat plus internal “thoughts”.

See `RUNNING_LOCALLY.md` (to be added alongside this file) for concrete run instructions once the MVP is fully wired up.


