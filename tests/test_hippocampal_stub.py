import asyncio

from langchain_core.messages import AIMessage, HumanMessage

from elyra_backend.memory.hippocampal_sim import HippocampalSim


def test_hippocampal_sim_recall_and_ingest_basic() -> None:
    sim = HippocampalSim()
    user_id = "u1"
    project_id = "p1"

    async def run() -> None:
        # Initially, no context is available.
        ctx_empty = await sim.recall("hello", user_id, project_id)
        assert "No prior episodic context" in ctx_empty

        # Ingest a user message and a couple of assistant messages and ensure
        # they are reflected in recall.
        user_msg = HumanMessage(content="How does memory work in Elyra?")
        msg1 = AIMessage(content="First reply about memory")
        msg2 = AIMessage(content="Second reply with more details")

        thought = "internal thought"
        await sim.ingest(user_msg, user_id, project_id, thought)
        await sim.ingest(msg1, user_id, project_id, thought)
        await sim.ingest(msg2, user_id, project_id, thought)

        ctx = await sim.recall("hello again", user_id, project_id)
        # The new recall format separates user questions and assistant replies.
        assert "Recent user questions" in ctx
        assert "Recent assistant replies" in ctx
        assert "How does memory work in Elyra?" in ctx
        assert "First reply about memory" in ctx
        assert "Second reply with more details" in ctx

    asyncio.run(run())


