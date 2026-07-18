from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from csv_cleaner import CsvCleanerError, clean_csv
from csv_cleaner.cli import main


class CsvCleanerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, name: str, content: str) -> Path:
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def read_rows(self, path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_keeps_first_duplicate_and_writes_summary(self) -> None:
        source = self.write(
            "input.csv",
            "email,name\na@example.com,First\nb@example.com,Only\na@example.com,Last\n",
        )
        output = self.root / "clean.csv"
        summary = self.root / "summary.json"

        result = clean_csv(source, output, summary, key_columns=["email"])

        self.assertEqual(
            self.read_rows(output),
            [
                {"email": "a@example.com", "name": "First"},
                {"email": "b@example.com", "name": "Only"},
            ],
        )
        self.assertEqual(result.rows_read, 3)
        self.assertEqual(result.duplicates_removed, 1)
        payload = json.loads(summary.read_text())
        self.assertEqual(payload["output_sha256"], result.output_sha256)
        self.assertEqual(payload["key_columns"], ["email"])

    def test_keeps_last_occurrence_in_source_order(self) -> None:
        source = self.write(
            "input.csv",
            "id,value\n1,old\n2,only\n1,new\n3,third\n",
        )
        output = self.root / "clean.csv"

        clean_csv(
            source,
            output,
            self.root / "summary.json",
            key_columns=["id"],
            keep="last",
        )

        self.assertEqual(
            self.read_rows(output),
            [
                {"id": "2", "value": "only"},
                {"id": "1", "value": "new"},
                {"id": "3", "value": "third"},
            ],
        )

    def test_composite_key(self) -> None:
        source = self.write(
            "input.csv",
            "account,date,value\na,2026-01-01,1\na,2026-01-02,2\na,2026-01-01,3\n",
        )
        output = self.root / "clean.csv"

        clean_csv(
            source,
            output,
            self.root / "summary.json",
            key_columns=["account", "date"],
        )

        self.assertEqual(len(self.read_rows(output)), 2)

    def test_rejects_missing_key_without_creating_output(self) -> None:
        source = self.write("input.csv", "id,value\n1,a\n")
        output = self.root / "clean.csv"

        with self.assertRaisesRegex(CsvCleanerError, "key columns not found: email"):
            clean_csv(
                source,
                output,
                self.root / "summary.json",
                key_columns=["email"],
            )
        self.assertFalse(output.exists())

    def test_rejects_duplicate_headers(self) -> None:
        source = self.write("input.csv", "id,id\n1,2\n")

        with self.assertRaisesRegex(CsvCleanerError, "duplicate column names"):
            clean_csv(
                source,
                self.root / "clean.csv",
                self.root / "summary.json",
                key_columns=["id"],
            )

    def test_rejects_malformed_row(self) -> None:
        source = self.write("input.csv", "id,value\n1,a,extra\n")

        with self.assertRaisesRegex(CsvCleanerError, "row 2"):
            clean_csv(
                source,
                self.root / "clean.csv",
                self.root / "summary.json",
                key_columns=["id"],
            )

    def test_rejects_overwriting_input(self) -> None:
        source = self.write("input.csv", "id,value\n1,a\n")

        with self.assertRaisesRegex(CsvCleanerError, "paths must be distinct"):
            clean_csv(
                source,
                source,
                self.root / "summary.json",
                key_columns=["id"],
            )

    def test_cli_returns_nonzero_for_invalid_input(self) -> None:
        source = self.write("input.csv", "id,value\n1,a\n")
        result = main(
            [
                str(source),
                str(self.root / "clean.csv"),
                "--keys",
                "missing",
            ]
        )
        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()

