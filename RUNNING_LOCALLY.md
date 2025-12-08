## Running Elyra Locally (Phase 1 MVP)

This guide assumes you have followed `DEVELOPMENT.md` to create a Python venv and install dependencies on Fedora Bluefin (or similar Linux).

### 1. Start Ollama (LLM backend)

Elyra expects an Ollama server with a suitable model (as configured in `elyra_backend/config.py`):

```bash
ollama serve
ollama pull mistral:7b-instruct-v0.3-q6_K
```

If your Ollama host or model name differs, set environment variables before starting the backend:

```bash
export ELYRA_OLLAMA_BASE_URL="http://localhost:11434"
export ELYRA_OLLAMA_MODEL="mistral:7b-instruct-v0.3-q6_K"
```

### 2. (Optional) Start Redis / Neo4j / Qdrant

For the Phase 1 MVP, the `HippocampalSim` implementation is purely in-memory and does **not** require these services.

When you want to experiment with real backends, you can start them with:

```bash
podman-compose up -d        # or: docker compose up -d
```

from the project root. Data is stored under `./data/`, keeping the Bluefin base image unchanged.

### 3. Run the backend API

Activate your venv and start Uvicorn:

```bash
cd /var/home/jim/workspace/elyra
source .venv/bin/activate
uvicorn elyra_backend.core.app:app --reload --port 8000
```

The backend exposes:

- `GET /health` – simple health check.
- `WS /chat/{user_id}/{project_id}` – streaming chat endpoint used by the Web UI.

### 4. Run the React/Tailwind Web UI

In a separate shell:

```bash
cd /var/home/jim/workspace/elyra/ui
npm install
npm run dev
```

Then open the printed URL (typically `http://localhost:5173`) in your browser.

The UI connects to `ws://localhost:8000/chat/demo-user/demo-project` and renders:

- a chat panel (user and assistant messages),
- an “Internal thought” side panel showing stubbed thoughts from `HippocampalSim`.

### 5. Running tests

With the venv active:

```bash
cd /var/home/jim/workspace/elyra
pytest
```

This runs the basic unit tests for the backend components.


