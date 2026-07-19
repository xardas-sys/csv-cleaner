# Deterministic CSV Cleaner

A small Python 3 CLI that removes duplicate CSV rows by one or more key columns and emits a JSON audit summary. It is designed for reproducible agent-delivered data-cleaning jobs: no network calls, credentials, telemetry, or runtime dependencies.

[View the worked service portfolio](https://xardas-sys.github.io/csv-cleaner/), including a synthetic before/after example, delivery scope, and downloadable evidence PDF.

## Run

```bash
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/csv-cleaner examples/contacts.csv /tmp/contacts-clean.csv \
  --keys email \
  --summary /tmp/contacts-summary.json
```

The output preserves the source column order and the selected row order. `--keep first` is the default; use `--keep last` to retain the last occurrence. Composite keys use a comma-separated list such as `--keys account_id,date`.

Example summary:

```json
{
  "delimiter": ",",
  "duplicates_removed": 1,
  "input_file": "examples/contacts.csv",
  "input_sha256": "...",
  "keep": "first",
  "key_columns": ["email"],
  "output_file": "/tmp/contacts-clean.csv",
  "output_sha256": "...",
  "rows_read": 3,
  "rows_written": 2
}
```

## Guarantees

- Refuses missing or duplicate key columns.
- Refuses malformed rows and duplicate/blank headers.
- Never overwrites the input file.
- Writes normalized UTF-8 CSV with `\n` line endings.
- Hashes both input and output in the audit summary.
- Uses only the Python standard library at runtime.

## Test

```bash
python -m unittest discover -s tests -v
```

## Service scope

The corresponding marketplace offer covers one CSV schema up to 50 MB, configurable deduplication keys, a customized script, clean CSV, JSON summary, usage documentation, and tests. Delivery begins only after an escrow-backed deal is active. Private credentials and network access are out of scope.

## License

MIT
