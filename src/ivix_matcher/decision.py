from __future__ import annotations

from dataclasses import replace

from .config import ConfigError, MatchingConfig, load_config
from .models import BusinessRecord, MatchResult


KNOWN_RULE_FIELDS = {"business_name_score", "legal_entity_score", "address_score", "combined_score"}
KNOWN_OPERATORS = {"gte", "gt", "lte", "lt", "eq"}


def _split_condition(condition_key: str) -> tuple[str, str]:
    for operator in sorted(KNOWN_OPERATORS, key=len, reverse=True):
        suffix = f"_{operator}"
        if condition_key.endswith(suffix):
            field = condition_key[: -len(suffix)]
            if field not in KNOWN_RULE_FIELDS:
                raise ConfigError(f"Unknown decision rule field: {field}")
            return field, operator
    raise ConfigError(f"Unknown decision rule operator in condition: {condition_key}")


def _condition_matches(actual: float, operator: str, expected: float) -> bool:
    if operator == "gte":
        return actual >= expected
    if operator == "gt":
        return actual > expected
    if operator == "lte":
        return actual <= expected
    if operator == "lt":
        return actual < expected
    if operator == "eq":
        return actual == expected
    raise ConfigError(f"Unknown decision rule operator: {operator}")


def _rule_matches(result: MatchResult, rule: dict) -> bool:
    for key, expected in rule["conditions"].items():
        field, operator = _split_condition(str(key))
        if not _condition_matches(float(getattr(result, field)), operator, float(expected)):
            return False
    return True


def classify_result(result: MatchResult, config: MatchingConfig | None = None) -> MatchResult:
    """Apply deterministic decision rules to one scored candidate."""
    config = config or load_config()
    reasons = list(result.reasons)
    for rule in config.decision_rules:
        if _rule_matches(result, rule):
            decision = str(rule["decision"])
            reasons.append(f"decision_rule:{rule['name']}")
            if rule.get("reason"):
                reasons.append(str(rule["reason"]))
            return replace(result, decision=decision, reasons=tuple(reasons))

    decision = config.default_decision
    reasons.append(f"decision_rule:default:{decision}")

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


def choose_best_result(results: list[MatchResult], record: BusinessRecord | None = None, config: MatchingConfig | None = None) -> MatchResult:
    if not results:
        if record is None:
            raise ValueError("record is required when no candidate results exist")
        return no_candidate_result(record)
    return classify_result(max(results, key=lambda r: (r.combined_score, r.business_name_score, r.legal_entity_score, r.address_score)), config)


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