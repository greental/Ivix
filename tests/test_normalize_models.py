from __future__ import annotations

from ivix_matcher.models import AddressParts, BusinessRecord
from ivix_matcher.config import MatchingConfig, load_config
from ivix_matcher.normalize import generate_name_variants, normalize_name, normalize_zip


def config_with_name_variants(updates: dict) -> MatchingConfig:
    raw = load_config().raw.copy()
    name_variants = dict(raw["name_variants"])
    name_variants.update(updates)
    raw["name_variants"] = name_variants
    return MatchingConfig(raw=raw, path=load_config().path)


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


def test_configured_gastrobar_variant() -> None:
    variants = generate_name_variants("Asian Gastro Bar")
    assert "asian gastrobar" in variants


def test_configured_pizzeria_variant() -> None:
    variants = generate_name_variants("Avenue Pizzeria")
    assert "avenue pizza" in variants


def test_compact_space_variants_can_be_enabled_or_disabled() -> None:
    enabled = config_with_name_variants({"compact_space_variants": True})
    disabled = config_with_name_variants({"compact_space_variants": False})

    assert "culichitown" in generate_name_variants("Culichi Town", enabled)
    assert "culichitown" not in generate_name_variants("Culichi Town", disabled)


def test_max_name_variant_cap_is_respected() -> None:
    config = config_with_name_variants(
        {
            "token_replacements": {"market": ["mkt", "mercado", "shop"], "acme": ["akme", "acmee"]},
            "max_variants_per_name": 3,
        }
    )

    assert len(generate_name_variants("Acme Market", config)) <= 3