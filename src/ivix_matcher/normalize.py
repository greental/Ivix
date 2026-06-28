from __future__ import annotations

import re
import string

from .config import MatchingConfig, load_config


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _legal_suffixes(config: MatchingConfig | None) -> set[str]:
    config = config or load_config()
    return {str(suffix) for suffix in config.name_variants.get("legal_suffixes", [])}


def normalize_name(name: str, config: MatchingConfig | None = None) -> str:
    """Normalize business names for deterministic, explainable matching."""
    value = name.lower().replace("&", " and ")
    value = value.translate(str.maketrans({char: " " for char in string.punctuation}))
    tokens = [token for token in collapse_spaces(value).split(" ") if token]
    tokens = ["and" if token == "&" else token for token in tokens]
    suffixes = _legal_suffixes(config)
    tokens = [token for token in tokens if token not in suffixes]
    return collapse_spaces(" ".join(tokens))


def compact_name(name: str, config: MatchingConfig | None = None) -> str:
    return normalize_name(name, config).replace(" ", "")


def _cap_variants(variants: set[str], max_variants: int) -> set[str]:
    return set(sorted(v for v in variants if v)[:max_variants])


def apply_configured_name_replacements(normalized: str, config: MatchingConfig | None = None) -> set[str]:
    config = config or load_config()
    max_variants = int(config.name_variants.get("max_variants_per_name", 20))
    replacements = config.name_variants.get("token_replacements", {})
    variants = {normalized}
    for source, targets in replacements.items():
        source_text = normalize_name(str(source), config)
        if not source_text or source_text not in normalized:
            continue
        for target in targets:
            target_text = normalize_name(str(target), config)
            if target_text:
                variants.add(collapse_spaces(normalized.replace(source_text, target_text)))
                if len(variants) >= max_variants:
                    return _cap_variants(variants, max_variants)
    return _cap_variants(variants, max_variants)


def add_compact_space_variants(variants: set[str], max_variants: int) -> set[str]:
    expanded = set(variants)
    for variant in sorted(variants):
        expanded.add(variant.replace(" ", ""))
        if len(expanded) >= max_variants:
            break
    return _cap_variants(expanded, max_variants)


def add_initial_pair_compaction(variants: set[str], max_variants: int) -> set[str]:
    expanded = set(variants)
    for variant in sorted(variants):
        tokens = variant.split()
        if len(tokens) > 1 and all(len(token) == 1 for token in tokens[:2]):
            expanded.add("".join(tokens[:2]) + (" " + " ".join(tokens[2:]) if len(tokens) > 2 else ""))
        if len(expanded) >= max_variants:
            break
    return _cap_variants(expanded, max_variants)


def generate_name_variants(name: str, config: MatchingConfig | None = None) -> tuple[str, ...]:
    """Generate deterministic variants for business-name comparison/indexing."""
    config = config or load_config()
    normalized = normalize_name(name, config)
    if not normalized:
        return ()
    max_variants = int(config.name_variants.get("max_variants_per_name", 20))
    variants = apply_configured_name_replacements(normalized, config)
    if config.name_variants.get("compact_space_variants", True):
        variants = add_compact_space_variants(variants, max_variants)
    if config.name_variants.get("initial_pair_compaction", True):
        variants = add_initial_pair_compaction(variants, max_variants)
    return tuple(sorted(v for v in variants if v)[:max_variants])


def normalize_zip(zip_code: str) -> dict[str, str]:
    """Return raw, digits-only, full digits, and ZIP5 forms."""
    raw = zip_code.strip()
    digits = re.sub(r"\D", "", raw)
    return {
        "raw": raw,
        "digits": digits,
        "full": digits,
        "zip5": digits[:5] if len(digits) >= 5 else digits,
    }


def normalize_token(value: str) -> str:
    value = value.lower()
    value = value.translate(str.maketrans({char: " " for char in string.punctuation}))
    return collapse_spaces(value)