from __future__ import annotations

import pandas as pd

from ivix_matcher.address_parser import UsAddressParser
from ivix_matcher.records import dataframe_to_records, dataset1_row_to_record, dataset2_row_to_record


def test_dataset1_row_to_record_uses_full_address_and_name() -> None:
    row = pd.Series({"id": "d1", "address": "3228 16th St, San Francisco, CA 94103", "name": "Mozzeria SF"})

    record = dataset1_row_to_record(row, UsAddressParser())

    assert record.record_id == "d1"
    assert record.source == "dataset1"
    assert record.normalized_name == "mozzeria sf"
    assert record.address.city == "san francisco"
    assert record.address.state == "ca"
    assert record.address.postal_code5 == "94103"


def test_dataset2_row_to_record_uses_split_address_and_account_alternate_name() -> None:
    row = pd.Series(
        {
            "id": "d2",
            "account_name": "MLK GAS STATION",
            "owner_name": "TTVV CORP",
            "name": "MLK Gas Station",
            "street": "1515 W MARTIN LUTHER KING JR BLVD",
            "city": "LOS ANGELES",
            "zip": "900621743",
        }
    )

    record = dataset2_row_to_record(row, UsAddressParser())

    assert record.record_id == "d2"
    assert record.source == "dataset2"
    assert record.normalized_name == "mlk gas station"
    assert record.alternate_names == ("MLK GAS STATION",)
    assert record.normalized_alternate_names == ("mlk gas station",)
    assert "ttvv" not in record.all_normalized_names
    assert record.address.city == "los angeles"
    assert record.address.postal_code5 == "90062"


def test_dataset2_falls_back_to_account_name_when_name_missing() -> None:
    row = pd.Series(
        {
            "id": "d2",
            "account_name": "Palm Ave Motors Auto Repair",
            "owner_name": "Donald Travis Rousseau",
            "name": "",
            "street": "308 7TH AVE",
            "city": "SAN MATEO",
            "zip": "944014218",
        }
    )

    record = dataset2_row_to_record(row, UsAddressParser())

    assert record.raw_name == "Palm Ave Motors Auto Repair"
    assert record.normalized_name == "palm ave motors auto repair"
    assert "donald" not in record.all_normalized_names


def test_dataframe_to_records_dispatches_by_dataset() -> None:
    df = pd.DataFrame([{"id": "d1", "address": "1 Main St, Oakland, CA 94612", "name": "Acme Inc"}])

    records = dataframe_to_records(df, "dataset1", UsAddressParser())

    assert len(records) == 1
    assert records[0].record_id == "d1"