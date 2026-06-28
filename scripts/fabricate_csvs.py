from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


OUTPUT_DIR = Path("generated/test-output")


def build_synthetic_rows(size: int) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    dataset1: list[dict[str, str]] = []
    dataset2: list[dict[str, str]] = []
    scenarios = ["exact", "name_variation", "address_variation", "zip4", "moved", "same_address_changed_name", "non_match"]

    for i in range(size):
        scenario = scenarios[i % len(scenarios)]
        base_name = f"Acme Market {i}"
        city = "Oakland"
        zip5 = f"946{i % 10}{i % 10}"
        street_no = str(100 + i)
        street = f"{street_no} Main St"
        d1_name = base_name
        d1_address = f"{street}, {city}, CA {zip5}"
        d2_name = base_name
        d2_street = street
        d2_city = city.upper()
        d2_zip = zip5

        if scenario == "name_variation":
            d1_name = f"{base_name}, LLC"
            d2_name = base_name.replace("Market", "Mkt")
        elif scenario == "address_variation":
            d1_address = f"{street_no} Main Street, {city}, CA {zip5}"
            d2_street = f"{street_no} MAIN ST"
        elif scenario == "zip4":
            d1_address = f"{street}, {city}, CA {zip5}-1234"
            d2_zip = f"{zip5}1234"
        elif scenario == "moved":
            d2_street = f"{900 + i} Broadway Ave"
            d2_city = "BERKELEY"
            d2_zip = "947041111"
        elif scenario == "same_address_changed_name":
            d2_name = f"Different Business {i}"
        elif scenario == "non_match":
            d1_name = f"Only In Dataset One {i}"
            d2_name = f"Only In Dataset Two {i}"
            d2_street = f"{700 + i} Other Rd"
            d2_zip = "900001111"

        dataset1.append({"id": f"d1_{i}", "address": d1_address, "name": d1_name})
        dataset2.append(
            {
                "id": f"d2_{i}",
                "account_name": d2_name.upper(),
                "owner_name": f"Owner {i}",
                "name": d2_name,
                "street": d2_street,
                "city": d2_city,
                "zip": d2_zip,
            }
        )
    return dataset1, dataset2


def fabricate(output_dir: Path = OUTPUT_DIR, size: int = 100) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset1, dataset2 = build_synthetic_rows(size)
    dataset1_path = output_dir / "synthetic_dataset_1.csv"
    dataset2_path = output_dir / "synthetic_dataset_2.csv"
    pd.DataFrame(dataset1, columns=["id", "address", "name"]).to_csv(dataset1_path, index=False)
    pd.DataFrame(dataset2, columns=["id", "account_name", "owner_name", "name", "street", "city", "zip"]).to_csv(dataset2_path, index=False)
    return dataset1_path, dataset2_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Fabricate synthetic Ivix-format CSVs.")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--size", type=int, default=100)
    args = parser.parse_args()
    d1, d2 = fabricate(Path(args.output_dir), args.size)
    print(f"Wrote {d1}")
    print(f"Wrote {d2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())