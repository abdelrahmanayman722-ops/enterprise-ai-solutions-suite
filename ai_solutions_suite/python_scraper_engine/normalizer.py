"""
Data Normalization & SHA-256 Deduplication Engine
==================================================
Cleans scraped content, unescapes entities, normalizes multi-currency pricing and dates,
and computes cryptographic SHA-256 fingerprints to eliminate duplicate records.
Author: Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

import html
import re
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set

class DataNormalizer:
    """Provides text sanitation, price/date normalization, and fingerprint deduplication."""

    CURRENCY_SYMBOLS = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "₹": "INR",
        "USD": "USD",
        "EUR": "EUR",
        "GBP": "GBP"
    }

    def __init__(self):
        self.seen_fingerprints: Set[str] = set()

    def clean_text(self, raw_text: Optional[str]) -> str:
        """Strips HTML tags, unescapes entities, removes control chars, and normalizes spaces."""
        if not raw_text:
            return ""
        # Unescape HTML entities (&amp;, &lt;, &quot;, &#39;)
        text = html.unescape(raw_text)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        # Collapse multiple spaces and newlines
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def parse_currency(self, raw_price: Optional[str]) -> Dict[str, Any]:
        """
        Parses raw pricing strings into structured amount, ISO currency code, and interval.
        Examples:
          - "$2,450.00 / mo" -> amount: 2450.0, currency: "USD", interval: "monthly"
          - "€120k / yr"      -> amount: 120000.0, currency: "EUR", interval: "annual"
          - "£45/hr"          -> amount: 45.0, currency: "GBP", interval: "hourly"
          - "FREE"            -> amount: 0.0, currency: "USD", interval: "one-time"
        """
        if not raw_price:
            return {"amount": 0.0, "currency": "USD", "interval": "one-time", "raw": ""}

        raw = raw_price.strip()
        lower = raw.lower()

        if "free" in lower or "complimentary" in lower:
            return {"amount": 0.0, "currency": "USD", "interval": "one-time", "raw": raw}

        # Detect currency
        currency = "USD"
        for sym, code in self.CURRENCY_SYMBOLS.items():
            if sym.lower() in lower:
                currency = code
                break

        # Detect interval using regex with flexible spacing
        interval = "one-time"
        if re.search(r'(/\s*mo(?:nth)?|\bmonthly\b|\bper\s+month\b)', lower):
            interval = "monthly"
        elif re.search(r'(/\s*(?:yr|year|annum)|\bannu(?:al|ally)\b|\bper\s+year\b)', lower):
            interval = "annual"
        elif re.search(r'(/\s*h(?:ou)?r|\bhourly\b|\bper\s+hour\b)', lower):
            interval = "hourly"

        # Check for 'k' multiplier (e.g. 120k)
        has_k = bool(re.search(r'\b\d+(?:\.\d+)?k\b', lower))

        # Extract numeric digits
        # Matches formats: 2,450.00, 2450, 120
        cleaned_num_str = re.sub(r'[^\d\.]', '', raw)
        amount = 0.0
        if cleaned_num_str:
            try:
                amount = float(cleaned_num_str)
                if has_k and amount < 1000.0:
                    amount *= 1000.0
            except ValueError:
                amount = 0.0

        return {
            "amount": round(amount, 2),
            "currency": currency,
            "interval": interval,
            "raw": raw
        }

    def normalize_date(self, raw_date: Optional[str]) -> str:
        """
        Normalizes arbitrary date strings to ISO-8601 (YYYY-MM-DDTHH:MM:SSZ).
        Handles relative dates ('yesterday', '2 days ago', '3 hours ago') and standard formats.
        """
        now = datetime.now(timezone.utc)
        if not raw_date or not raw_date.strip():
            return now.isoformat()

        raw = raw_date.strip().lower()

        # Relative date patterns
        if "yesterday" in raw:
            return (now - timedelta(days=1)).isoformat()
        if "today" in raw or "just now" in raw:
            return now.isoformat()

        days_ago = re.search(r'(\d+)\s+day', raw)
        if days_ago:
            return (now - timedelta(days=int(days_ago.group(1)))).isoformat()

        hours_ago = re.search(r'(\d+)\s+hour', raw)
        if hours_ago:
            return (now - timedelta(hours=int(hours_ago.group(1)))).isoformat()

        # Try parsing standard formats
        date_formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%b %d, %Y",
            "%B %d, %Y",
            "%d/%m/%Y",
            "%m/%d/%Y"
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(raw_date.strip(), fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except ValueError:
                continue

        # Fallback to current UTC timestamp
        return now.isoformat()

    def compute_fingerprint(self, record: Dict[str, Any], key_fields: Optional[List[str]] = None) -> str:
        """
        Computes SHA-256 cryptographic fingerprint over canonicalized key fields.
        Default key fields: domain/source, title, and raw_id or url.
        """
        fields = key_fields or ["domain", "title", "url", "id", "price"]
        canonical_parts = []
        for f in sorted(fields):
            val = str(record.get(f, "")).strip().lower()
            canonical_parts.append(f"{f}:{val}")

        canonical_str = "|".join(canonical_parts)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def is_duplicate(self, fingerprint: str) -> bool:
        """Checks if fingerprint was already observed in this session."""
        return fingerprint in self.seen_fingerprints

    def register_record(self, record: Dict[str, Any], key_fields: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Computes fingerprint, checks duplicate status, and registers it.
        Returns (is_new, fingerprint).
        """
        fp = self.compute_fingerprint(record, key_fields)
        if fp in self.seen_fingerprints:
            return False, fp
        self.seen_fingerprints.add(fp)
        return True, fp

    def clear(self):
        """Clears deduplication cache."""
        self.seen_fingerprints.clear()
