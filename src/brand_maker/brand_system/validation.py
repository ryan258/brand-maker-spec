"""Pure validation helpers for canonical living-brand contracts."""

import re
from collections.abc import Iterable, Mapping

HTML_TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")


def reject_raw_html(value: str) -> str:
    """Reject HTML-shaped markup while allowing ordinary angle-bracket prose."""

    if HTML_TAG.search(value):
        raise ValueError("raw HTML is not allowed in narrative content")
    return value


def require_unique_ids(ids: Iterable[str]) -> set[str]:
    """Return all IDs after rejecting the first duplicate."""

    found: set[str] = set()
    for canonical_id in ids:
        if canonical_id in found:
            raise ValueError(f"duplicate canonical id: {canonical_id}")
        found.add(canonical_id)
    return found


def require_known_references(
    references: Iterable[tuple[str, str]], known_by_kind: Mapping[str, set[str]]
) -> None:
    """Reject references whose target is absent or has the wrong canonical kind."""

    for kind, target_id in references:
        if target_id not in known_by_kind.get(kind, set()):
            raise ValueError(f"dangling reference: {target_id}")


def require_acyclic_token_graph(graph: Mapping[str, set[str]]) -> None:
    """Reject direct or indirect cycles between canonical tokens."""

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(token_id: str) -> None:
        if token_id in visiting:
            raise ValueError(f"token reference cycle involving: {token_id}")
        if token_id in visited:
            return
        visiting.add(token_id)
        for dependency in graph.get(token_id, set()):
            visit(dependency)
        visiting.remove(token_id)
        visited.add(token_id)

    for token_id in graph:
        visit(token_id)
