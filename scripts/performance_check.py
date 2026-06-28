from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ivix_matcher.address_parser import UsAddressParser
from ivix_matcher.candidates import CandidateIndex
from ivix_matcher.config import load_config
from ivix_matcher.io import load_csv
from ivix_matcher.matching import run_matching
from ivix_matcher.records import dataframes_to_query_and_index_records

from scripts.fabricate_csvs import fabricate


def run(size: int, output_dir: Path) -> dict[str, float | int]:
    config = load_config()
    d1_path, d2_path = fabricate(output_dir, size)
    parser = UsAddressParser()
    records1, records2 = dataframes_to_query_and_index_records(load_csv(d1_path), load_csv(d2_path), parser, config)
    index = CandidateIndex.build(records2, config)
    candidate_count = sum(len(index.query(record)) for record in records1)
    start = time.perf_counter()
    run_result = run_matching(records1, records2, config)
    runtime = time.perf_counter() - start
    return {
        "size": size,
        "candidate_count": candidate_count,
        "selected_results": len(run_result.selected_results),
        "debug_candidates": len(run_result.debug_results),
        "runtime_seconds": round(runtime, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synthetic matching performance check.")
    parser.add_argument("--size", type=int, default=1000)
    parser.add_argument("--output-dir", default="generated/test-output/perf")
    args = parser.parse_args()
    metrics = run(args.size, Path(args.output_dir))
    print(metrics)
    print("Note: match_debug.csv-style output can grow with candidate_count on large fabricated datasets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())