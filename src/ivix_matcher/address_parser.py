from __future__ import annotations

from typing import Protocol

import usaddress

from .models import AddressParts
from .normalize import collapse_spaces, normalize_token, normalize_zip


class AddressParser(Protocol):
    def parse(self, address: str, *, city: str = "", postal_code: str = "", state: str = "", country: str = "") -> AddressParts:
        """Parse and normalize an address string into structured parts."""


STREET_TYPE_ALIASES = {
    "avenue": "ave",
    "ave": "ave",
    "street": "st",
    "st": "st",
    "road": "rd",
    "rd": "rd",
    "boulevard": "blvd",
    "blvd": "blvd",
    "drive": "dr",
    "dr": "dr",
    "lane": "ln",
    "ln": "ln",
    "place": "pl",
    "pl": "pl",
    "court": "ct",
    "ct": "ct",
}


def normalize_street_type(value: str) -> str:
    token = normalize_token(value)
    return STREET_TYPE_ALIASES.get(token, token)


def normalized_street(street_name: str, street_type: str) -> str:
    return collapse_spaces(" ".join(part for part in [normalize_token(street_name), normalize_street_type(street_type)] if part))


class UsAddressParser:
    """US address parser behind a small interface so other parsers can replace it later."""

    def parse(self, address: str, *, city: str = "", postal_code: str = "", state: str = "", country: str = "") -> AddressParts:
        tagged = self._tag(address)
        raw_zip = postal_code or tagged.get("ZipCode", "")
        zip_parts = normalize_zip(raw_zip)
        parsed_city = city or tagged.get("PlaceName", "")
        parsed_state = state or tagged.get("StateName", "")
        street_number = normalize_token(tagged.get("AddressNumber", ""))
        street_name = normalize_token(
            collapse_spaces(
                " ".join(
                    tagged.get(label, "")
                    for label in [
                        "StreetNamePreDirectional",
                        "StreetNamePreModifier",
                        "StreetName",
                        "StreetNamePostModifier",
                        "StreetNamePostDirectional",
                    ]
                )
            )
        )
        street_type = normalize_street_type(tagged.get("StreetNamePostType", ""))
        unit = normalize_token(collapse_spaces(" ".join([tagged.get("OccupancyType", ""), tagged.get("OccupancyIdentifier", "")])) )

        return AddressParts(
            country=normalize_token(country),
            state=normalize_token(parsed_state),
            city=normalize_token(parsed_city),
            postal_code_raw=zip_parts["raw"],
            postal_code_digits=zip_parts["digits"],
            postal_code_full=zip_parts["full"],
            postal_code5=zip_parts["zip5"],
            street_number=street_number,
            street_name=street_name,
            street_type=street_type,
            unit=unit,
            normalized_street=normalized_street(street_name, street_type),
        )

    @staticmethod
    def _tag(address: str) -> dict[str, str]:
        try:
            tagged, _address_type = usaddress.tag(address)
            return dict(tagged)
        except usaddress.RepeatedLabelError as exc:
            return dict(exc.parsed_string)