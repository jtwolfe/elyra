"""
HippocampalSim interfaces and in-memory stub implementation.

The `stub` module provides the Phase 1 in-memory version. Future
implementations will add Redis/Neo4j/Qdrant-backed variants that
preserve the same public interface.
"""

from .stub import HippocampalSim  # re-export for convenience

__all__ = ["HippocampalSim"]


