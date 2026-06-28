from __future__ import annotations

import re
import string


BUSINESS_SUFFIXES = {
    "co",
    "company",
    "corp",
    "corporation",
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
    "lp",
    "llp",
    "pllc",
}

BUSINESS_WORD_VARIANTS = {
    "pizzeria": ("pizza",),
    "pizza": ("pizzeria",),
    "gastrobar": ("gastro bar",),
}


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_name(name: str) -> str:
    """Normalize business names for deterministic, explainable matching."""
    value = name.lower().replace("&", " and ")
    value = value.translate(str.maketrans({char: " " for char in string.punctuation}))
    tokens = [token for token in collapse_spaces(value).split(" ") if token]
    tokens = ["and" if token == "&" else token for token in tokens]
    tokens = [token for token in tokens if token not in BUSINESS_SUFFIXES]
    return collapse_spaces(" ".join(tokens))


def compact_name(name: str) -> str:
    return normalize_name(name).replace(" ", "")


def _with_business_word_variants(normalized: str) -> set[str]:
    variants = {normalized}
    tokens = normalized.split()
    for index, token in enumerate(tokens):
        for replacement in BUSINESS_WORD_VARIANTS.get(token, ()): 
            replaced = tokens.copy()
            replaced[index:index + 1] = replacement.split()
            variants.add(collapse_spaces(" ".join(replaced)))
    if "gastro bar" in normalized:
        variants.add(normalized.replace("gastro bar", "gastrobar"))
    return variants


def generate_name_variants(name: str) -> tuple[str, ...]:
    """Generate deterministic variants for business-name comparison/indexing."""
    normalized = normalize_name(name)
    if not normalized:
        return ()
    variants = _with_business_word_variants(normalized)
    for variant in list(variants):
        variants.add(variant.replace(" ", ""))
        tokens = variant.split()
        if len(tokens) > 1 and all(len(token) == 1 for token in tokens[:2]):
            variants.add("".join(tokens[:2]) + (" " + " ".join(tokens[2:]) if len(tokens) > 2 else ""))
    return tuple(sorted(v for v in variants if v))


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