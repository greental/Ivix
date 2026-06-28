from __future__ import annotations

from rapidfuzz import fuzz

from .models import AddressParts, MatchCandidate, MatchResult


def score_name(candidate: MatchCandidate) -> tuple[float, list[str]]:
    left = candidate.record1.normalized_name
    scores: list[tuple[float, str]] = []
    for right in candidate.record2.all_normalized_names:
        if left and right:
            scores.append((float(fuzz.token_set_ratio(left, right)), right))
    if not scores:
        return 0.0, ["name:missing"]
    best_score, best_name = max(scores, key=lambda item: item[0])
    return best_score, [f"name:best={best_score:.1f} against '{best_name}'"]


def _component_score(left: str, right: str, weight: float, label: str, reasons: list[str]) -> float:
    if not left or not right:
        reasons.append(f"address:{label}=missing")
        return 0.0
    if left == right:
        reasons.append(f"address:{label}=match")
        return weight
    reasons.append(f"address:{label}=diff")
    return 0.0


def score_address_parts(left: AddressParts, right: AddressParts) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    score += _component_score(left.street_number, right.street_number, 22.0, "street_number", reasons)
    score += _component_score(left.street_name, right.street_name, 20.0, "street_name", reasons)
    score += _component_score(left.street_type, right.street_type, 8.0, "street_type", reasons)
    score += _component_score(left.city, right.city, 15.0, "city", reasons)
    score += _component_score(left.state, right.state, 10.0, "state", reasons)
    score += _component_score(left.postal_code5, right.postal_code5, 20.0, "zip5", reasons)
    if left.postal_code_full and right.postal_code_full and left.postal_code_full == right.postal_code_full:
        score += 5.0
        reasons.append("address:full_zip=match")
    elif left.postal_code_full or right.postal_code_full:
        reasons.append("address:full_zip=no_match_or_missing")
    return min(score, 100.0), reasons


def score_candidate(candidate: MatchCandidate) -> MatchResult:
    name_score, name_reasons = score_name(candidate)
    address_score, address_reasons = score_address_parts(candidate.record1.address, candidate.record2.address)
    combined_score = round((name_score * 0.62) + (address_score * 0.38), 2)
    reasons = [*candidate.blocking_reasons, *name_reasons, *address_reasons]
    return MatchResult(
        id_1=candidate.record1.record_id,
        id_2=candidate.record2.record_id,
        address_score=round(address_score, 2),
        name_score=round(name_score, 2),
        combined_score=combined_score,
        decision="unclassified",
        reasons=tuple(reasons),
    )