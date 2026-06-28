from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .models import AddressParts, BusinessRecord, MatchCandidate
from .config import MatchingConfig, load_config
from .normalize import generate_name_variants


MIN_NAME_TOKEN_LENGTH = 4


def _address_value(address: AddressParts, field_name: str) -> str:
    if not hasattr(address, field_name):
        raise ValueError(f"Unknown address field in blocking config: {field_name}")
    return str(getattr(address, field_name))


def _scope_variants(address: AddressParts, config: MatchingConfig) -> list[tuple[str, ...]]:
    scope_fields = [str(field) for field in config.blocking.get("scope_fields", [])]
    if not scope_fields:
        return [()]
    full_scope = tuple(_address_value(address, field) for field in scope_fields)
    scopes = [full_scope]
    if config.blocking.get("fallback_scopes", True):
        for index in range(len(scope_fields)):
            scopes.append(tuple(value for i, value in enumerate(full_scope) if i != index))
        scopes.append(())
    return [scope for scope in dict.fromkeys(scopes) if all(scope)] or [()]


def generate_address_keys(address: AddressParts, config: MatchingConfig | None = None) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Centralized address blocking keys used by both indexing and querying."""
    config = config or load_config()
    keys: list[tuple[str, tuple[str, ...]]] = []
    for scope in _scope_variants(address, config):
        for fields in config.blocking.get("address_keys", []):
            values = tuple(_address_value(address, str(field)) for field in fields)
            if all(values):
                label = "+".join(str(field) for field in fields)
                keys.append((label, (*scope, *values)))
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
    config: MatchingConfig = field(default_factory=load_config)

    @classmethod
    def build(cls, dataset2_records: list[BusinessRecord], config: MatchingConfig | None = None) -> "CandidateIndex":
        index = cls(config=config or load_config())
        for record in dataset2_records:
            for key_type, key in generate_address_keys(record.address, index.config):
                index.address_indexes[key_type][key].append(record)
            for fingerprint in generate_name_fingerprints(record, index.config):
                index.name_index[fingerprint].append(record)
            for fingerprint in generate_legal_name_fingerprints(record, index.config):
                index.legal_name_index[fingerprint].append(record)
        return index

    def query(self, record: BusinessRecord) -> list[MatchCandidate]:
        found: dict[str, tuple[BusinessRecord, set[str]]] = {}
        for key_type, key in generate_address_keys(record.address, self.config):
            for candidate in self.address_indexes.get(key_type, {}).get(key, []):
                found.setdefault(candidate.record_id, (candidate, set()))[1].add(f"blocking:address:{key_type}")
        for fingerprint in generate_name_fingerprints(record, self.config):
            for candidate in self.name_index.get(fingerprint, []):
                found.setdefault(candidate.record_id, (candidate, set()))[1].add("blocking:business_name_fingerprint")
            for candidate in self.legal_name_index.get(fingerprint, []):
                found.setdefault(candidate.record_id, (candidate, set()))[1].add("blocking:legal_entity_fingerprint")
        return [
            MatchCandidate(record1=record, record2=candidate, blocking_reasons=tuple(sorted(reasons)))
            for candidate, reasons in found.values()
        ]