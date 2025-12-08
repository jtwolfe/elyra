"""Daemon and background job stubs (gap detection, replay, etc.)."""

from __future__ import annotations

import asyncio
from typing import Iterable, List, Set, Tuple

from langchain_core.messages import AIMessage

from elyra_backend.config import settings
from elyra_backend.logging import get_logger
from elyra_backend.memory.hippocampal_sim.stub import HippocampalSim


logger = get_logger(__name__)

# Very small in-memory registry of active (user_id, project_id) pairs.
_active_sessions: Set[Tuple[str, str]] = set()


def register_session(user_id: str, project_id: str) -> None:
    """Register an active session for potential background replay."""
    _active_sessions.add((user_id, project_id))


def _get_active_sessions() -> Iterable[Tuple[str, str]]:
    # Return a snapshot to avoid iteration over a mutating set.
    return list(_active_sessions)


async def _daemon_loop(hippo: HippocampalSim, interval_seconds: int = 300) -> None:
    """
    Minimal background loop that periodically generates internal thoughts.

    For each known (user_id, project_id) pair, the loop:
    - calls `hippo.generate_thought(...)`,
    - wraps it in an AIMessage,
    - and ingests it as an internal episode.
    """
    logger.info("Daemon loop started (interval=%s seconds).", interval_seconds)
    while True:
        await asyncio.sleep(interval_seconds)
        if not settings.ENABLE_REPLAY:
            continue

        sessions: List[Tuple[str, str]] = list(_get_active_sessions())
        for user_id, project_id in sessions:
            try:
                thought = await hippo.generate_thought(user_id, project_id)
                internal_msg = AIMessage(content=f"[daemon] {thought}")
                await hippo.ingest(internal_msg, user_id, project_id, thought)
                logger.info(
                    "Daemon generated thought for user_id=%s project_id=%s",
                    user_id,
                    project_id,
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception(
                    "Error during daemon replay for user_id=%s project_id=%s: %s",
                    user_id,
                    project_id,
                    exc,
                )


def start_daemon_loop(hippo: HippocampalSim, interval_seconds: int = 300) -> None:
    """
    Start the daemon loop in the background.

    This should be called from within the FastAPI startup event, so that it
    runs on the same event loop as the application.
    """
    asyncio.create_task(_daemon_loop(hippo, interval_seconds=interval_seconds))


