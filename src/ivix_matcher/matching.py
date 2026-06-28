from __future__ import annotations

from dataclasses import dataclass

from .candidates import CandidateIndex
from .config import MatchingConfig, load_config
from .decision import choose_best_result, classify_result, resolve_one_to_one, no_candidate_result
from .models import BusinessRecord, MatchResult
from .scoring import score_candidate


@dataclass(frozen=True)
class MatchRun:
    selected_results: list[MatchResult]
    debug_results: list[MatchResult]


def run_matching(dataset1: list[BusinessRecord], dataset2: list[BusinessRecord], config: MatchingConfig | None = None) -> MatchRun:
    config = config or load_config()
    index = CandidateIndex.build(dataset2, config)
    best_results: list[MatchResult] = []
    debug_results: list[MatchResult] = []
    for record1 in dataset1:
        candidates = index.query(record1)
        scored = [score_candidate(candidate) for candidate in candidates]
        classified = [classify_result(result, config) for result in scored]
        debug_results.extend(classified if classified else [no_candidate_result(record1)])
        best_results.append(choose_best_result(scored, record1, config))
    return MatchRun(selected_results=resolve_one_to_one(best_results), debug_results=debug_results)


def match_records(dataset1: list[BusinessRecord], dataset2: list[BusinessRecord], config: MatchingConfig | None = None) -> list[MatchResult]:
    """Run the deterministic linkage pipeline and return one result per resolvable record.

    Candidate lookup is performed only through indexes built over dataset2.
    """
    return run_matching(dataset1, dataset2, config).selected_results