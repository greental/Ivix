from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .models import AddressParts, BusinessRecord, MatchCandidate
from .config import MatchingConfig, load_config
from .normalize import generate_name_variants


MIN_NAME_TOKEN_LENGTH = 4


def _scope_variants(address: AddressParts) -> list[tuple[str, str]]:
    scopes: list[tuple[str, str]] = []
    if address.country and address.state:
        scopes.append((address.country, address.state))
    if address.state:
        scopes.append(("", address.state))
    if address.country:
        scopes.append((address.country, ""))
    scopes.append(("", ""))
    return list(dict.fromkeys(scopes))


def generate_address_keys(address: AddressParts) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Centralized address blocking keys used by both indexing and querying."""
    keys: list[tuple[str, tuple[str, ...]]] = []
    for country, state in _scope_variants(address):
        prefix = (country, state)
        if address.postal_code5 and address.street_number:
            keys.append(("zip5_street_number", (*prefix, address.postal_code5, address.street_number)))
        if address.city and address.street_number:
            keys.append(("city_street_number", (*prefix, address.city, address.street_number)))
        if address.postal_code5 and address.normalized_street:
            keys.append(("zip5_street", (*prefix, address.postal_code5, address.normalized_street)))
        if address.city and address.normalized_street:
            keys.append(("city_street", (*prefix, address.city, address.normalized_street)))
    return tuple(dict.fromkeys(keys))


def _fingerprints_from_names(names: tuple[str, ...], config: MatchingConfig | None = None) -> tuple[str, ...]:
    config = config or load_config()
    tokens: set[str] = set()
    for name in names:
        variants = generate_name_variants(name, config) or (name,)
        parts = [part for variant in variants for part in variant.split() if len(part) >= MIN_NAME_TOKEN_LENGTH and part != "and"]
        tokens.update(parts)
        if len(parts) >= 2:
            tokens.add(" ".join(sorted(parts[:3])))
    return tuple(sorted(tokens))


def generate_name_fingerprints(record: BusinessRecord, config: MatchingConfig | None = None) -> tuple[str, ...]:
    return _fingerprints_from_names(record.all_normalized_names, config)


def generate_legal_name_fingerprints(record: BusinessRecord, config: MatchingConfig | None = None) -> tuple[str, ...]:
    return _fingerprints_from_names(record.all_normalized_legal_names, config)


@dataclass
class CandidateIndex:
    address_indexes: dict[str, dict[tuple[str, ...], list[BusinessRecord]]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(list)))
    name_index: dict[str, list[BusinessRecord]] = field(default_factory=lambda: defaultdict(list))
    legal_name_index: dict[str, list[BusinessRecord]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    def build(cls, dataset2_records: list[BusinessRecord]) -> "CandidateIndex":
        index = cls()
        for record in dataset2_records:
            for key_type, key in generate_address_keys(record.address):
                index.address_indexes[key_type][key].append(record)
            for fingerprint in generate_name_fingerprints(record):
                index.name_index[fingerprint].append(record)
            for fingerprint in generate_legal_name_fingerprints(record):
                index.legal_name_index[fingerprint].append(record)
        return index

    def query(self, record: BusinessRecord) -> list[MatchCandidate]:
        found: dict[str, tuple[BusinessRecord, set[str]]] = {}
        for key_type, key in generate_address_keys(record.address):
            for candidate in self.address_indexes.get(key_type, {}).get(key, []):
                found.setdefault(candidate.record_id, (candidate, set()))[1].add(f"address:{key_type}")
        for fingerprint in generate_name_fingerprints(record):
            for candidate in self.name_index.get(fingerprint, []):
                found.setdefault(candidate.record_id, (candidate, set()))[1].add("name_fallback:business")
            for candidate in self.legal_name_index.get(fingerprint, []):
                found.setdefault(candidate.record_id, (candidate, set()))[1].add("name_fallback:owner_name")
        return [
            MatchCandidate(record1=record, record2=candidate, blocking_reasons=tuple(sorted(reasons)))
            for candidate, reasons in found.values()
        ]