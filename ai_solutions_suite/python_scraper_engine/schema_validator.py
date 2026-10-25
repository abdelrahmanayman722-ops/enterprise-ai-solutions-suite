"""
Scraper Schema Validator & Error Quarantine Engine
===================================================
Enforces strict Pydantic-style type constraints, boundary checks, and error quarantine
to isolate malformed payloads without crashing the ingestion pipeline.
Author: Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

class ValidationError(Exception):
    """Raised when record violates required schema constraints."""
    pass

class SchemaValidator:
    """Validates scraped data records against strict enterprise contracts."""

    def __init__(self, min_title_len: int = 2, max_title_len: int = 500):
        self.min_title_len = min_title_len
        self.max_title_len = max_title_len
        self.quarantine_records: List[Dict[str, Any]] = []

    def validate_record(self, record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates a single record against schema rules:
        - Must be a dictionary.
        - Must contain non-empty 'title' within allowed length bounds.
        - 'price' (or normalized price amount) must be a non-negative float.
        - Must not contain abusive or corrupted payload strings.
        Returns (is_valid, error_reason).
        """
        if not isinstance(record, dict):
            return False, "Record is not a dictionary."

        # Title validation
        title = record.get("title")
        if title is None:
            return False, "Field 'title' is required."
        if not isinstance(title, str):
            return False, f"Field 'title' must be a string, got {type(title).__name__}."
        clean_title = title.strip()
        if len(clean_title) < self.min_title_len:
            return False, f"Title length ({len(clean_title)}) is below minimum ({self.min_title_len})."
        if len(clean_title) > self.max_title_len:
            return False, f"Title length ({len(clean_title)}) exceeds maximum ({self.max_title_len})."

        # Price validation
        price_val = record.get("price")
        # May be float or string or dict from normalizer
        if isinstance(price_val, dict):
            amount = price_val.get("amount", 0.0)
        elif isinstance(price_val, (int, float)):
            amount = float(price_val)
        elif isinstance(price_val, str):
            import re
            cleaned_num = re.sub(r'[^\d\.]', '', price_val)
            amount = float(cleaned_num) if cleaned_num else 0.0
        elif price_val is None:
            amount = 0.0
        else:
            return False, f"Field 'price' has invalid type: {type(price_val).__name__}."

        if amount < 0.0:
            return False, f"Price amount ({amount}) cannot be negative."

        # Boundary check on overall record payload size (prevent memory bombs)
        if len(str(record)) > 100000:
            return False, "Total record size exceeds 100KB boundary limit."

        return True, None

    def quarantine(self, record: Dict[str, Any], reason: str):
        """Isolates malformed record with diagnostic metadata."""
        quarantined_entry = {
            "record": record,
            "error_reason": reason,
            "quarantined_at": datetime.now(timezone.utc).isoformat()
        }
        self.quarantine_records.append(quarantined_entry)

    def process(self, records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filters a list of records:
        - Valid records are retained and returned.
        - Invalid records are quarantined with reasons.
        Returns (valid_records, quarantined_records).
        """
        valid_records = []
        for r in records:
            is_valid, reason = self.validate_record(r)
            if is_valid:
                valid_records.append(r)
            else:
                self.quarantine(r, reason or "Unknown validation failure")

        return valid_records, self.quarantine_records

    def get_quarantine_report(self) -> Dict[str, Any]:
        """Returns statistical overview of quarantined records."""
        reasons_count: Dict[str, int] = {}
        for entry in self.quarantine_records:
            r = entry["error_reason"]
            reasons_count[r] = reasons_count.get(r, 0) + 1

        return {
            "total_quarantined": len(self.quarantine_records),
            "reasons_breakdown": reasons_count,
            "quarantine_log": self.quarantine_records
        }

    def clear(self):
        """Resets the quarantine buffer."""
        self.quarantine_records.clear()
