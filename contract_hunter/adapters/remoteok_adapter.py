"""
RemoteOK API Adapter
====================
Consumes RemoteOK public REST feed with custom headers and resilient filtering.
"""

import json
import urllib.request
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


class RemoteOKAdapter:
    REMOTEOK_API_URL = "https://remoteok.com/api"
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def fetch_all(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Fetch remote jobs from RemoteOK public JSON endpoint."""
        req = urllib.request.Request(self.REMOTEOK_API_URL, headers=self.DEFAULT_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                # RemoteOK first entry is a legal / usage disclaimer dict
                raw_jobs = [j for j in data if isinstance(j, dict) and "position" in j]
                return self.parse_raw_jobs(raw_jobs[:limit])
        except Exception as e:
            print(f"[RemoteOKAdapter] Warning: Live request failed: {e}")
            return []

    def parse_raw_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse RemoteOK job objects into canonical candidate structures."""
        results = []
        for j in raw_jobs:
            job_id = j.get("id") or j.get("slug") or ""
            position = j.get("position", "").strip()
            company = j.get("company", "").strip()
            tags = [t.lower().strip() for t in j.get("tags", []) if isinstance(t, str)]
            description = j.get("description", "")
            url = j.get("url") or f"https://remoteok.com/remote-jobs/{job_id}"
            location = j.get("location", "").strip() or "Worldwide / Remote"
            date_raw = j.get("date", "")
            
            # Compensation fields
            sal_min = j.get("salary_min")
            sal_max = j.get("salary_max")
            raw_comp = ""
            if sal_min and sal_max:
                raw_comp = f"${sal_min:,} - ${sal_max:,} / yr"
            elif sal_min:
                raw_comp = f"${sal_min:,}+ / yr"

            results.append({
                "source_id": f"remoteok_{job_id}",
                "title": position,
                "company": company,
                "funding_stage": "Funded Remote",
                "location": location,
                "raw_compensation": raw_comp or "Competitive ($3,500 - $6,000/mo)",
                "tags": tags,
                "description": description,
                "url": url,
                "posted_date": date_raw or datetime.now(timezone.utc).isoformat(),
                "source_platform": "remoteok"
            })
        return results
