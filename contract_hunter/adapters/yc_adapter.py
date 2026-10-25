"""
Y Combinator Work at a Startup Adapter
======================================
Extracts pre-hydrated startup job postings directly from Inertia.js `data-page`
payloads on `ycombinator.com/jobs` and `workatastartup.com/jobs`.
"""

import json
import urllib.request
import re
import html
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


class YCAdapter:
    YC_JOBS_URL = "https://www.ycombinator.com/jobs"
    WORK_AT_A_STARTUP_URL = "https://www.workatastartup.com/jobs"
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def _fetch_html(self, url: str) -> Optional[str]:
        req = urllib.request.Request(url, headers=self.DEFAULT_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"[YCAdapter] Warning: Failed to fetch {url}: {e}")
            return None

    def extract_inertia_data_page(self, html_content: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON payload from Inertia.js data-page attribute."""
        if not html_content:
            return None
        
        # Match data-page="..." or data-page='...'
        match = re.search(r'data-page=(["\'])(.*?)\1', html_content, re.DOTALL)
        if not match:
            return None

        raw_attr = match.group(2)
        try:
            decoded_json = html.unescape(raw_attr)
            return json.loads(decoded_json)
        except Exception as e:
            print(f"[YCAdapter] Failed to decode Inertia data-page JSON: {e}")
            return None

    def parse_job_postings_from_page(self, inertia_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Inertia props structure for job postings."""
        if not inertia_data or not isinstance(inertia_data, dict):
            return []

        props = inertia_data.get("props", {})
        # Different Inertia components name the list differently: jobPostings or jobs
        postings = props.get("jobPostings") or props.get("jobs") or []
        if not isinstance(postings, list):
            return []

        results = []
        for p in postings:
            if not isinstance(p, dict):
                continue

            posting_id = p.get("id") or p.get("job_id") or ""
            title = p.get("title") or p.get("role") or "Full-Stack Engineer"
            company = p.get("companyName") or p.get("company_name") or "YC Startup"
            batch = p.get("companyBatchName") or p.get("batch") or "YC"
            funding_stage = f"YC {batch}" if not batch.startswith("YC") else batch
            salary_range = p.get("salaryRange") or p.get("salary") or "$120k - $160k"
            equity = p.get("equityRange") or p.get("equity") or ""
            one_liner = p.get("companyOneLiner") or p.get("one_liner") or ""
            skills = p.get("skills") or []
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",") if s.strip()]
            location = p.get("location") or "Worldwide / Remote"
            url = p.get("applyUrl") or p.get("url") or f"https://www.ycombinator.com/companies/{company.lower().replace(' ', '-')}/jobs/{posting_id}"

            raw_desc = f"{one_liner}\nSkills: {', '.join(skills)}\nEquity: {equity}".strip()

            results.append({
                "source_id": f"yc_{posting_id}",
                "title": title,
                "company": company,
                "funding_stage": funding_stage,
                "salary_range": salary_range,
                "company_one_liner": one_liner,
                "location": location,
                "skills": skills,
                "url": url,
                "description": raw_desc,
                "posted_date": datetime.now(timezone.utc).isoformat(),
                "source_platform": "ycombinator"
            })

        return results

    def fetch_all(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetch and parse jobs from YC."""
        html_content = self._fetch_html(self.YC_JOBS_URL)
        if not html_content:
            # Fallback attempt to workatastartup
            html_content = self._fetch_html(self.WORK_AT_A_STARTUP_URL)

        if not html_content:
            return []

        inertia_data = self.extract_inertia_data_page(html_content)
        if not inertia_data:
            return []

        jobs = self.parse_job_postings_from_page(inertia_data)
        return jobs[:limit]
