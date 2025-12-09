from typing import Any, Dict

from elyra_backend.tools import ToolRegistry


def test_docs_search_returns_results_for_known_term() -> None:
    """
    Ensure that the docs_search tool can be invoked and returns a structured
    payload, and that it finds at least one hit for a term that should exist
    in the Elyra docs tree (e.g. \"roadmap\").
    """

    registry = ToolRegistry()

    result: Dict[str, Any] = registry._tool_docs_search("roadmap", top_k=5)  # type: ignore[attr-defined]
    assert isinstance(result, dict)
    assert result.get("query") == "roadmap"

    hits = result.get("results") or []
    # We do not assert a specific file path here to keep the test robust to
    # doc reorganisations, but we expect at least one hit in the current tree.
    assert isinstance(hits, list)
    assert hits, "Expected at least one docs_search hit for 'roadmap'"


