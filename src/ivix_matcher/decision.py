from __future__ import annotations

from dataclasses import replace

from .models import BusinessRecord, MatchResult


def classify_result(result: MatchResult) -> MatchResult:
    """Apply deterministic decision rules to one scored candidate."""
    name = result.name_score
    address = result.address_score
    reasons = list(result.reasons)

    if name >= 92:
        if address >= 80:
            decision = "match"
            reasons.append("decision:strong_name_strong_address")
        elif address >= 45:
            decision = "match"
            reasons.append("decision:strong_name_medium_address")
        else:
            decision = "match"
            reasons.append("decision:strong_name_weak_address_moved_business_allowed")
    elif name >= 75 and address >= 80:
        decision = "review"
        reasons.append("decision:medium_name_strong_address")
    elif name < 75 and address >= 80:
        decision = "review"
        reasons.append("decision:weak_name_strong_address_not_auto_match")
    else:
        decision = "best_candidate_below_threshold"
        reasons.append("decision:below_threshold")

    return replace(result, decision=decision, reasons=tuple(reasons))


def no_candidate_result(record: BusinessRecord) -> MatchResult:
    return MatchResult(
        id_1=record.record_id,
        id_2="",
        address_score=0.0,
        name_score=0.0,
        combined_score=0.0,
        decision="no_candidate",
        reasons=("decision:no_candidate",),
    )


def choose_best_result(results: list[MatchResult], record: BusinessRecord | None = None) -> MatchResult:
    if not results:
        if record is None:
            raise ValueError("record is required when no candidate results exist")
        return no_candidate_result(record)
    return classify_result(max(results, key=lambda r: (r.combined_score, r.name_score, r.address_score)))


def resolve_one_to_one(results: list[MatchResult]) -> list[MatchResult]:
    """Keep each dataset1 and dataset2 id at most once, preferring strongest matches."""
    ordered = sorted(results, key=lambda r: (r.combined_score, r.name_score, r.address_score), reverse=True)
    used_1: set[str] = set()
    used_2: set[str] = set()
    selected: list[MatchResult] = []

    for result in ordered:
        if result.id_1 in used_1:
            continue
        if result.id_2 and result.id_2 in used_2:
            continue
        selected.append(result)
        used_1.add(result.id_1)
        if result.id_2:
            used_2.add(result.id_2)

    return sorted(selected, key=lambda r: r.id_1)