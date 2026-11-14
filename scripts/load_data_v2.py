
#!/usr/bin/env python3
"""Safely load validated synthetic CSV data into the isolated SQLite database."""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data" / "step38_test" / "generated"
DB_PATH = ROOT / "data" / "step40_test" / "insurance_schema_v2.db"

TABLES = [
    "claimants",
    "policies",
    "incidents",
    "providers",
    "claims",
    "invoices",
    "payments",
    "relationship_edges",
]


def read_csv(name):
    path = DATA_DIR / f"{name}.csv"

    if not path.is_file():
        raise FileNotFoundError(f"Missing CSV file: {path}")

    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def main():
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}. Run create_schema_v2.py first."
        )

    datasets = {name: read_csv(name) for name in TABLES}

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        # Stop if the isolated database already contains data.
        all_tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        ]

        for name in all_tables:
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{name}"'
            ).fetchone()[0]

            if count != 0:
                raise RuntimeError(
                    f"Import stopped: table '{name}' already has "
                    f"{count} records. No existing data was changed."
                )

        # All inserts happen in one transaction.
        with connection:
            for name in TABLES:
                rows = datasets[name]

                if not rows:
                    raise ValueError(f"No records in {name}.csv")

                columns = list(rows[0].keys())
                quoted_columns = ", ".join(
                    f'"{column}"' for column in columns
                )
                placeholders = ", ".join(
                    "?" for _ in columns
                )

                sql = (
                    f'INSERT INTO "{name}" '
                    f'({quoted_columns}) VALUES ({placeholders})'
                )

                values = [
                    tuple(row[column] for column in columns)
                    for row in rows
                ]

                connection.executemany(sql, values)

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise RuntimeError(
                f"Foreign-key violations detected: {violations[:5]}"
            )

        print("\nSTEP 40D - DATA IMPORT RESULTS")
        print("=" * 45)

        for name in TABLES:
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{name}"'
            ).fetchone()[0]
            print(f"{name}: {count}")

        print("=" * 45)
        print("FOREIGN KEY VIOLATIONS:", len(violations))
        print("STEP 40D: PASSED")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
