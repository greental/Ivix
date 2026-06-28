from __future__ import annotations

from ivix_matcher.models import AddressParts, BusinessRecord, MatchCandidate
from ivix_matcher.scoring import score_address_parts, score_business_name, score_candidate, score_name


def rec(record_id: str, name: str, address: AddressParts, alternates: tuple[str, ...] = ()) -> BusinessRecord:
    return BusinessRecord(
        record_id=record_id,
        source="x",
        raw_name=name,
        normalized_name=name,
        address=address,
        normalized_alternate_names=alternates,
    )


def test_score_name_uses_best_alternate_name() -> None:
    candidate = MatchCandidate(
        rec("1", "grossman noshery bar", AddressParts()),
        rec("2", "unrelated", AddressParts(), alternates=("grossman noshery and bar",)),
    )

    score, reasons = score_name(candidate)

    assert score >= 90
    assert "grossman noshery and bar" in reasons[0]


def test_score_address_parts_scores_components_separately() -> None:
    left = AddressParts(state="ca", city="oakland", postal_code5="94612", postal_code_full="946121234", street_number="1", street_name="main", street_type="st")
    right = AddressParts(state="ca", city="oakland", postal_code5="94612", postal_code_full="946121234", street_number="1", street_name="main", street_type="st")

    score, reasons = score_address_parts(left, right)

    assert score == 100
    assert "address:street_number=match" in reasons
    assert "address:full_zip=match" in reasons


def test_score_address_parts_does_not_award_missing_state() -> None:
    left = AddressParts(state="ca", city="oakland", postal_code5="94612", street_number="1", street_name="main", street_type="st")
    right = AddressParts(city="oakland", postal_code5="94612", street_number="1", street_name="main", street_type="st")

    score, reasons = score_address_parts(left, right)

    assert score == 100
    assert "address:state=missing_neutral" in reasons


def test_score_candidate_combines_name_address_and_reasons() -> None:
    addr = AddressParts(city="oakland", postal_code5="94612", street_number="1", street_name="main", street_type="st")
    result = score_candidate(MatchCandidate(rec("1", "acme market", addr), rec("2", "acme market", addr), ("name_fallback:business",)))

    assert result.id_1 == "1"
    assert result.id_2 == "2"
    assert result.name_score == 100
    assert result.combined_score > 90
    assert "name_fallback:business" in result.reasons


def test_missing_state_and_full_zip_do_not_penalize_exact_address() -> None:
    left = AddressParts(city="oakland", postal_code5="94612", postal_code_full="946121234", street_number="1", street_name="main", street_type="st")
    right = AddressParts(city="oakland", postal_code5="94612", street_number="1", street_name="main", street_type="st")
    score, reasons = score_address_parts(left, right)
    assert score >= 96
    assert "address:full_zip=missing_or_diff_neutral" in reasons


def test_street_number_alone_is_sparse_not_strong() -> None:
    score, reasons = score_address_parts(AddressParts(street_number="1"), AddressParts(street_number="1"))
    assert score == 55
    assert "address:evidence=sparse_cap" in reasons


def test_compact_name_matching_culichi_town() -> None:
    candidate = MatchCandidate(rec("1", "culichi town", AddressParts()), rec("2", "CULICHITOWN BELL, INC.", AddressParts()))
    assert score_business_name(candidate).score >= 90


def test_spaced_initials_match() -> None:
    candidate = MatchCandidate(rec("1", "The CB Stop", AddressParts()), rec("2", "THE C B STOP, INC.", AddressParts()))
    assert score_business_name(candidate).score >= 90


def test_business_word_variants_match_pizzeria_pizza() -> None:
    candidate = MatchCandidate(rec("1", "Avenue Pizzeria", AddressParts()), rec("2", "AVENUE PIZZA INC", AddressParts()))
    assert score_business_name(candidate).score >= 90


def test_gastro_bar_gastrobar_variant() -> None:
    candidate = MatchCandidate(rec("1", "Z Town - Asian Gastro Bar", AddressParts()), rec("2", "Z TOWN - ASIAN GASTROBAR", AddressParts()))
    assert score_business_name(candidate).score >= 90