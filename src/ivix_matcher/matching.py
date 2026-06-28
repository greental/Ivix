from __future__ import annotations

from .candidates import CandidateIndex
from .decision import choose_best_result, resolve_one_to_one
from .models import BusinessRecord, MatchResult
from .scoring import score_candidate


def match_records(dataset1: list[BusinessRecord], dataset2: list[BusinessRecord]) -> list[MatchResult]:
    """Run the deterministic linkage pipeline and return one result per resolvable record.

    Candidate lookup is performed only through indexes built over dataset2.
    """
    index = CandidateIndex.build(dataset2)
    best_results: list[MatchResult] = []
    for record1 in dataset1:
        candidates = index.query(record1)
        scored = [score_candidate(candidate) for candidate in candidates]
        best_results.append(choose_best_result(scored, record1))
    return resolve_one_to_one(best_results)