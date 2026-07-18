from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import CsvCleanerError, clean_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv-cleaner",
        description="Deduplicate a CSV and emit an auditable JSON summary.",
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--keys",
        required=True,
        help="Comma-separated columns that form the duplicate key.",
    )
    parser.add_argument(
        "--keep",
        choices=("first", "last"),
        default="first",
        help="Which occurrence to preserve (default: first).",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        help="Summary path (default: <output>.summary.json).",
    )
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--encoding", default="utf-8-sig")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    keys = [column.strip() for column in arguments.keys.split(",")]
    summary = arguments.summary or Path(f"{arguments.output}.summary.json")
    try:
        result = clean_csv(
            arguments.input,
            arguments.output,
            summary,
            key_columns=keys,
            keep=arguments.keep,
            delimiter=arguments.delimiter,
            encoding=arguments.encoding,
        )
    except CsvCleanerError as error:
        print(f"csv-cleaner: {error}", file=sys.stderr)
        return 2

    print(result.to_json(), end="")
    return 0

