"""Creates the finance database with Northwind's suppliers and Q3 supplier payments.

    python3 seed_finance.py /var/lib/northwind/finance.db

Does nothing if the database already exists.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

SUPPLIERS = [
    ("Harbour Packaging Ltd", "20-45-77", "active"),
    ("Kestrel Logistics", "40-11-62", "active"),
    ("Meadow Fresh Foods", "30-98-21", "active"),
    ("Brightline Cleaning Services", "60-14-55", "active"),
    ("Oakridge Office Supplies", "20-87-03", "active"),
    ("Summit Shopfitting", "55-70-19", "active"),
    ("Northgate Security Systems", "09-01-28", "active"),
    ("Riverside Print Works", "77-32-46", "blocked"),
]
CREATORS = ["daniel.hughes", "chloe.evans", "daniel.hughes", "chloe.evans", "priya.shah"]
APPROVERS = ["mark.taylor", "olivia.bennett", "priya.shah", "mark.taylor"]


def main(path: str) -> int:
    db_path = Path(path)
    if db_path.exists():
        print(f"{db_path} already exists, left as it is")
        return 0
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.executescript("""
        CREATE TABLE suppliers (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, sort_code TEXT NOT NULL,
            status TEXT NOT NULL);
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY, supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
            invoice TEXT NOT NULL, amount NUMERIC NOT NULL, currency TEXT NOT NULL,
            created_by TEXT NOT NULL, created_on TEXT NOT NULL,
            approved_by TEXT, approved_on TEXT, status TEXT NOT NULL);
    """)
    db.executemany("INSERT INTO suppliers (name, sort_code, status) VALUES (?, ?, ?)", SUPPLIERS)
    day, n = date(2026, 7, 1), 0
    while day <= date(2026, 9, 30):
        if day.weekday() in (1, 3):  # payment runs on Tuesdays and Thursdays
            for k in range(2):
                n += 1
                creator = CREATORS[n % len(CREATORS)]
                approver = APPROVERS[n % len(APPROVERS)]
                amount = round(180 + (n * 379.17) % 9400, 2)
                db.execute(
                    "INSERT INTO payments (supplier_id, invoice, amount, currency, created_by,"
                    " created_on, approved_by, approved_on, status)"
                    " VALUES (?, ?, ?, 'GBP', ?, ?, ?, ?, 'Paid')",
                    (
                        1 + (n * 3 + k) % 7,
                        f"INV-{26000 + n * 7}",
                        amount,
                        creator,
                        day.isoformat(),
                        approver,
                        (day + timedelta(days=1)).isoformat(),
                    ),
                )
        day += timedelta(days=1)
    db.commit()
    db.close()
    print(f"created {db_path} with {len(SUPPLIERS)} suppliers and {n} payments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "/var/lib/northwind/finance.db"))
