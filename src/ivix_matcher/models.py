from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AddressParts:
    country: str = ""
    state: str = ""
    city: str = ""
    postal_code_raw: str = ""
    postal_code_digits: str = ""
    postal_code_full: str = ""
    postal_code5: str = ""
    street_number: str = ""
    street_name: str = ""
    street_type: str = ""
    unit: str = ""
    normalized_street: str = ""


@dataclass(frozen=True)
class BusinessRecord:
    record_id: str
    source: str
    raw_name: str
    normalized_name: str
    address: AddressParts
    alternate_names: tuple[str, ...] = field(default_factory=tuple)
    normalized_alternate_names: tuple[str, ...] = field(default_factory=tuple)
    legal_entity_names: tuple[str, ...] = field(default_factory=tuple)
    normalized_legal_entity_names: tuple[str, ...] = field(default_factory=tuple)
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def all_normalized_names(self) -> tuple[str, ...]:
        names = (self.normalized_name, *self.normalized_alternate_names)
        return tuple(dict.fromkeys(name for name in names if name))

    @property
    def all_normalized_legal_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(name for name in self.normalized_legal_entity_names if name))


@dataclass(frozen=True)
class MatchCandidate:
    record1: BusinessRecord
    record2: BusinessRecord
    blocking_reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MatchResult:
    id_1: str
    id_2: str
    address_score: float
    business_name_score: float
    legal_entity_score: float
    best_name_field: str
    best_name_value: str
    combined_score: float
    decision: str
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def name_score(self) -> float:
        """Backward-compatible name score: best business/legal evidence."""
        return max(self.business_name_score, self.legal_entity_score)