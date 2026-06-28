from __future__ import annotations

import argparse

from .address_parser import UsAddressParser
from .io import ensure_output_not_input, inspect_headers, load_csv
from .matching import match_records
from .output import write_debug, write_matches
from .records import dataframe_to_records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Match Ivix assignment business records.")
    parser.add_argument("--dataset1", required=True, help="Path to first/read-only CSV dataset")
    parser.add_argument("--dataset2", required=True, help="Path to second/read-only CSV dataset")
    parser.add_argument("--output", required=True, help="Path for matches.csv output")
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
    ensure_output_not_input(args.debug_output, input_paths)

    df1 = load_csv(args.dataset1)
    df2 = load_csv(args.dataset2)
    headers1, headers2 = inspect_headers(args.dataset1, args.dataset2)
    print(f"Loaded dataset1: {len(df1)} rows, headers={headers1}")
    print(f"Loaded dataset2: {len(df2)} rows, headers={headers2}")
    parser = UsAddressParser()
    records1 = dataframe_to_records(df1, "dataset1", parser)
    records2 = dataframe_to_records(df2, "dataset2", parser)
    results = match_records(records1, records2)
    write_matches(results, args.output, input_paths)
    write_debug(results, args.debug_output, input_paths)
    print(f"Wrote matches: {args.output}")
    print(f"Wrote debug: {args.debug_output}")
    return 0