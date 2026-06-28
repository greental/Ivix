from __future__ import annotations

from ivix_matcher.decision import choose_best_result, classify_result, no_candidate_result, resolve_one_to_one
from ivix_matcher.models import AddressParts, BusinessRecord, MatchResult


def result(id_1: str, id_2: str, name: float, address: float, combined: float | None = None) -> MatchResult:
    return MatchResult(id_1, id_2, address, name, 0.0, "name", "", combined if combined is not None else (name * 0.62 + address * 0.38), "unclassified", ())


def test_strong_name_weak_address_is_match_for_moved_business() -> None:
    classified = classify_result(result("1", "2", 96, 20))
    assert classified.decision == "match"
    assert "decision:strong_business_name_weak_address_moved_business_allowed" in classified.reasons


def test_owner_name_with_strong_address_can_match() -> None:
    classified = classify_result(MatchResult("1", "2", 96, 20, 98, "owner_name", "T D Oil & Gas LLC", 90, "unclassified", ()))
    assert classified.decision == "match"
    assert "matched by legal entity/owner_name + strong address" in classified.reasons


def test_owner_name_with_weak_address_stays_review() -> None:
    classified = classify_result(MatchResult("1", "2", 40, 20, 98, "owner_name", "T D Oil & Gas LLC", 60, "unclassified", ()))
    assert classified.decision == "review"
    assert "decision:strong_legal_entity_weak_address_review" in classified.reasons


def test_strong_address_weak_name_is_review_not_match() -> None:
    classified = classify_result(result("1", "2", 50, 95))
    assert classified.decision == "review"


def test_weak_name_weak_address_is_best_candidate_below_threshold() -> None:
    classified = classify_result(result("1", "2", 55, 30))
    assert classified.decision == "best_candidate_below_threshold"


def test_choose_best_result_keeps_highest_scoring_even_below_threshold() -> None:
    best = choose_best_result([result("1", "2", 40, 30, 35), result("1", "3", 60, 40, 52)])
    assert best.id_2 == "3"
    assert best.decision == "best_candidate_below_threshold"


def test_no_candidate_result() -> None:
    record = BusinessRecord("1", "dataset1", "", "", AddressParts())
    res = no_candidate_result(record)
    assert res.id_1 == "1"
    assert res.id_2 == ""
    assert res.decision == "no_candidate"


def test_resolve_one_to_one_prefers_combined_then_name_score() -> None:
    resolved = resolve_one_to_one([
        result("a", "x", 98, 80, 91),
        result("b", "x", 95, 90, 91),
        result("c", "y", 80, 80, 80),
    ])

    assert [(r.id_1, r.id_2) for r in resolved] == [("a", "x"), ("b", ""), ("c", "y")]
    assert "decision:conflict_lost_dataset2=x" in resolved[1].reasons