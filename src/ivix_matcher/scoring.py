from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from .models import AddressParts, BusinessRecord, MatchCandidate, MatchResult
from .normalize import generate_name_variants


@dataclass(frozen=True)
class NameScore:
    score: float
    field: str
    value: str
    reason: str


def _field_names(record: BusinessRecord) -> list[tuple[str, str]]:
    names = [("name", record.raw_name)]
    names.extend(("account_name", name) for name in record.alternate_names)
    if not record.alternate_names:
        names.extend(("account_name", name) for name in record.normalized_alternate_names)
    return [(field, value) for field, value in names if value]


def _best_score_against(left_name: str, right_fields: list[tuple[str, str]], missing_reason: str) -> NameScore:
    left_variants = generate_name_variants(left_name)
    scores: list[tuple[float, str, str, str]] = []
    for field, right_name in right_fields:
        for left_variant in left_variants:
            for right_variant in generate_name_variants(right_name):
                token_score = float(fuzz.token_set_ratio(left_variant, right_variant))
                ratio_score = float(fuzz.ratio(left_variant, right_variant))
                scores.append((max(token_score, ratio_score), field, right_name, right_variant))
    if not scores:
        return NameScore(0.0, "", "", missing_reason)
    best_score, field, raw_value, variant = max(scores, key=lambda item: item[0])
    return NameScore(round(best_score, 2), field, raw_value, f"{field}:best={best_score:.1f} against '{variant}'")


def score_business_name(candidate: MatchCandidate) -> NameScore:
    return _best_score_against(candidate.record1.raw_name, _field_names(candidate.record2), "business_name:missing")


def score_legal_entity(candidate: MatchCandidate) -> NameScore:
    fields = [("owner_name", name) for name in candidate.record2.legal_entity_names]
    return _best_score_against(candidate.record1.raw_name, fields, "legal_entity:missing")


def score_name(candidate: MatchCandidate) -> tuple[float, list[str]]:
    """Backward-compatible helper returning best name evidence."""
    business = score_business_name(candidate)
    legal = score_legal_entity(candidate)
    best = business if business.score >= legal.score else legal
    return best.score, [best.reason]


def _comparable_component(left: str, right: str, weight: float, label: str, reasons: list[str]) -> tuple[float, float]:
    if not left or not right:
        reasons.append(f"address:{label}=missing_neutral")
        return 0.0, 0.0
    if left == right:
        reasons.append(f"address:{label}=match")
        return weight, weight
    reasons.append(f"address:{label}=diff")
    return 0.0, weight


def score_address_parts(left: AddressParts, right: AddressParts) -> tuple[float, list[str]]:
    reasons: list[str] = []
    matched = 0.0
    comparable = 0.0
    comparable_labels: set[str] = set()
    matched_labels: set[str] = set()
    for left_value, right_value, weight, label in [
        (left.street_number, right.street_number, 18.0, "street_number"),
        (left.street_name, right.street_name, 24.0, "street_name"),
        (left.street_type, right.street_type, 8.0, "street_type"),
        (left.city, right.city, 18.0, "city"),
        (left.postal_code5, right.postal_code5, 26.0, "zip5"),
        (left.state, right.state, 6.0, "state"),
    ]:
        add, possible = _comparable_component(left_value, right_value, weight, label, reasons)
        matched += add
        comparable += possible
        if possible:
            comparable_labels.add(label)
        if add:
            matched_labels.add(label)

    if comparable == 0:
        reasons.append("address:evidence=none")
        return 0.0, reasons

    score = (matched / comparable) * 100.0
    has_core_street = {"street_number", "street_name"}.issubset(comparable_labels)
    has_location = bool({"city", "zip5"} & comparable_labels)
    if not has_core_street or not has_location:
        score = min(score, 55.0)
        reasons.append("address:evidence=sparse_cap")
    elif {"street_number", "street_name", "city", "zip5"}.issubset(matched_labels):
        score = max(score, 96.0)
        reasons.append("address:evidence=street_city_zip5_exact")

    if left.postal_code_full and right.postal_code_full and left.postal_code_full == right.postal_code_full and left.postal_code_full != left.postal_code5:
        score = min(100.0, score + 3.0)
        reasons.append("address:full_zip=match")
        reasons.append("address:full_zip=bonus_match")
    elif left.postal_code_full or right.postal_code_full:
        reasons.append("address:full_zip=missing_or_diff_neutral")
    return round(score, 2), reasons


def score_candidate(candidate: MatchCandidate) -> MatchResult:
    business = score_business_name(candidate)
    legal = score_legal_entity(candidate)
    address_score, address_reasons = score_address_parts(candidate.record1.address, candidate.record2.address)
    best = business if business.score >= legal.score else legal
    effective_name = business.score if business.score >= 75 or address_score < 85 else max(business.score, legal.score * 0.92)
    combined_score = round((effective_name * 0.62) + (address_score * 0.38), 2)
    reasons = [
        *candidate.blocking_reasons,
        f"business_name:{business.reason}",
        f"legal_entity:{legal.reason}",
        *address_reasons,
    ]
    return MatchResult(
        id_1=candidate.record1.record_id,
        id_2=candidate.record2.record_id,
        address_score=address_score,
        business_name_score=business.score,
        legal_entity_score=legal.score,
        best_name_field=best.field,
        best_name_value=best.value,
        combined_score=combined_score,
        decision="unclassified",
        reasons=tuple(reasons),
    )
