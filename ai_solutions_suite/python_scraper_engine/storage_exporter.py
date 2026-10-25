"""
Multi-Target Storage Exporter (JSON, CSV, SQLite UPSERT)
=========================================================
Exports validated scraper pipelines into JSON, CSV, and concurrent SQLite tables
with automated index creation and SHA-256 fingerprint UPSERT (INSERT OR REPLACE).
Author: Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

import csv
import json
import os
import sqlite3
from typing import List, Dict, Any, Optional

class StorageExporter:
    """Handles multi-format data exports with ACID atomicity and idempotency."""

    @staticmethod
    def export_json(records: List[Dict[str, Any]], filepath: str, indent: int = 2) -> str:
        """Writes records to a formatted JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True) if os.path.dirname(filepath) else None
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=indent, ensure_ascii=False)
        return filepath

    @staticmethod
    def export_csv(records: List[Dict[str, Any]], filepath: str) -> str:
        """Writes records to an RFC-4180 compliant CSV file."""
        if not records:
            # Create empty file with empty headers
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                pass
            return filepath

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True) if os.path.dirname(filepath) else None

        # Collect union of all keys across records for consistent alignment
        fieldnames_set = set()
        for r in records:
            fieldnames_set.update(r.keys())
        fieldnames = sorted(list(fieldnames_set))

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                # Flatten any nested dictionaries or lists for CSV compatibility
                flat_row = {}
                for k in fieldnames:
                    val = r.get(k)
                    if isinstance(val, (dict, list)):
                        flat_row[k] = json.dumps(val, ensure_ascii=False)
                    else:
                        flat_row[k] = val
                writer.writerow(flat_row)

        return filepath

    @staticmethod
    def export_sqlite(
        records: List[Dict[str, Any]],
        db_path: str = "scraped_data.db",
        table_name: str = "scraped_records",
        upsert: bool = True
    ) -> int:
        """
        Persists records into SQLite with automated schema creation, WAL journal mode,
        and atomic UPSERT based on SHA-256 fingerprint.
        Returns the number of records inserted/replaced.
        """
        if not records:
            return 0

        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True) if os.path.dirname(db_path) else None

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            # Enable WAL mode for high concurrency
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")

            # Define schema
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS `{table_name}` (
                fingerprint TEXT PRIMARY KEY,
                id TEXT,
                title TEXT NOT NULL,
                price REAL,
                currency TEXT,
                interval TEXT,
                source_url TEXT,
                extracted_at TEXT,
                raw_payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_table_sql)

            # Create performance indices
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_price ON `{table_name}`(price);")
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_extracted ON `{table_name}`(extracted_at);")

            # Determine insert strategy
            action = "INSERT OR REPLACE" if upsert else "INSERT OR IGNORE"
            insert_sql = f"""
            {action} INTO `{table_name}` (
                fingerprint, id, title, price, currency, interval, source_url, extracted_at, raw_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """

            rows_to_insert = []
            for r in records:
                fp = str(r.get("fingerprint") or r.get("id") or hash(r.get("title", "")))
                rec_id = str(r.get("id", ""))
                title = str(r.get("title", "Untitled"))

                # Price normalization
                raw_p = r.get("price")
                if isinstance(raw_p, dict):
                    price_num = float(raw_p.get("amount", 0.0))
                    currency = str(raw_p.get("currency", "USD"))
                    interval = str(raw_p.get("interval", "one-time"))
                elif isinstance(raw_p, (int, float)):
                    price_num = float(raw_p)
                    currency = str(r.get("currency", "USD"))
                    interval = str(r.get("interval", "one-time"))
                elif isinstance(raw_p, str):
                    import re
                    num_match = re.search(r'[\d\.]+', raw_p)
                    price_num = float(num_match.group(0)) if num_match else 0.0
                    currency = str(r.get("currency", "USD"))
                    interval = str(r.get("interval", "one-time"))
                else:
                    price_num = 0.0
                    currency = "USD"
                    interval = "one-time"

                source_url = str(r.get("url") or r.get("source_url") or "")
                extracted_at = str(r.get("extracted_at") or r.get("timestamp") or "")
                raw_payload = json.dumps(r, ensure_ascii=False)

                rows_to_insert.append((
                    fp, rec_id, title, price_num, currency, interval, source_url, extracted_at, raw_payload
                ))

            cursor.executemany(insert_sql, rows_to_insert)
            conn.commit()
            return len(rows_to_insert)
        finally:
            conn.close()
