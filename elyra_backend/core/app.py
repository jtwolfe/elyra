from typing import Any, Dict, List
import json

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
    Elyra root workflow: execute planned tools (if any), then call the LLM
    to produce a final user-facing answer.

    The root node treats ``state["messages"]`` as a short conversational history
    and uses the latest human message as the primary prompt, while threading a
    small slice of recent turns into the LLM call.
    """
    messages: List[BaseMessage] = state["messages"]
    last_message = messages[-1]
    prompt_text = getattr(last_message, "content", "")

    # Execute any tools that the planner requested for this turn.
    tool_results: List[Dict[str, Any]] = []
    planned = state.get("planned_tools") or []
    for spec in planned:
        name = spec.get("name")
        args = spec.get("args") or {}
        if not isinstance(name, str) or not isinstance(args, dict):
            continue
        try:
            result = await tools.execute(name, **args)
            state["tools_used"].append(name)
            tool_results.append({"name": name, "args": args, "result": result})
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Tool invocation failed for %s: %s", name, exc)
    state["tool_results"] = tool_results

    context = await hippo.recall(prompt_text, state["user_id"], state["project_id"])
    # Baseline internal thought from HippocampalSim. This is used as part of the
    # prompt but may be overridden for UI purposes if the model returns its own
    # explicit thinking (e.g. in <think>...</think> blocks).
    base_thought = await hippo.generate_thought(
        state["user_id"], state["project_id"]
    )

    # Convert tool_results into a compact text block for the prompt.
    tool_block = ""
    if tool_results:
        lines = ["Tool outputs:"]
        for tr in tool_results:
            n = tr.get("name")
            r = tr.get("result")
            snippet = str(r)
            if len(snippet) > 300:
                snippet = snippet[:297] + "..."
            lines.append(f"- {n}: {snippet}")
        tool_block = "\n".join(lines)

    assembled_messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": "\n\n".join(
                [
                    hippo.system_prompt,
                    f"Memory context:\n{context}",
                    f"Internal thought:\n{base_thought}",
                    tool_block,
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

    # If the model produced an explicit thinking section (e.g. <think>...</think>),
    # separate that from the user-facing reply. The inner think text becomes the
    # dynamic per-turn `thought` shown in the UI, while the visible reply is what
    # the user sees in the chat.
    final_thought = base_thought
    visible_reply = reply_text
    if "<think>" in reply_text and "</think>" in reply_text:
        try:
            _pre, rest = reply_text.split("<think>", 1)
            think_block, after = rest.split("</think>", 1)
            inner_thought = think_block.strip()
            # Prefer everything after </think> as the visible reply; fall back to
            # the original if parsing yields an empty string.
            candidate_reply = after.strip()
            if candidate_reply:
                visible_reply = candidate_reply
            final_thought = inner_thought or base_thought
        except Exception:  # pragma: no cover - defensive parsing
            visible_reply = reply_text
            final_thought = base_thought

    ai_msg = AIMessage(content=visible_reply)
    await hippo.ingest(ai_msg, state["user_id"], state["project_id"], final_thought)

    # Record a brief note in the scratchpad for routing/debug purposes.
    state["scratchpad"] = (
        state.get("scratchpad", "") + "\nelyra_root: replied to user message"
    ).strip()

    return {
        "messages": [ai_msg],
        "thought": final_thought,
        "tools_used": state["tools_used"],
        "scratchpad": state["scratchpad"],
        "planned_tools": state.get("planned_tools", []),
        "tool_results": state.get("tool_results", []),
    }


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
    Researcher sub-agent for Elyra.

    For the current phase this acts as a simple research executor:
    - when routed here by the planner (route == \"researcher\"), it calls
      the ``docs_search`` tool against the local docs tree using the latest
      user message as the query,
    - and appends a short synthetic message summarising the findings.
    """
    # Only perform research when the planner explicitly delegates here.
    route = (state.get("route") or "").lower()
    if route != "researcher":
        return {}

    messages: List[BaseMessage] = state["messages"]
    last = messages[-1]
    content = str(getattr(last, "content", "")).strip()

    try:
        logger.info("researcher_sub invoking 'docs_search' for query: %s", content)
        search_result = await tools.execute("docs_search", query=content, top_k=5)
        state["tools_used"].append("docs_search")
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("researcher_sub tool invocation failed: %s", exc)
        return {}

    hits = search_result.get("results") or []
    if not hits:
        summary_text = (
            "I searched the local Elyra documentation for your question, but did "
            "not find any directly relevant sections."
        )
    else:
        lines: List[str] = ["I searched the Elyra docs and found these sections:"]
        for hit in hits[:3]:
            path = hit.get("path", "")
            snippet = (hit.get("snippet") or "").strip().replace("\n", " ")
            if len(snippet) > 200:
                snippet = snippet[:197] + "..."
            lines.append(f"- {path}: {snippet}")
        summary_text = "\n".join(lines)

    ai_msg = AIMessage(content=summary_text)
    messages.append(ai_msg)
    state["scratchpad"] = (
        state.get("scratchpad", "")
        + ("\n" if state.get("scratchpad") else "")
        + "researcher_sub: responded with docs_search summary"
    ).strip()
    return {
        "messages": messages,
        "scratchpad": state["scratchpad"],
        "tools_used": state["tools_used"],
    }


