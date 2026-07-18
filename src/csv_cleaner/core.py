from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Sequence


class CsvCleanerError(ValueError):
    """Raised when an input cannot be cleaned without ambiguity."""


@dataclass(frozen=True)
class CleanSummary:
    input_file: str
    output_file: str
    rows_read: int
    rows_written: int
    duplicates_removed: int
    key_columns: list[str]
    keep: Literal["first", "last"]
    delimiter: str
    input_sha256: str
    output_sha256: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validated_paths(input_path: Path, output_path: Path, summary_path: Path) -> None:
    if not input_path.is_file():
        raise CsvCleanerError(f"input is not a file: {input_path}")

    resolved_input = input_path.resolve()
    destinations = [output_path.resolve(), summary_path.resolve()]
    if resolved_input in destinations:
        raise CsvCleanerError("input, output, and summary paths must be distinct")
    if destinations[0] == destinations[1]:
        raise CsvCleanerError("output and summary paths must be distinct")

    for destination in (output_path, summary_path):
        if not destination.parent.is_dir():
            raise CsvCleanerError(f"destination directory does not exist: {destination.parent}")


def _read_rows(
    input_path: Path,
    *,
    encoding: str,
    delimiter: str,
) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with input_path.open("r", encoding=encoding, newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            if not reader.fieldnames:
                raise CsvCleanerError("input has no header row")

            fieldnames = list(reader.fieldnames)
            if len(fieldnames) != len(set(fieldnames)):
                raise CsvCleanerError("input contains duplicate column names")
            if any(not name for name in fieldnames):
                raise CsvCleanerError("input contains a blank column name")

            rows: list[dict[str, str]] = []
            for line_number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise CsvCleanerError(
                        f"row {line_number} does not match the header column count"
                    )
                rows.append(row)
            return fieldnames, rows
    except UnicodeDecodeError as error:
        raise CsvCleanerError(f"input is not valid {encoding}: {error}") from error
    except csv.Error as error:
        raise CsvCleanerError(f"invalid CSV: {error}") from error


def _deduplicate(
    rows: Sequence[dict[str, str]],
    key_columns: Sequence[str],
    keep: Literal["first", "last"],
) -> list[dict[str, str]]:
    if keep == "first":
        seen: set[tuple[str, ...]] = set()
        selected: list[dict[str, str]] = []
        for row in rows:
            key = tuple(row[column] for column in key_columns)
            if key not in seen:
                seen.add(key)
                selected.append(row)
        return selected

    last_index: dict[tuple[str, ...], int] = {}
    for index, row in enumerate(rows):
        last_index[tuple(row[column] for column in key_columns)] = index
    return [
        row
        for index, row in enumerate(rows)
        if last_index[tuple(row[column] for column in key_columns)] == index
    ]


def clean_csv(
    input_path: str | Path,
    output_path: str | Path,
    summary_path: str | Path,
    *,
    key_columns: Sequence[str],
    keep: Literal["first", "last"] = "first",
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
) -> CleanSummary:
    """Deduplicate a CSV and write a deterministic output plus JSON audit summary."""

    source = Path(input_path)
    output = Path(output_path)
    summary = Path(summary_path)
    _validated_paths(source, output, summary)

    keys = list(key_columns)
    if not keys or any(not column for column in keys):
        raise CsvCleanerError("at least one non-empty key column is required")
    if len(keys) != len(set(keys)):
        raise CsvCleanerError("key columns must be unique")
    if keep not in {"first", "last"}:
        raise CsvCleanerError("keep must be 'first' or 'last'")
    if len(delimiter) != 1:
        raise CsvCleanerError("delimiter must be exactly one character")

    fieldnames, rows = _read_rows(source, encoding=encoding, delimiter=delimiter)
    missing = [column for column in keys if column not in fieldnames]
    if missing:
        raise CsvCleanerError(f"key columns not found: {', '.join(missing)}")

    selected = _deduplicate(rows, keys, keep)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter=delimiter,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(selected)

    result = CleanSummary(
        input_file=str(source),
        output_file=str(output),
        rows_read=len(rows),
        rows_written=len(selected),
        duplicates_removed=len(rows) - len(selected),
        key_columns=keys,
        keep=keep,
        delimiter=delimiter,
        input_sha256=_sha256(source),
        output_sha256=_sha256(output),
    )
    summary.write_text(result.to_json(), encoding="utf-8")
    return result

