from __future__ import annotations

import argparse

from .address_parser import UsAddressParser
from .io import ensure_output_not_input, inspect_headers, load_csv
from .matching import run_matching
from .output import write_debug, write_matches, write_selected_candidates
from .records import dataframe_to_records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Match Ivix assignment business records.")
    parser.add_argument("--dataset1", required=True, help="Path to first/read-only CSV dataset")
    parser.add_argument("--dataset2", required=True, help="Path to second/read-only CSV dataset")
    parser.add_argument("--output", required=True, help="Path for matches.csv output")
    parser.add_argument(
        "--selected-output",
        default="selected_candidates.csv",
        help="Path for selected best-candidate output (default: selected_candidates.csv)",
    )
    parser.add_argument(
        "--debug-output",
        default="match_debug.csv",
        help="Path for debug scoring output (default: match_debug.csv)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_paths = [args.dataset1, args.dataset2]
    ensure_output_not_input(args.output, input_paths)
    ensure_output_not_input(args.selected_output, input_paths)
    ensure_output_not_input(args.debug_output, input_paths)

    df1 = load_csv(args.dataset1)
    df2 = load_csv(args.dataset2)
    headers1, headers2 = inspect_headers(args.dataset1, args.dataset2)
    print(f"Loaded dataset1: {len(df1)} rows, headers={headers1}")
    print(f"Loaded dataset2: {len(df2)} rows, headers={headers2}")
    parser = UsAddressParser()
    records1 = dataframe_to_records(df1, "dataset1", parser)
    records2 = dataframe_to_records(df2, "dataset2", parser)
    run = run_matching(records1, records2)
    write_matches(run.selected_results, args.output, input_paths)
    write_selected_candidates(run.selected_results, args.selected_output, input_paths)
    write_debug(run.debug_results, args.debug_output, input_paths)
    print(f"Wrote accepted matches only: {args.output}")
    print(f"Wrote best candidate per dataset1 row: {args.selected_output}")
    print(f"Wrote all scored candidates/debug details: {args.debug_output} ({len(run.debug_results)} candidates)")
    return 0