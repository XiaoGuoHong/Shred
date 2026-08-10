from __future__ import annotations

from collections.abc import Sequence

from shred.classification.contracts import CorrectionContext


def _bigrams(text: str) -> set[str]:
    return {text[i : i + 2] for i in range(len(text) - 1)}


def _jaccard(text: str, other: str) -> float:
    a = _bigrams(text)
    b = _bigrams(other)
    if not a and not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def rank_corrections(
    text: str,
    corrections: Sequence[CorrectionContext],
    limit: int = 5,
) -> list[CorrectionContext]:
    scored: list[tuple[float, int, CorrectionContext]] = []
    for idx, correction in enumerate(corrections):
        score = _jaccard(text, correction.event_text)
        scored.append((score, idx, correction))

    positive = [(s, i, c) for s, i, c in scored if s > 0]

    if not positive:
        return list(corrections[:3])

    positive.sort(key=lambda x: (-x[0], x[1]))
    return [c for _, _, c in positive[:limit]]
