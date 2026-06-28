from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ivix_matcher.cli import main
from ivix_matcher.io import ensure_output_not_input, inspect_headers, load_csv


def write_csv(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_load_csv_uses_strings_and_fills_na(tmp_path: Path) -> None:
    path = tmp_path / "input.csv"
    write_csv(path, "id,name,zip\n1,A,00123\n2,,\n")

    df = load_csv(path)

    assert list(df.columns) == ["id", "name", "zip"]
    assert df.loc[0, "zip"] == "00123"
    assert df.loc[1, "name"] == ""
    assert df.loc[1, "zip"] == ""


def test_output_safeguard_rejects_input_path(tmp_path: Path) -> None:
    input_path = tmp_path / "dataset.csv"
    input_path.write_text("id\n1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Refusing to overwrite"):
        ensure_output_not_input(input_path, [input_path])


def test_output_safeguard_allows_different_path(tmp_path: Path) -> None:
    ensure_output_not_input(tmp_path / "matches.csv", [tmp_path / "dataset.csv"])


def test_inspect_headers(tmp_path: Path) -> None:
    d1 = tmp_path / "d1.csv"
    d2 = tmp_path / "d2.csv"
    write_csv(d1, "id,address,name\n1,a,n\n")
    write_csv(d2, "id,street,city\n2,s,c\n")

    assert inspect_headers(d1, d2) == (["id", "address", "name"], ["id", "street", "city"])


def test_cli_loads_inputs_and_checks_outputs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    d1 = tmp_path / "d1.csv"
    d2 = tmp_path / "d2.csv"
    write_csv(d1, "id,address,name\n1,a,n\n")
    write_csv(d2, "id,account_name,owner_name,name,street,city,zip\n2,acct,owner,n,s,c,z\n")

    exit_code = main([
        "--dataset1", str(d1),
        "--dataset2", str(d2),
        "--output", str(tmp_path / "matches.csv"),
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Loaded dataset1" in captured.out
    assert "Loaded dataset2" in captured.out