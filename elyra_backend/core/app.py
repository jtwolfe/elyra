from typing import Any, Dict, List
import json
import re

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
    logger.info(f"Root: Executing {len(planned)} planned tools")
    for spec in planned:
        name = spec.get("name")
        args = spec.get("args") or {}
        if not isinstance(name, str) or not isinstance(args, dict):
            continue
        try:
            result = await tools.execute(name, **args)
            state["tools_used"].append(name)
            tool_results.append({"name": name, "args": args, "result": result})
            logger.info(f"Root: Successfully executed tool {name}")
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(f"Root: Tool {name} execution failed: {exc}")
    state["tool_results"] = tool_results

    # Ingest tool results into memory so they persist across turns.
    logger.info(f"Root: Successfully executed {len(tool_results)} tools, ingesting to memory")
    for tr in tool_results:
        tool_name = tr.get("name", "")
        tool_args = tr.get("args", {})
        tool_result = tr.get("result", {})
        # Create a synthetic message summarizing the tool execution.
        result_summary = str(tool_result)
        if len(result_summary) > 500:
            result_summary = result_summary[:497] + "..."
        tool_msg_content = (
            f"Tool {tool_name} executed with args {tool_args}: {result_summary}"
        )
        tool_msg = AIMessage(content=tool_msg_content)
        try:
            await hippo.ingest(
                tool_msg,
                state["user_id"],
                state["project_id"],
                thought=f"tool_execution:{tool_name}",
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(f"Root: Memory ingestion failed for tool result: {exc}")

    context, _ = await hippo.recall(
        prompt_text, state["user_id"], state["project_id"]
    )
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
    logger.info("Validator: Placeholder validator - no validation performed (Phase 1)")
    logger.info("Validator: Future implementation will check factual consistency")

    return {}


def determine_tools_for_iteration(iteration: int, previous_results: List, query: str) -> List[Dict]:
    if iteration == 0:
        return [{"name": "docs_search", "args": {"query": query, "top_k": 5}}]
    elif iteration == 1:
        return [{"name": "web_search", "args": {"query": query, "top_k": 5}}]
    elif iteration == 2 and previous_results:
        top_url = previous_results[-1].get("result", {}).get("results", [{}])[0].get("url", "")
        if top_url:
            return [{"name": "browse_page", "args": {"url": top_url}}]
    return []

def has_sufficient_results(results: List) -> bool:
    total_hits = sum(len(r.get("result", {}).get("results", [])) for r in results)
    return total_hits >= settings.RESEARCHER_MIN_RESULTS_THRESHOLD

def should_retry(previous_results: List) -> bool:
    return not has_sufficient_results(previous_results)

def build_multi_iteration_summary(all_results: List, query: str) -> str:
    lines = [f"Research summary for: {query}"]
    for res in all_results:
        tool_name = res.get("name", "")
        result = res.get("result", {})
        if result.get("error"):
            lines.append(f"Error in {tool_name}: {result['error']}")
        else:
            for item in result.get("results", [])[:3]:
                if "content" in item:
                    lines.append(f"- From {item['source_reference']}: {item['content'][:200]}...")
                elif "snippet" in item:
                    lines.append(f"- {item['title']} ({item['url']}): {item['snippet'][:200]}...")
                elif "content" in item:
                    lines.append(f"- Fetched page: {item['content'][:200]}...")
    return "\n".join(lines)

async def researcher_sub(state: ChatState) -> Dict[str, Any]:
    max_iterations = settings.RESEARCHER_MAX_ITERATIONS
    iteration = 0
    all_tool_results = []
    query = str(state["messages"][-1].content).strip()
    messages = state["messages"]
    executed_tool_names = []

    logger.info(f"Researcher: Starting multi-shot research for query: {query}")

    while iteration < max_iterations:
        logger.info(f"Researcher: Starting iteration {iteration + 1}/{max_iterations}")
        tools_to_try = determine_tools_for_iteration(iteration, all_tool_results, query)
        
        if not tools_to_try:
            logger.warning("Researcher: No more tools to try, stopping")
            break
        
        iteration_results = []
        for spec in tools_to_try:
            name = spec["name"]
            args = spec["args"]
            try:
                logger.info(f"Researcher: Executing tool {name} with args {args}")
                result = await tools.execute(name, **args)
                state["tools_used"].append(name)
                executed_tool_names.append(name)
                iteration_results.append({"name": name, "args": args, "result": result})
            except Exception as exc:
                logger.error(f"Researcher: Tool {name} execution failed: {exc}")
                iteration_results.append({"name": name, "args": args, "result": {"error": str(exc)}})
        
        all_tool_results.extend(iteration_results)
        
        if has_sufficient_results(all_tool_results):
            logger.info(f"Researcher: Sufficient results gathered after {iteration + 1} iterations")
            break
        
        if should_retry(iteration_results):
            logger.warning(f"Researcher: Results insufficient, retrying with alternative approach")
            iteration += 1
            continue
        else:
            logger.info("Researcher: No retry needed, stopping")
            break
    
    if iteration >= max_iterations:
        logger.warning(f"Researcher: Maximum iterations reached ({max_iterations}), stopping research")
    
    summary_text = build_multi_iteration_summary(all_tool_results, query)
    ai_msg = AIMessage(content=summary_text)
    messages.append(ai_msg)
    
    state["scratchpad"] = (
        state.get("scratchpad", "")
        + f"\nresearcher_sub: executed tools {executed_tool_names} across {iteration + 1} iterations"
    ).strip()
    
    state["tool_results"] = all_tool_results
    
    return {
        "messages": messages,
        "scratchpad": state["scratchpad"],
        "tools_used": state["tools_used"],
        "tool_results": state["tool_results"],
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

    context, adequacy_score = await hippo.recall(
        user_content, state["user_id"], state["project_id"]
    )

    # Context adequacy signal based on the adequacy score from memory.
    if adequacy_score < 0.3:
        context_hint = (
            "Context status: very sparse or missing; strongly prefer research tools "
            "to gather information before answering."
        )
    elif adequacy_score < 0.6:
        context_hint = (
            "Context status: partial; consider research tools to supplement "
            "existing context."
        )
    else:
        context_hint = (
            "Context status: adequate; tools optional but still useful if needed."
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
        "\n"
        "CRITICAL: I HAVE REAL ACCESS TO ALL TOOLS LISTED BELOW. When the user asks "
        "to \"search the internet\", \"search online\", or requests web information, "
        "I MUST use the web_search tool. I NEVER say I don't have access - I DO have it.\n"
        "\n"
        "- First, I inspect your question and the memory context.\n"
        "- If the existing context already clearly contains the answer, I may "
        "answer directly via my root agent (elyra_root) without additional research.\n"
        "- If context is sparse, missing, or clearly insufficient, I strongly "
        "prefer using research tools or sub-agents (like the researcher agent "
        "calling docs_search or web_search) to gather information before answering.\n"
        "- I REALLY DO have access at runtime to the tools listed below. Treat "
        "them as actual capabilities, not hypothetical. Never say that I do not "
        "have tools if a listed tool could help.\n"
        "- I have access to internal sub-agents: validator, researcher, elyra_root.\n"
        "- I also have access to tools (time, text utilities, docs_search, "
        "read_project_file, web_search, browse_page, code_exec) which you will "
        "see listed separately.\n"
        "- First, I write my reasoning inside <think>...</think> for humans only.\n"
        "- Then I MUST ALWAYS output a JSON plan inside <plan>...</plan> tags with this exact schema:\n"
        '  { \"delegate_to\": \"researcher\" | \"validator\" | \"end\",\n'
        '    \"tools\": [ { \"name\": string, \"args\": object } ] }\n'
        "- The <plan> tags are REQUIRED. I always include them, even if tools=[] and delegate_to=\"end\".\n"
        "- Example format: <plan>{\"delegate_to\":\"researcher\",\"tools\":[{\"name\":\"web_search\",\"args\":{\"query\":\"chocolate cake\",\"top_k\":5}}]}</plan>\n"
        "- If no tools or sub-agent are needed, I use delegate_to=\"end\" and tools=[].\n"
        "\n"
        "MANDATORY TOOL USE RULES:\n"
        "- When user asks about current time, date, or real-time information "
        "(e.g., \"what is the time\", \"what time is it\", \"current time\"), "
        "I MUST include get_time in tools=[].\n"
        "- When user asks to \"search the internet\", \"search online\", \"search the web\", "
        "\"can you search\", \"search for X\", \"look up X\", or ANY request involving "
        "internet/web search, I MUST use web_search tool via researcher agent.\n"
        "- When user asks to \"research X\", I MUST use research tools:\n"
        "  * For Elyra project questions: use docs_search via researcher agent\n"
        "  * For general web information, recipes, current events, or ANY external topic: "
        "use web_search tool via researcher agent\n"
        "  * For specific URLs: use browse_page tool\n"
        "- CRITICAL: If the user explicitly mentions \"search the internet\", \"search online\", "
        "or \"web search\", I MUST ALWAYS plan web_search tool. Never say I don't have "
        "access - I DO have web_search available.\n"
        "- When user asks about external topics, recipes, current events, or information "
        "not in my training data, I MUST use web_search or browse_page.\n"
        "\n"
        "AGENT DELEGATION RULES:\n"
        "- Use researcher agent when gathering information (docs, web, project files).\n"
        "- Use validator agent for factual consistency checks (future use).\n"
        "- Use end (elyra_root) when no sub-agent is needed but tools may still be used."
    )

    # Expanded examples to guide the planner toward reliable tool use.
    examples_text = (
        "Example 1 (time question - MUST use get_time):\n"
        "User: \"what is the time\"\n"
        "Plan: delegate_to=\"end\" and tools=[{\"name\": \"get_time\", \"args\": {}}].\n"
        "\n"
        "Example 2 (research request - MUST use research tools):\n"
        "User: \"can you please research the elyra project\"\n"
        "Context: sparse or empty.\n"
        "Plan: delegate_to=\"researcher\" and tools=[{\"name\": \"docs_search\", "
        "\"args\": {\"query\": \"elyra project\", \"top_k\": 5}}].\n"
        "\n"
        "Example 3 (web search request - MUST use web_search):\n"
        "User: \"search the internet for information about the italian parliament in 1994\"\n"
        "Plan: delegate_to=\"researcher\" and tools=[{\"name\": \"web_search\", "
        "\"args\": {\"query\": \"italian parliament 1994\", \"top_k\": 5}}].\n"
        "\n"
        "Example 3b (explicit internet search - MUST use web_search):\n"
        "User: \"can you search the internet for a chocolate cake recipe\"\n"
        "Plan: delegate_to=\"researcher\" and tools=[{\"name\": \"web_search\", "
        "\"args\": {\"query\": \"chocolate cake recipe\", \"top_k\": 5}}].\n"
        "\n"
        "Example 4 (internal project question):\n"
        "User: \"How does the Elyra project work?\"\n"
        "Context: brief or generic.\n"
        "Plan: delegate_to=\"researcher\" and tools=[{\"name\": \"docs_search\", "
        "\"args\": {\"query\": \"How does the Elyra project work?\", \"top_k\": 3}}].\n"
        "\n"
        "Example 5 (capability demonstration):\n"
        "User: \"Are you able to read the docs for the Elyra project?\"\n"
        "Context: sparse or generic.\n"
        "Plan: delegate_to=\"researcher\" and tools=[{\"name\": \"docs_search\", "
        "\"args\": {\"query\": \"Elyra project docs\", \"top_k\": 3}}].\n"
        "\n"
        "Example 6 (general knowledge question - use web_search):\n"
        "User: \"What happened in Italy in 1994?\"\n"
        "Plan: delegate_to=\"researcher\" and tools=[{\"name\": \"web_search\", "
        "\"args\": {\"query\": \"Italy 1994\", \"top_k\": 5}}].\n"
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

    # Add a final reminder before the user query if it contains search-related keywords
    user_lower = user_content.lower()
    if any(
        phrase in user_lower
        for phrase in [
            "search the internet",
            "search online",
            "search the web",
            "can you search",
            "web search",
        ]
    ):
        planner_messages.append(
            {
                "role": "system",
                "content": (
                    "REMINDER: The user explicitly asked to search the internet/web. "
                    "You MUST use web_search tool via researcher agent. Do NOT say "
                    "you don't have access - you DO have web_search available."
                ),
            }
        )

    planner_messages.append({"role": "user", "content": user_content})
    # Final reminder about required format
    planner_messages.append(
        {
            "role": "system",
            "content": (
                "REMINDER: You MUST output your plan in <plan>...</plan> tags with valid JSON. "
                "Example: <plan>{\"delegate_to\":\"researcher\",\"tools\":[{\"name\":\"web_search\",\"args\":{\"query\":\"test\",\"top_k\":5}}]}</plan>"
            ),
        }
    )

    raw = await ollama_client.chat(planner_messages)

    logger.debug("planner_sub raw LLM response (first 500 chars): %s", raw[:500])

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
            logger.debug("Failed to parse <think> block")

    # Extract <plan>{...}</plan> (optional but expected)
    if "<plan>" in raw and "</plan>" in raw:
        try:
            _, rest = raw.split("<plan>", 1)
            plan_block, _ = rest.split("</plan>", 1)
            plan_block = plan_block.strip()
            logger.debug("Extracted plan block: %s", plan_block)
            plan = json.loads(plan_block)

            delegate = str(plan.get("delegate_to") or "").lower()
            if delegate in {"researcher", "validator", "end"}:
                route = delegate
            else:
                logger.warning(
                    "Planner: Invalid delegate_to value: %s, defaulting to 'end'", delegate
                )
                route = "end"

            tools_spec = plan.get("tools") or []
            if isinstance(tools_spec, list):
                for spec in tools_spec[:3]:  # at most 3 tools per turn
                    name = spec.get("name")
                    args = spec.get("args") or {}
                    if not (isinstance(name, str) and isinstance(args, dict)):
                        logger.warning("Planner: Tool specification invalid: %s", spec)
                    if isinstance(name, str) and isinstance(args, dict):
                        planned_tools.append({"name": name, "args": args})
            logger.info(
                "planner_sub parsed plan: route=%s, tools=%s", route, [t["name"] for t in planned_tools]
            )
            logger.info("Planner: Successfully parsed plan: route=%s, tools=%s", route, [t["name"] for t in planned_tools])
        except json.JSONDecodeError as exc:
            logger.error(
                "Planner: Failed to parse LLM response JSON - %s. Response was: %s", exc, raw[:200]
            )
            route = "end"
            planned_tools = []
        except Exception as exc:  # pragma: no cover - defensive parsing
            logger.exception("Unexpected error parsing planner response: %s", exc)
            route = "end"
            planned_tools = []
    else:
        # No <plan> tags found - try to extract JSON anyway as fallback
        logger.warning(
            "planner_sub response missing <plan> tags. Attempting fallback JSON extraction. Raw response (first 500 chars): %s",
            raw[:500],
        )
        # Try to find JSON object in the response as fallback
        try:
            # Look for JSON-like patterns: { "delegate_to": ... }
            json_match = re.search(r'\{[^{}]*"delegate_to"[^{}]*\}', raw, re.DOTALL)
            if json_match:
                plan_str = json_match.group(0)
                logger.info("Found JSON-like pattern in response, attempting parse: %s", plan_str[:200])
                plan = json.loads(plan_str)
                delegate = str(plan.get("delegate_to") or "").lower()
                if delegate in {"researcher", "validator", "end"}:
                    route = delegate
                tools_spec = plan.get("tools") or []
                if isinstance(tools_spec, list):
                    for spec in tools_spec[:3]:
                        name = spec.get("name")
                        args = spec.get("args") or {}
                        if isinstance(name, str) and isinstance(args, dict):
                            planned_tools.append({"name": name, "args": args})
                logger.info(
                    "Fallback JSON extraction succeeded: route=%s, tools=%s",
                    route,
                    [t["name"] for t in planned_tools],
                )
        except Exception as fallback_exc:
            logger.error("Fallback JSON extraction also failed: %s", fallback_exc)

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


