from typing import Any, Dict, List

from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langgraph.graph import START, END, StateGraph

from elyra_backend.config import settings
from elyra_backend.core.state import ChatState
from elyra_backend.llm.ollama_client import OllamaClient
from elyra_backend.memory.hippocampal_sim.stub import HippocampalSim
from elyra_backend.tools.registry import ToolRegistry
from elyra_backend.logging import get_logger
from elyra_backend.daemon import register_session, start_daemon_loop


app = FastAPI(title="Elyra v1")

logger = get_logger(__name__)

ollama_client = OllamaClient()
hippo = HippocampalSim()
tools = ToolRegistry()


@app.on_event("startup")
async def _start_daemon() -> None:
    """
    Optionally start the background daemon loop if enabled via settings.

    The daemon is responsible for simple replay-like behaviour in later phases.
    For Phase 1 it only generates occasional internal thoughts in the background.
    """
    if settings.ENABLE_DAEMON:
        start_daemon_loop(hippo)


@app.get("/health")
async def health() -> Dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok", "model": settings.OLLAMA_MODEL}


async def elyra_root(state: ChatState) -> Dict[str, Any]:
    """
    Single-node Elyra root workflow for the Phase 1 MVP.

    - Recalls a small amount of context from HippocampalSim.
    - Generates a trivial internal thought string.
    - Optionally calls a simple tool (get_time) based on the prompt.
    - Calls the Ollama LLM and returns an assistant message.

    The root node treats `state["messages"]` as a short conversational history and
    uses the latest human message as the primary prompt, while threading a
    small slice of recent turns into the LLM call.
    """
    messages: List[BaseMessage] = state["messages"]
    last_message = messages[-1]
    prompt_text = getattr(last_message, "content", "")

    context = await hippo.recall(prompt_text, state["user_id"], state["project_id"])
    thought = await hippo.generate_thought(state["user_id"], state["project_id"])

    tool_result_text = ""
    lowered = prompt_text.lower()

    # Very small, explicit trigger phrases for built-in tools.
    try:
        if "what time is it" in lowered or "current time" in lowered:
            logger.info("Invoking tool 'get_time' based on prompt content.")
            tool_result = await tools.execute("get_time")
            tool_result_text += f"\n\n[tool:get_time] {tool_result}"

        if "summarize:" in lowered:
            # Take everything after the first occurrence of "summarize:".
            summary_target = prompt_text.split("summarize:", 1)[-1].strip()
            logger.info("Invoking tool 'summarize_text' based on prompt content.")
            tool_result = await tools.execute("summarize_text", text=summary_target)
            tool_result_text += f"\n\n[tool:summarize_text] {tool_result}"

        if "echo with time:" in lowered:
            echo_target = prompt_text.split("echo with time:", 1)[-1].strip()
            logger.info("Invoking tool 'echo_with_time' based on prompt content.")
            tool_result = await tools.execute("echo_with_time", text=echo_target)
            tool_result_text += f"\n\n[tool:echo_with_time] {tool_result}"
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Tool invocation failed: %s", exc)

    assembled_messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": "\n\n".join(
                [
                    hippo.system_prompt,
                    f"Memory context:\n{context}",
                    f"Internal thought:\n{thought}",
                    tool_result_text or "",
                ]
            ).strip(),
        }
    ]

    # Thread in a small slice of recent dialog history (excluding the latest
    # message, which is added explicitly below) to keep prompts compact but
    # conversational.
    history_slice = messages[:-1][-3:]
    for m in history_slice:
        role = "user"
        msg_type = getattr(m, "type", "")
        if msg_type == "ai":
            role = "assistant"
        elif msg_type == "human":
            role = "user"
        assembled_messages.append(
            {
                "role": role,
                "content": getattr(m, "content", ""),
            }
        )

    # Add the latest user message at the end of the prompt.
    assembled_messages.append({"role": "user", "content": prompt_text})

    try:
        reply_text = await ollama_client.chat(assembled_messages)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Error while calling OllamaClient.chat: %s", exc)
        reply_text = (
            "I ran into an internal error while talking to the language model. "
            "Please try again in a moment."
        )
    ai_msg = AIMessage(content=reply_text)

    await hippo.ingest(ai_msg, state["user_id"], state["project_id"], thought)

    return {"messages": [ai_msg], "thought": thought}


