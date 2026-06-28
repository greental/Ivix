from __future__ import annotations

from ivix_matcher.models import AddressParts, BusinessRecord
from ivix_matcher.normalize import normalize_name, normalize_zip


def test_normalize_name_lowercase_punctuation_suffixes_and_spaces() -> None:
    assert normalize_name("  Acme, Inc. LLC  ") == "acme"


def test_normalize_name_normalizes_ampersand_to_and() -> None:
    assert normalize_name("Grossman's Noshery & Bar") == "grossman s noshery and bar"


def test_normalize_name_removes_corporate_suffixes() -> None:
    assert normalize_name("TTVV Corp") == "ttvv"
    assert normalize_name("Example Incorporated") == "example"


def test_normalize_zip_keeps_raw_digits_full_and_zip5() -> None:
    assert normalize_zip("94103-1234") == {
        "raw": "94103-1234",
        "digits": "941031234",
        "full": "941031234",
        "zip5": "94103",
    }


def test_normalize_zip_handles_compact_zip_plus_4() -> None:
    assert normalize_zip("900621743")["zip5"] == "90062"


def test_business_record_all_normalized_names_deduplicates_blanks() -> None:
    record = BusinessRecord(
        record_id="1",
        source="dataset2",
        raw_name="Acme Inc",
        normalized_name="acme",
        address=AddressParts(),
        normalized_alternate_names=("acme", "acme market", ""),
    )

    assert record.all_normalized_names == ("acme", "acme market")