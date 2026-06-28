# Ivix Record Matching

Deterministic, explainable Python record-linkage pipeline for the Ivix assignment.

## Run

```bash
python main.py --dataset1 "dataset_1 (34).csv" --dataset2 "dataset_2 (34).csv" --output matches.csv
```

Optional output paths:

```bash
python main.py \
  --dataset1 "dataset_1 (34).csv" \
  --dataset2 "dataset_2 (34).csv" \
  --output matches.csv \
  --selected-output selected_candidates.csv \
  --debug-output match_debug.csv
```

Input CSVs are treated as read-only. The CLI refuses to write any output to the same path as either input file.

## Outputs

- `matches.csv`: final accepted matches only, with columns `id_1,id_2`.
- `selected_candidates.csv`: one best candidate per dataset 1 row, including `match`, `review`, `best_candidate_below_threshold`, and `no_candidate` rows.
- `match_debug.csv`: all scored candidates, not just selected candidates. This can grow large on fabricated/larger datasets.

Debug/selected columns:

```text
id_1,id_2,address_score,business_name_score,legal_entity_score,best_name_field,best_name_value,combined_score,decision,reasons
```

## Matching approach

- Builds address and name/legal fallback indexes over dataset 2 only.
- Dataset 1 records generate lookup keys and query those indexes; candidate generation does not scan dataset 2 per row.
- Address scoring treats missing optional fields such as state/full ZIP as neutral while requiring sufficient evidence coverage so sparse matches cannot become high confidence.
- Business-name scoring compares generated normal/compact/variant forms using RapidFuzz.
- Legal/entity matching (`owner_name`) is scored separately from business names and is only allowed to produce an automatic match with strong address evidence.

## Tests and performance

```bash
pytest -q
python scripts/performance_check.py --size 1000
```

The performance script reports candidate count and runtime. Synthetic CSVs are written under `generated/test-output/`.