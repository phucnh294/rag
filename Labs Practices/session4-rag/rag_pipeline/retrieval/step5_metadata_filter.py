"""Pre-filter candidates by status/area before reranking.

If any candidate's document is tagged status="current" (the authoritative
source for its topic), drop reference-only candidates that are either
untagged (area is None — can't confirm they're about something else) or
share one of the current document(s)' area. A reference-only candidate
with an explicit, different area survives, since it's confirmed to be
about an unrelated topic rather than a same-topic decoy.

Falls back to the full pool when nothing is tagged current (an un-curated
topic), or when the caller explicitly opts in to reference-only content
via include_reference.
"""

from __future__ import annotations

from typing import Any


def filter_by_metadata_martin(
    candidates: list[Any], include_reference: bool = False
) -> list[Any]:
    """Return candidates with same-topic reference-only chunks excluded."""
    if include_reference:
        return candidates

    current_areas = {c.get("area") for c in candidates if c.get("status") == "current"}
    if not current_areas:
        return candidates

    def is_same_topic_reference(chunk: Any) -> bool:
        if chunk.get("status") == "current":
            return False
        return chunk.get("area") is None or chunk.get("area") in current_areas

    return [c for c in candidates if not is_same_topic_reference(c)]
