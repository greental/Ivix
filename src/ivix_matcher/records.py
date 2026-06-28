from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .address_parser import AddressParser
from .config import MatchingConfig, load_config
from .models import BusinessRecord
from .normalize import normalize_name


FULL_ADDRESS_REQUIRED_KEYS = ("id", "business_name", "full_address")
SPLIT_ADDRESS_REQUIRED_KEYS = ("id", "business_name", "street", "city", "postal_code")


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


def _configured_fields(config: MatchingConfig, schema_name: str, keys: tuple[str, ...]) -> set[str]:
    schema = config.schemas[schema_name]
    return {schema[key] for key in keys if schema.get(key)}


def _configured_list_fields(config: MatchingConfig, schema_name: str, key: str) -> list[str]:
    value = config.schemas[schema_name].get(key, [])
    return list(value) if isinstance(value, list) else []


def _full_address_required_headers(config: MatchingConfig) -> set[str]:
    return _configured_fields(config, "full_address", FULL_ADDRESS_REQUIRED_KEYS)


def _split_address_required_headers(config: MatchingConfig) -> set[str]:
    return _configured_fields(config, "split_address", SPLIT_ADDRESS_REQUIRED_KEYS)


def _schema(config: MatchingConfig, name: str) -> dict[str, object]:
    return config.schemas[name]


def dataset1_row_to_record(row: pd.Series, parser: AddressParser, config: MatchingConfig | None = None) -> BusinessRecord:
    config = config or load_config()
    schema = _schema(config, "full_address")
    raw = _row_dict(row)
    raw_name = raw.get(str(schema["business_name"]), "")
    return BusinessRecord(
        record_id=raw.get(str(schema["id"]), ""),
        source="dataset1",
        raw_name=raw_name,
        normalized_name=normalize_name(raw_name),
        address=parser.parse(raw.get(str(schema["full_address"]), ""), country=str(schema.get("country_default", ""))),
        raw=raw,
    )


def dataset2_row_to_record(row: pd.Series, parser: AddressParser, config: MatchingConfig | None = None) -> BusinessRecord:
    config = config or load_config()
    schema = _schema(config, "split_address")
    raw = _row_dict(row)
    alternate_fields = _configured_list_fields(config, "split_address", "alternate_business_names")
    legal_fields = _configured_list_fields(config, "split_address", "legal_entity_names")
    alternate_names = _clean_names(raw.get(field, "") for field in alternate_fields)
    legal_names = _clean_names(raw.get(field, "") for field in legal_fields)
    raw_name = raw.get(str(schema["business_name"]), "") or (alternate_names[0] if alternate_names else "")
    return BusinessRecord(
        record_id=raw.get(str(schema["id"]), ""),
        source="dataset2",
        raw_name=raw_name,
        normalized_name=normalize_name(raw_name),
        alternate_names=alternate_names,
        normalized_alternate_names=tuple(normalize_name(name) for name in alternate_names),
        legal_entity_names=legal_names,
        normalized_legal_entity_names=tuple(normalize_name(name) for name in legal_names),
        address=parser.parse(
            raw.get(str(schema["street"]), ""),
            city=raw.get(str(schema["city"]), ""),
            postal_code=raw.get(str(schema["postal_code"]), ""),
            country=str(schema.get("country_default", "")),
        ),
        raw=raw,
    )


def detect_record_format(columns: Iterable[str], config: MatchingConfig | None = None) -> str:
    config = config or load_config()
    formats = detect_supported_record_formats(columns, config)
    if "split_address" in formats:
        return "split_address"
    if "full_address" in formats:
        return "full_address"
    headers = set(columns)
    full_required = _full_address_required_headers(config)
    split_required = _split_address_required_headers(config)
    raise UnknownDatasetFormatError(
        "Unsupported CSV headers. Expected at least one of: "
        f"full-address structure {sorted(full_required)} or "
        f"split-address structure {sorted(split_required)}. "
        f"Actual headers: {sorted(headers)}"
    )


def detect_supported_record_formats(columns: Iterable[str], config: MatchingConfig | None = None) -> set[str]:
    config = config or load_config()
    headers = set(columns)
    formats: set[str] = set()
    if _full_address_required_headers(config).issubset(headers):
        formats.add("full_address")
    if _split_address_required_headers(config).issubset(headers):
        formats.add("split_address")
    return formats


def _dataframe_to_records_as(df: pd.DataFrame, parser: AddressParser, record_format: str, config: MatchingConfig) -> list[BusinessRecord]:
    if record_format == "full_address":
        return [dataset1_row_to_record(row, parser, config) for _, row in df.iterrows()]
    if record_format == "split_address":
        return [dataset2_row_to_record(row, parser, config) for _, row in df.iterrows()]
    raise AssertionError(f"Unexpected record format: {record_format}")


def dataframe_to_records(df: pd.DataFrame, parser: AddressParser, config: MatchingConfig | None = None) -> list[BusinessRecord]:
    config = config or load_config()
    record_format = detect_record_format(df.columns, config)
    return _dataframe_to_records_as(df, parser, record_format, config)


def dataframes_to_query_and_index_records(
    first: pd.DataFrame,
    second: pd.DataFrame,
    parser: AddressParser,
    config: MatchingConfig | None = None,
) -> tuple[list[BusinessRecord], list[BusinessRecord]]:
    """Return (query/full-address records, index/split-address records) by headers.

    CLI argument order is intentionally irrelevant. If both files support both
    formats, the first is used as query and the second as index deterministically.
    """
    config = config or load_config()
    first_formats = detect_supported_record_formats(first.columns, config)
    second_formats = detect_supported_record_formats(second.columns, config)

    if "full_address" in first_formats and "split_address" in second_formats:
        return _dataframe_to_records_as(first, parser, "full_address", config), _dataframe_to_records_as(second, parser, "split_address", config)
    if "full_address" in second_formats and "split_address" in first_formats:
        return _dataframe_to_records_as(second, parser, "full_address", config), _dataframe_to_records_as(first, parser, "split_address", config)

    full_required = _full_address_required_headers(config)
    split_required = _split_address_required_headers(config)

    raise UnknownDatasetFormatError(
        "Could not assign query/index roles from CSV headers. Need one input that supports "
        f"full-address structure {sorted(full_required)} and one input that supports "
        f"split-address structure {sorted(split_required)}. "
        f"First headers: {sorted(set(first.columns))}; second headers: {sorted(set(second.columns))}"
    )