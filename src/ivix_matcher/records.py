from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .address_parser import AddressParser
from .models import BusinessRecord
from .normalize import normalize_name


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
    return BusinessRecord(
        record_id=raw.get("id", ""),
        source="dataset2",
        raw_name=raw_name,
        normalized_name=normalize_name(raw_name),
        alternate_names=alternate_names,
        normalized_alternate_names=tuple(normalize_name(name) for name in alternate_names),
        address=parser.parse(
            raw.get("street", ""),
            city=raw.get("city", ""),
            postal_code=raw.get("zip", ""),
            country="us",
        ),
        raw=raw,
    )


def dataframe_to_records(df: pd.DataFrame, dataset: str, parser: AddressParser) -> list[BusinessRecord]:
    if dataset == "dataset1":
        return [dataset1_row_to_record(row, parser) for _, row in df.iterrows()]
    if dataset == "dataset2":
        return [dataset2_row_to_record(row, parser) for _, row in df.iterrows()]
    raise ValueError(f"Unknown dataset: {dataset}")