from __future__ import annotations

from pathlib import Path

import pandas as pd

from .io import ensure_output_not_input
from .models import MatchResult


def write_matches(results: list[MatchResult], output_path: str | Path, input_paths: list[str | Path]) -> None:
    ensure_output_not_input(output_path, input_paths)
    rows = [{"id_1": result.id_1, "id_2": result.id_2} for result in results if result.id_2 and result.decision == "match"]
    pd.DataFrame(rows, columns=["id_1", "id_2"]).to_csv(output_path, index=False)


def write_selected_candidates(results: list[MatchResult], output_path: str | Path, input_paths: list[str | Path]) -> None:
    write_debug(results, output_path, input_paths)


def write_debug(results: list[MatchResult], output_path: str | Path, input_paths: list[str | Path]) -> None:
    ensure_output_not_input(output_path, input_paths)
    rows = [
        {
            "id_1": result.id_1,
            "id_2": result.id_2,
            "address_score": result.address_score,
            "business_name_score": result.business_name_score,
            "legal_entity_score": result.legal_entity_score,
            "best_name_field": result.best_name_field,
            "best_name_value": result.best_name_value,
            "combined_score": result.combined_score,
            "decision": result.decision,
            "reasons": "; ".join(result.reasons),
        }
        for result in results
    ]
    pd.DataFrame(
        rows,
        columns=["id_1", "id_2", "address_score", "business_name_score", "legal_entity_score", "best_name_field", "best_name_value", "combined_score", "decision", "reasons"],
    ).to_csv(output_path, index=False)