def _elyra_router(state: ChatState) -> str:
    """
    Router that uses the planner's `route` field instead of keyword heuristics.
    """
    route = (state.get("route") or "").lower()
    if route in {"validator", "researcher"}:
        return route
    return "end"


async def planner_sub(state: ChatState) -> Dict[str, Any]:
    """
    Planner sub-agent.

    - Looks at the latest user message, recent history, and memory context.
    - Decides which sub-agent to delegate to and which tools to call.
    - Writes its internal reasoning into `thought` and its plan into
      `route` and `planned_tools`.
    """
    messages: List[BaseMessage] = state["messages"]
    last = messages[-1]
    user_content = str(getattr(last, "content", "")).strip()

    context = await hippo.recall(user_content, state["user_id"], state["project_id"])

    # Very lightweight context adequacy signal based on the length of the
    # recalled context. This is a stand-in for the richer scoring described in
    # the memory architecture docs.
    lines = [ln for ln in str(context).splitlines() if ln.strip()]
    context_len = len(lines)
    if context_len == 0:
        context_hint = "Context status: empty or unavailable for this topic."
    elif context_len < 5:
        context_hint = "Context status: sparse; consider research tools."
    else:
        context_hint = (
            "Context status: non-trivial; you may still use tools if helpful."
        )

    tools_catalog = tools.list_tools()
    agents_desc = {
        "validator": "Checks factual consistency of answers.",
        "researcher": "Uses tools (e.g. docs_search) to gather external/project info.",
        "elyra_root": "Synthesises final user-facing answers.",
    }

    planner_system = (
        "I am Elyra's internal planner. I think step-by-step about what I should "
        "do next before I answer you.\n"
        "- First, I inspect your question and the memory context.\n"
        "- If the existing context already clearly contains the answer, I may "
        "answer directly via my root agent (elyra_root) without additional research.\n"
        "- If context is sparse, missing, or clearly insufficient, I strongly "
        "prefer using research tools or sub-agents (like the researcher agent "
        "calling docs_search) to gather information before answering.\n"
        "- I have access to internal sub-agents: validator, researcher, elyra_root.\n"
        "- I also have access to tools (time, text utilities, docs_search, "
        "read_project_file, web_search, browse_page, code_exec) which you will "
        "see listed separately.\n"
        "- First, I write my reasoning inside <think>...</think> for humans only.\n"
        "- Then I output a single JSON plan inside <plan>...</plan> with schema:\n"
        '  { \"delegate_to\": \"researcher\" | \"validator\" | \"end\",\n'
        '    \"tools\": [ { \"name\": string, \"args\": object } ] }\n'
        "- If no tools or sub-agent are needed, I use delegate_to=\"end\" and tools=[].\n"
        "- I prefer the researcher agent plus docs_search when you ask about Elyra "
        "itself (architecture, memory, roadmap, how Elyra works) or mention "
        "docs/documentation.\n"
        "- When you ask about my capabilities with tools or agents (for example, "
        "\"can you research\" or \"can you read the docs\"), I plan at least one "
        "safe research step that demonstrates those capabilities when possible."
    )

    # A couple of lightweight examples to bias the planner toward sensible
    # research behaviour without over-constraining it.
    examples_text = (
        "Example 1 (internal project question):\n"
        "User: \"How does the Elyra project work?\"\n"
        "Context: brief or generic.\n"
        "Plan: delegate_to=\"researcher\" and tools=[{\"name\": \"docs_search\", "
        "\"args\": {\"query\": \"How does the Elyra project work?\", \"top_k\": 3}}].\n"
        "\n"
        "Example 2 (simple factual tool question):\n"
        "User: \"What is the current time?\"\n"
        "Plan: delegate_to=\"end\" and tools=[{\"name\": \"get_time\", \"args\": {}}].\n"
        "\n"
        "Example 3 (capability + docs question):\n"
        "User: \"Are you able to read the docs for the Elyra project?\"\n"
        "Context: sparse or generic.\n"
        "Plan: delegate_to=\"researcher\" and tools=[{\"name\": \"docs_search\", "
        "\"args\": {\"query\": \"Elyra project docs\", \"top_k\": 3}}].\n"
    )

    planner_messages: List[Dict[str, str]] = [
        {"role": "system", "content": planner_system},
        {"role": "system", "content": examples_text},
        {"role": "system", "content": f"Memory context:\n{context}"},
        {"role": "system", "content": context_hint},
        {
            "role": "system",
            "content": "Available tools:\n"
            + "\n".join(f"- {name}: {desc}" for name, desc in tools_catalog.items()),
        },
        {
            "role": "system",
            "content": "Available sub-agents:\n"
            + "\n".join(f"- {k}: {v}" for k, v in agents_desc.items()),
        },
    ]

    # Short history slice (excluding latest, which we add explicitly)
    history_slice = messages[:-1][-3:]
    for m in history_slice:
        role = "assistant" if getattr(m, "type", "") == "ai" else "user"
        planner_messages.append(
            {"role": role, "content": str(getattr(m, "content", ""))}
        )

    planner_messages.append({"role": "user", "content": user_content})

    raw = await ollama_client.chat(planner_messages)

    planner_thought = state.get("thought", "")
    route = "end"
    planned_tools: List[Dict[str, Any]] = []

    # Extract <think> (optional)
    if "<think>" in raw and "</think>" in raw:
        try:
            _, rest = raw.split("<think>", 1)
            think_block, after_think = rest.split("</think>", 1)
            planner_thought = think_block.strip() or planner_thought
            raw = after_think.strip()
        except Exception:  # pragma: no cover - defensive parsing
            pass

    # Extract <plan>{...}</plan> (optional but expected)
    if "<plan>" in raw and "</plan>" in raw:
        try:
            _, rest = raw.split("<plan>", 1)
            plan_block, _ = rest.split("</plan>", 1)
            plan = json.loads(plan_block)

            delegate = str(plan.get("delegate_to") or "").lower()
            if delegate in {"researcher", "validator", "end"}:
                route = delegate
            else:
                route = "end"

            tools_spec = plan.get("tools") or []
            if isinstance(tools_spec, list):
                for spec in tools_spec[:3]:  # at most 3 tools per turn
                    name = spec.get("name")
                    args = spec.get("args") or {}
                    if isinstance(name, str) and isinstance(args, dict):
                        planned_tools.append({"name": name, "args": args})
        except Exception:  # pragma: no cover - defensive parsing
            route = "end"
            planned_tools = []

    scratch = state.get("scratchpad", "")
    note = f"planner_sub: route={route}, planned_tools={[t['name'] for t in planned_tools]}"
    state["scratchpad"] = (scratch + ("\n" if scratch else "") + note).strip()

    state["route"] = route
    state["planned_tools"] = planned_tools
    state["thought"] = planner_thought

    return {
        "thought": state["thought"],
        "route": state["route"],
        "planned_tools": state["planned_tools"],
        "scratchpad": state["scratchpad"],
    }


workflow = StateGraph(ChatState)
workflow.add_node("planner_sub", planner_sub)
workflow.add_node("elyra_root", elyra_root)
workflow.add_node("validator_sub", validator_sub)
workflow.add_node("researcher_sub", researcher_sub)
workflow.add_edge(START, "planner_sub")
workflow.add_conditional_edges(
    "planner_sub",
    _elyra_router,
    {
        "validator": "validator_sub",
        "researcher": "researcher_sub",
        "end": "elyra_root",
    },
)
workflow.add_edge("validator_sub", "elyra_root")
workflow.add_edge("researcher_sub", "elyra_root")
workflow.add_edge("elyra_root", END)
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
                "tools_used": [],
                "scratchpad": "",
                "route": None,
                "planned_tools": [],
                "tool_results": [],
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
                    # Trace information is used by the UI debug panel to show
                    # what Elyra was reasoning over for this turn.
                    "trace": {
                        "tools_used": result.get("tools_used", []),
                        "scratchpad": result.get("scratchpad", ""),
                        "planned_tools": result.get("planned_tools", []),
                        "tool_results": result.get("tool_results", []),
                    },
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


