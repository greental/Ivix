from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ivix_matcher.cli import main
from ivix_matcher.matching import match_records
from ivix_matcher.models import AddressParts, BusinessRecord, MatchResult
from ivix_matcher.output import write_debug, write_matches


def rec(record_id: str, name: str, address: AddressParts) -> BusinessRecord:
    return BusinessRecord(record_id=record_id, source="x", raw_name=name, normalized_name=name, address=address)


def test_match_records_returns_no_candidate_for_records_without_candidates() -> None:
    results = match_records([rec("1", "abc", AddressParts())], [])
    assert len(results) == 1
    assert results[0].decision == "no_candidate"


def test_match_records_preserves_dataset1_rows_after_conflict_resolution() -> None:
    addr = AddressParts(city="oakland", postal_code5="94612", street_number="1", street_name="main", street_type="st", normalized_street="main st")
    d1 = [rec("1", "acme market", addr), rec("2", "acme market", addr)]
    d2 = [rec("x", "acme market", addr)]

    results = match_records(d1, d2)

    assert len(results) == 2
    assert sum(1 for result in results if result.id_2 == "x") == 1
    assert sum(1 for result in results if result.id_2 == "") == 1


def test_write_matches_and_debug_outputs_expected_columns(tmp_path: Path) -> None:
    result = MatchResult("1", "2", 80, 95, 89.3, "match", ("why",))
    matches = tmp_path / "matches.csv"
    debug = tmp_path / "debug.csv"

    write_matches([result], matches, [])
    write_debug([result], debug, [])

    assert list(pd.read_csv(matches).columns) == ["id_1", "id_2"]
    assert list(pd.read_csv(debug).columns) == ["id_1", "id_2", "address_score", "name_score", "combined_score", "decision", "reasons"]


def test_write_outputs_refuse_to_overwrite_inputs(tmp_path: Path) -> None:
    input_path = tmp_path / "dataset.csv"
    input_path.write_text("id\n1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        write_matches([], input_path, [input_path])
    with pytest.raises(ValueError):
        write_debug([], input_path, [input_path])


def test_cli_runs_end_to_end_and_writes_outputs(tmp_path: Path) -> None:
    d1 = tmp_path / "d1.csv"
    d2 = tmp_path / "d2.csv"
    matches = tmp_path / "matches.csv"
    debug = tmp_path / "match_debug.csv"
    d1.write_text("id,address,name\n1,1 Main St Oakland CA 94612,Acme Market\n", encoding="utf-8")
    d2.write_text(
        "id,account_name,owner_name,name,street,city,zip\n2,Acme Market,,Acme Market,1 Main St,Oakland,94612\n",
        encoding="utf-8",
    )

    assert main(["--dataset1", str(d1), "--dataset2", str(d2), "--output", str(matches), "--debug-output", str(debug)]) == 0
    assert pd.read_csv(matches).to_dict("records") == [{"id_1": 1, "id_2": 2}]
    assert pd.read_csv(debug).loc[0, "decision"] == "match"