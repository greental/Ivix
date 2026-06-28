from __future__ import annotations

from dataclasses import replace

from .models import BusinessRecord, MatchResult


def classify_result(result: MatchResult) -> MatchResult:
    """Apply deterministic decision rules to one scored candidate."""
    business_name = result.business_name_score
    legal_name = result.legal_entity_score
    address = result.address_score
    reasons = list(result.reasons)

    if business_name >= 92:
        if address >= 80:
            decision = "match"
            reasons.append("decision:strong_business_name_strong_address")
        elif address >= 45:
            decision = "match"
            reasons.append("decision:strong_business_name_medium_address")
        else:
            decision = "match"
            reasons.append("decision:strong_business_name_weak_address_moved_business_allowed")
    elif legal_name >= 92 and address >= 85:
        decision = "match"
        reasons.append("matched by legal entity/owner_name + strong address")
    elif legal_name >= 92:
        decision = "review"
        reasons.append("decision:strong_legal_entity_weak_address_review")
    elif business_name >= 75 and address >= 80:
        decision = "review"
        reasons.append("decision:medium_business_name_strong_address")
    elif business_name < 75 and address >= 80:
        decision = "review"
        reasons.append("decision:weak_business_name_strong_address_not_auto_match")
    else:
        decision = "best_candidate_below_threshold"
        reasons.append("decision:below_threshold")

    return replace(result, decision=decision, reasons=tuple(reasons))


def no_candidate_result(record: BusinessRecord) -> MatchResult:
    return MatchResult(
        id_1=record.record_id,
        id_2="",
        address_score=0.0,
        business_name_score=0.0,
        legal_entity_score=0.0,
        best_name_field="",
        best_name_value="",
        combined_score=0.0,
        decision="no_candidate",
        reasons=("decision:no_candidate",),
    )


def choose_best_result(results: list[MatchResult], record: BusinessRecord | None = None) -> MatchResult:
    if not results:
        if record is None:
            raise ValueError("record is required when no candidate results exist")
        return no_candidate_result(record)
    return classify_result(max(results, key=lambda r: (r.combined_score, r.business_name_score, r.legal_entity_score, r.address_score)))


def resolve_one_to_one(results: list[MatchResult]) -> list[MatchResult]:
    """Resolve dataset2 conflicts while preserving one result row per dataset1 id.

    Winners keep their selected dataset2 id. A losing dataset1 keeps its debug
    row, but its id_2 is cleared so output matches remain one-to-one.
    """
    ordered = sorted(results, key=lambda r: (r.combined_score, r.business_name_score, r.legal_entity_score, r.address_score), reverse=True)
    used_1: set[str] = set()
    used_2: set[str] = set()
    selected_by_id1: dict[str, MatchResult] = {}

    for result in ordered:
        if result.id_1 in used_1:
            continue
        if result.id_2 and result.id_2 in used_2:
            conflict = replace(
                result,
                id_2="",
                decision="best_candidate_below_threshold",
                reasons=(*result.reasons, f"decision:conflict_lost_dataset2={result.id_2}"),
            )
            selected_by_id1[result.id_1] = conflict
            used_1.add(result.id_1)
            continue
        selected_by_id1[result.id_1] = result
        used_1.add(result.id_1)
        if result.id_2:
            used_2.add(result.id_2)

    return [selected_by_id1[result.id_1] for result in sorted(results, key=lambda r: r.id_1) if result.id_1 in selected_by_id1]