from __future__ import annotations

from ivix_matcher.address_parser import UsAddressParser, normalize_street_type


def test_normalize_street_type_aliases() -> None:
    assert normalize_street_type("Street") == "st"
    assert normalize_street_type("BLVD") == "blvd"


def test_usaddress_parser_parses_full_dataset1_style_address() -> None:
    parts = UsAddressParser().parse("3228 16th St, San Francisco, CA 94103", country="US")

    assert parts.country == "us"
    assert parts.state == "ca"
    assert parts.city == "san francisco"
    assert parts.postal_code_raw == "94103"
    assert parts.postal_code_digits == "94103"
    assert parts.postal_code5 == "94103"
    assert parts.street_number == "3228"
    assert parts.street_name == "16th"
    assert parts.street_type == "st"
    assert parts.normalized_street == "16th st"


def test_usaddress_parser_accepts_split_city_and_zip() -> None:
    parts = UsAddressParser().parse(
        "1515 W MARTIN LUTHER KING JR BLVD",
        city="LOS ANGELES",
        postal_code="900621743",
    )

    assert parts.city == "los angeles"
    assert parts.postal_code5 == "90062"
    assert parts.street_number == "1515"
    assert "martin luther king" in parts.street_name
    assert parts.street_type == "blvd"


def test_usaddress_parser_handles_units() -> None:
    parts = UsAddressParser().parse("10 Main Street Suite 5, Oakland, CA 94612")

    assert parts.unit == "suite 5"