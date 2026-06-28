from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load an input CSV using the assignment-required pandas options."""
    return pd.read_csv(path, dtype=str).fillna("")


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def ensure_output_not_input(output_path: str | Path, input_paths: list[str | Path]) -> None:
    """Refuse to write an output file over any read-only input file."""
    output = _resolved(output_path)
    inputs = {_resolved(path) for path in input_paths}
    if output in inputs:
        raise ValueError(f"Refusing to overwrite input CSV: {output_path}")


def inspect_headers(dataset1: str | Path, dataset2: str | Path) -> tuple[list[str], list[str]]:
    df1 = load_csv(dataset1)
    df2 = load_csv(dataset2)
    return list(df1.columns), list(df2.columns)