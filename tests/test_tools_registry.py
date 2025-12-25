from typing import Any, Dict

from elyra.runtime.tools.registry import build_default_registry


def test_docs_search_returns_results_for_known_term() -> None:
    """
    Ensure that the docs_search tool can be invoked and returns a structured
    payload, and that it finds at least one hit for a term that should exist
    in the Elyra docs tree (e.g. \"roadmap\").
    """

    registry = build_default_registry()
    tool = registry.get("docs_search")
    assert tool is not None

    # Use a term that is guaranteed to exist in the canonical v2 docs tree.
    result: Dict[str, Any] = tool({"query": "Braid", "max_hits": 5})
    assert isinstance(result, dict)
    assert result.get("query") == "Braid"

    hits = result.get("hits") or []
    # We do not assert a specific file path here to keep the test robust to
    # doc reorganisations, but we expect at least one hit in the current tree.
    assert isinstance(hits, list)
    assert hits, "Expected at least one docs_search hit for 'Braid'"


