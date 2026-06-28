from __future__ import annotations

from ivix_matcher.models import AddressParts, BusinessRecord
from ivix_matcher.candidates import CandidateIndex, generate_address_keys, generate_name_fingerprints


def record(record_id: str, name: str, address: AddressParts) -> BusinessRecord:
    return BusinessRecord(record_id=record_id, source="x", raw_name=name, normalized_name=name, address=address)


def test_generate_address_keys_includes_strict_and_relaxed_country_state_keys() -> None:
    address = AddressParts(country="us", state="ca", city="oakland", postal_code5="94612", street_number="1", normalized_street="main st")

    keys = generate_address_keys(address)

    assert ("zip5_street_number", ("us", "ca", "94612", "1")) in keys
    assert ("zip5_street_number", ("", "ca", "94612", "1")) in keys
    assert ("zip5_street_number", ("us", "", "94612", "1")) in keys
    assert ("zip5_street_number", ("", "", "94612", "1")) in keys


def test_candidate_index_queries_dataset2_address_index_without_scan() -> None:
    d2 = record("2", "other", AddressParts(country="us", city="oakland", postal_code5="94612", street_number="1", normalized_street="main st"))
    d1 = record("1", "x", AddressParts(country="us", state="ca", city="oakland", postal_code5="94612", street_number="1", normalized_street="main st"))

    candidates = CandidateIndex.build([d2]).query(d1)

    assert [candidate.record2.record_id for candidate in candidates] == ["2"]
    assert any(reason.startswith("address:") for reason in candidates[0].blocking_reasons)


def test_name_fingerprint_fallback_finds_moved_business() -> None:
    d2 = record("2", "grossman noshery", AddressParts(city="los angeles", street_number="9"))
    d1 = record("1", "grossman noshery", AddressParts(city="san francisco", street_number="1"))

    candidates = CandidateIndex.build([d2]).query(d1)

    assert [candidate.record2.record_id for candidate in candidates] == ["2"]
    assert "name:fingerprint" in candidates[0].blocking_reasons


def test_candidate_query_deduplicates_records_found_by_multiple_keys() -> None:
    addr = AddressParts(country="us", city="oakland", postal_code5="94612", street_number="1", normalized_street="main st")
    d2 = record("2", "acme market", addr)
    d1 = record("1", "acme market", addr)

    candidates = CandidateIndex.build([d2]).query(d1)

    assert len(candidates) == 1
    assert "name:fingerprint" in candidates[0].blocking_reasons


def test_generate_name_fingerprints_uses_strong_tokens() -> None:
    rec = record("1", "acme market and bar", AddressParts())
    assert "market" in generate_name_fingerprints(rec)
    assert "bar" not in generate_name_fingerprints(rec)