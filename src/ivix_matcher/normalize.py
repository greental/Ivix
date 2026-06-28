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