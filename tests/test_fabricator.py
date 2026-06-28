from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.fabricate_csvs import fabricate
from scripts.performance_check import run


def test_fabricator_writes_expected_headers_under_output_dir(tmp_path: Path) -> None:
    d1, d2 = fabricate(tmp_path / "generated" / "test-output", size=14)

    assert d1.parent == tmp_path / "generated" / "test-output"
    assert list(pd.read_csv(d1).columns) == ["id", "address", "name"]
    assert list(pd.read_csv(d2).columns) == ["id", "account_name", "owner_name", "name", "street", "city", "zip"]
    assert len(pd.read_csv(d1)) == 14
    assert len(pd.read_csv(d2)) == 14


def test_fabricator_includes_required_scenario_variations(tmp_path: Path) -> None:
    d1, d2 = fabricate(tmp_path / "out", size=7)
    df1 = pd.read_csv(d1, dtype=str).fillna("")
    df2 = pd.read_csv(d2, dtype=str).fillna("")

    assert df1["address"].str.contains("-").any()  # ZIP+4 variation
    assert df2["city"].str.contains("BERKELEY").any()  # moved business
    assert df2["name"].str.contains("Different Business").any()  # same address, changed name
    assert df1["name"].str.contains("Only In Dataset One").any()  # non-match


def test_performance_check_reports_runtime_and_candidate_counts(tmp_path: Path) -> None:
    metrics = run(20, tmp_path / "perf")

    assert metrics["size"] == 20
    assert metrics["candidate_count"] >= 0
    assert metrics["results"] <= 20
    assert metrics["runtime_seconds"] >= 0