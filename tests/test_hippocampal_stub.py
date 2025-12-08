import asyncio

from langchain_core.messages import AIMessage

from elyra_backend.memory.hippocampal_sim import HippocampalSim


def test_hippocampal_sim_recall_and_ingest_basic() -> None:
    sim = HippocampalSim()
    user_id = "u1"
    project_id = "p1"

    async def run() -> None:
        # Initially, no context is available.
        ctx_empty = await sim.recall("hello", user_id, project_id)
        assert "No prior episodic context" in ctx_empty

        # Ingest a couple of messages and ensure they are reflected in recall.
        msg1 = AIMessage(content="First reply")
        msg2 = AIMessage(content="Second reply")

        thought = "internal thought"
        await sim.ingest(msg1, user_id, project_id, thought)
        await sim.ingest(msg2, user_id, project_id, thought)

        ctx = await sim.recall("hello again", user_id, project_id)
        assert "First reply" in ctx
        assert "Second reply" in ctx

    asyncio.run(run())


