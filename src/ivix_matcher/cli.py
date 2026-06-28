from __future__ import annotations

import argparse

from .io import ensure_output_not_input, inspect_headers, load_csv


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

    # Slice 1: prove the CLI can load and inspect actual headers. Later slices
    # replace this placeholder with the full matching pipeline.
    df1 = load_csv(args.dataset1)
    df2 = load_csv(args.dataset2)
    headers1, headers2 = inspect_headers(args.dataset1, args.dataset2)
    print(f"Loaded dataset1: {len(df1)} rows, headers={headers1}")
    print(f"Loaded dataset2: {len(df2)} rows, headers={headers2}")
    return 0