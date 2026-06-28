from __future__ import annotations

from ivix_matcher.models import AddressParts, BusinessRecord
from ivix_matcher.candidates import CandidateIndex, generate_address_keys, generate_name_fingerprints
from ivix_matcher.config import MatchingConfig, load_config


def config_with_blocking(updates: dict) -> MatchingConfig:
    raw = load_config().raw.copy()
    blocking = dict(raw["blocking"])
    blocking.update(updates)
    raw["blocking"] = blocking
    return MatchingConfig(raw=raw, path=load_config().path)


def record(record_id: str, name: str, address: AddressParts) -> BusinessRecord:
    return BusinessRecord(record_id=record_id, source="x", raw_name=name, normalized_name=name, address=address)


def test_generate_address_keys_default_has_no_country_state_scope() -> None:
    address = AddressParts(country="us", state="ca", city="oakland", postal_code5="94612", street_number="1", normalized_street="main st")

    keys = generate_address_keys(address)

    assert ("postal_code5+street_number", ("94612", "1")) in keys
    assert all(key[1][0] != "us" for key in keys)


def test_generate_address_keys_can_use_country_state_scope_from_config() -> None:
    config = config_with_blocking({"scope_fields": ["country", "state"], "fallback_scopes": True})
    address = AddressParts(country="us", state="ca", city="oakland", postal_code5="94612", street_number="1", normalized_street="main st")

    keys = generate_address_keys(address, config)

    assert ("postal_code5+street_number", ("us", "ca", "94612", "1")) in keys
    assert ("postal_code5+street_number", ("ca", "94612", "1")) in keys
    assert ("postal_code5+street_number", ("us", "94612", "1")) in keys
    assert ("postal_code5+street_number", ("94612", "1")) in keys


def test_candidate_index_queries_dataset2_address_index_without_scan() -> None:
    d2 = record("2", "other", AddressParts(country="us", city="oakland", postal_code5="94612", street_number="1", normalized_street="main st"))
    d1 = record("1", "x", AddressParts(country="us", state="ca", city="oakland", postal_code5="94612", street_number="1", normalized_street="main st"))

    candidates = CandidateIndex.build([d2]).query(d1)

    assert [candidate.record2.record_id for candidate in candidates] == ["2"]
    assert any(reason.startswith("blocking:address:") for reason in candidates[0].blocking_reasons)


def test_name_fingerprint_fallback_finds_moved_business() -> None:
    d2 = record("2", "grossman noshery", AddressParts(city="los angeles", street_number="9"))
    d1 = record("1", "grossman noshery", AddressParts(city="san francisco", street_number="1"))

    candidates = CandidateIndex.build([d2]).query(d1)

    assert [candidate.record2.record_id for candidate in candidates] == ["2"]
    assert "blocking:business_name_fingerprint" in candidates[0].blocking_reasons


def test_legal_entity_fingerprint_fallback_finds_candidate() -> None:
    d2 = BusinessRecord(
        record_id="2",
        source="x",
        raw_name="unrelated",
        normalized_name="unrelated",
        address=AddressParts(city="los angeles", street_number="9"),
        legal_entity_names=("Green Valley Holdings LLC",),
        normalized_legal_entity_names=("green valley holdings",),
    )
    d1 = record("1", "Green Valley Holdings", AddressParts(city="san francisco", street_number="1"))

    candidates = CandidateIndex.build([d2]).query(d1)

    assert [candidate.record2.record_id for candidate in candidates] == ["2"]
    assert "blocking:legal_entity_fingerprint" in candidates[0].blocking_reasons


def test_candidate_query_deduplicates_records_found_by_multiple_keys() -> None:
    addr = AddressParts(country="us", city="oakland", postal_code5="94612", street_number="1", normalized_street="main st")
    d2 = record("2", "acme market", addr)
    d1 = record("1", "acme market", addr)

    candidates = CandidateIndex.build([d2]).query(d1)

    assert len(candidates) == 1
    assert "blocking:business_name_fingerprint" in candidates[0].blocking_reasons
    assert any(reason.startswith("blocking:address:") for reason in candidates[0].blocking_reasons)


def test_generate_name_fingerprints_uses_strong_tokens() -> None:
    rec = record("1", "acme market and bar", AddressParts())
    assert "market" in generate_name_fingerprints(rec)
    assert "bar" not in generate_name_fingerprints(rec)