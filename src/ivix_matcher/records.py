from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .address_parser import AddressParser
from .models import BusinessRecord
from .normalize import normalize_name


FULL_ADDRESS_REQUIRED_HEADERS = frozenset({"id", "address", "name"})
SPLIT_ADDRESS_REQUIRED_HEADERS = frozenset({"id", "account_name", "owner_name", "name", "street", "city", "zip"})


class UnknownDatasetFormatError(ValueError):
    """Raised when CSV headers do not match a supported input shape."""


def _row_dict(row: pd.Series) -> dict[str, str]:
    return {str(key): str(value) for key, value in row.to_dict().items()}


def _clean_names(names: Iterable[str]) -> tuple[str, ...]:
    cleaned = []
    seen = set()
    for name in names:
        value = str(name).strip()
        if value and value not in seen:
            cleaned.append(value)
            seen.add(value)
    return tuple(cleaned)


def dataset1_row_to_record(row: pd.Series, parser: AddressParser) -> BusinessRecord:
    raw = _row_dict(row)
    raw_name = raw.get("name", "")
    return BusinessRecord(
        record_id=raw.get("id", ""),
        source="dataset1",
        raw_name=raw_name,
        normalized_name=normalize_name(raw_name),
        address=parser.parse(raw.get("address", ""), country="us"),
        raw=raw,
    )


def dataset2_row_to_record(row: pd.Series, parser: AddressParser) -> BusinessRecord:
    raw = _row_dict(row)
    raw_name = raw.get("name", "") or raw.get("account_name", "")
    alternate_names = _clean_names([raw.get("account_name", "")])
    legal_names = _clean_names([raw.get("owner_name", "")])
    return BusinessRecord(
        record_id=raw.get("id", ""),
        source="dataset2",
        raw_name=raw_name,
        normalized_name=normalize_name(raw_name),
        alternate_names=alternate_names,
        normalized_alternate_names=tuple(normalize_name(name) for name in alternate_names),
        legal_entity_names=legal_names,
        normalized_legal_entity_names=tuple(normalize_name(name) for name in legal_names),
        address=parser.parse(
            raw.get("street", ""),
            city=raw.get("city", ""),
            postal_code=raw.get("zip", ""),
            country="us",
        ),
        raw=raw,
    )


def detect_record_format(columns: Iterable[str]) -> str:
    headers = set(columns)
    if SPLIT_ADDRESS_REQUIRED_HEADERS.issubset(headers):
        return "split_address"
    if FULL_ADDRESS_REQUIRED_HEADERS.issubset(headers):
        return "full_address"
    raise UnknownDatasetFormatError(
        "Unsupported CSV headers. Expected at least one of: "
        f"full-address structure {sorted(FULL_ADDRESS_REQUIRED_HEADERS)} or "
        f"split-address structure {sorted(SPLIT_ADDRESS_REQUIRED_HEADERS)}. "
        f"Actual headers: {sorted(headers)}"
    )


def dataframe_to_records(df: pd.DataFrame, parser: AddressParser) -> list[BusinessRecord]:
    record_format = detect_record_format(df.columns)
    if record_format == "full_address":
        return [dataset1_row_to_record(row, parser) for _, row in df.iterrows()]
    if record_format == "split_address":
        return [dataset2_row_to_record(row, parser) for _, row in df.iterrows()]
    raise AssertionError(f"Unexpected detected record format: {record_format}")