async def validator_sub(state: ChatState) -> Dict[str, Any]:
    """
    Placeholder validator sub-agent.

    In later phases this will perform factual consistency checks. For now it
    simply passes the state through unchanged so that the graph structure
    matches the planned architecture.
    """
    # No-op for Phase 1.
    return {}


async def researcher_sub(state: ChatState) -> Dict[str, Any]:
    """
    Placeholder researcher sub-agent.

    Eventually this node will orchestrate web/API tools. For now it is a
    no-op that exists so the LangGraph wiring mirrors the design docs.
    """
    # No-op for Phase 1.
    return {}


def _elyra_router(state: ChatState) -> str:
    """
    Extremely simple router deciding where to go after the root node.

    This is intentionally heuristic and mostly illustrative:
    - if the last user message mentions \"validate\", branch to validator_sub;
    - if it mentions \"research\" or \"web\", branch to researcher_sub;
    - otherwise, end the graph.
    """
    messages: List[BaseMessage] = state["messages"]
    last = messages[-1]
    content = str(getattr(last, "content", "")).lower()
    if "validate" in content:
        return "validator"
    if "research" in content or "web" in content:
        return "researcher"
    return "end"


workflow = StateGraph(ChatState)
workflow.add_node("elyra_root", elyra_root)
workflow.add_node("validator_sub", validator_sub)
workflow.add_node("researcher_sub", researcher_sub)
workflow.add_edge(START, "elyra_root")
workflow.add_conditional_edges(
    "elyra_root",
    _elyra_router,
    {
        "validator": "validator_sub",
        "researcher": "researcher_sub",
        "end": END,
    },
)
workflow.add_edge("validator_sub", END)
workflow.add_edge("researcher_sub", END)
app_graph = workflow.compile()


@app.websocket("/chat/{user_id}/{project_id}")
async def chat_ws(websocket: WebSocket, user_id: str, project_id: str) -> None:
    """
    WebSocket endpoint for the Web UI.

    Expects JSON objects of the form:
        {"content": "hello world"}
    and streams back assistant messages plus the internal thought string.
    """
    await websocket.accept()
    logger.info("WebSocket connected for user_id=%s project_id=%s", user_id, project_id)
    # Track this session for potential background daemon work.
    register_session(user_id, project_id)
    # Maintain a short per-connection message history so that each turn can
    # see recent context while still keeping prompts small.
    session_messages: List[BaseMessage] = []
    try:
        while True:
            data = await websocket.receive_json()
            content = str(data.get("content", ""))
            logger.info(
                "Received user message on WebSocket (user_id=%s, project_id=%s): %s",
                user_id,
                project_id,
                content[:200],
            )
            user_message = HumanMessage(content=content)
            session_messages.append(user_message)

            state: ChatState = {
                "messages": session_messages,
                "user_id": user_id,
                "project_id": project_id,
                # Initial value is ignored by the node; it will overwrite this.
                "thought": "",
            }

            # For the MVP, keep things simple and just invoke the graph once
            # per user message instead of streaming intermediate chunks.
            try:
                result = await app_graph.ainvoke(state)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Error during LangGraph invocation: %s", exc)
                await websocket.send_json(
                    {
                        "type": "assistant_message",
                        "role": "assistant",
                        "content": (
                            "Something went wrong while processing your request. "
                            "Please try again or rephrase your question."
                        ),
                        "thought": "",
                    }
                )
                continue
            messages = result.get("messages") or []
            if not messages:
                continue

            last = messages[-1]
            session_messages.append(last)
            await websocket.send_json(
                {
                    "type": "assistant_message",
                    "role": "assistant",
                    "content": getattr(last, "content", ""),
                    "thought": result.get("thought", ""),
                }
            )
    except WebSocketDisconnect:
        # Normal disconnect; nothing special to do.
        logger.info(
            "WebSocket disconnected for user_id=%s project_id=%s",
            user_id,
            project_id,
        )
        return


