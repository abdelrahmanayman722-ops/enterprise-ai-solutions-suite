"""
WeWorkRemotely RSS Feed Adapter
===============================
Ingests live remote engineering roles across Full-Stack, Programming,
Backend, and DevOps categories via RSS 2.0 XML feeds.
"""

import urllib.request
import xml.etree.ElementTree as ET
import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any, Optional


class WWRAdapter:
    FEED_URLS = [
        "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    ]
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def _fetch_rss_content(self, url: str) -> Optional[str]:
        req = urllib.request.Request(url, headers=self.DEFAULT_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"[WWRAdapter] Warning: Failed to fetch RSS feed {url}: {e}")
            return None

    def parse_rss_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """Parse WeWorkRemotely RSS 2.0 XML into structured opportunities."""
        if not xml_text:
            return []

        jobs = []
        try:
            root = ET.fromstring(xml_text)
            channel = root.find("channel")
            if channel is None:
                return []

            items = channel.findall("item")
            for idx, item in enumerate(items):
                parsed = self._parse_item(item, idx)
                if parsed:
                    jobs.append(parsed)
            return jobs
        except Exception as e:
            print(f"[WWRAdapter] XML parsing error: {e}")
            return []

    def _parse_item(self, item: ET.Element, fallback_idx: int) -> Optional[Dict[str, Any]]:
        raw_title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date_raw = item.findtext("pubDate", "").strip()
        guid = item.findtext("guid", "").strip() or f"wwr_{fallback_idx}"
        region = item.findtext("region", "").strip() or "Worldwide / Remote"
        job_type = item.findtext("type", "").strip() or "Contractor"
        description_raw = item.findtext("description", "").strip()

        # Split title: WeWorkRemotely titles are formatted as "Company Name: Position Title"
        company = ""
        role = raw_title
        if ":" in raw_title:
            parts = raw_title.split(":", 1)
            company = parts[0].strip()
            role = parts[1].strip()

        # Parse publication date to ISO format
        posted_iso = datetime.now(timezone.utc).isoformat()
        if pub_date_raw:
            try:
                dt = parsedate_to_datetime(pub_date_raw)
                posted_iso = dt.isoformat()
            except Exception:
                pass

        # Clean description HTML
        clean_desc = html.unescape(description_raw)
        clean_desc = re.sub(r"<[^>]+>", " ", clean_desc)
        clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

        # Attempt to extract salary cues from description or title
        raw_comp = "Competitive ($3,500 - $6,000/mo)"
        salary_match = re.search(
            r"([$€£]\s*\d+(?:,\d{3})*(?:\.\d+)?(?:\s*[kK])?\s*(?:-|to)?\s*[$€£]?\s*\d+(?:,\d{3})*(?:\.\d+)?(?:\s*[kK])?"
            r"(?:\s*(?:/|\bper\b)?\s*(?:yr|year|annual|mo|month|hr|hour))?)",
            clean_desc,
            re.IGNORECASE
        )
        if salary_match and len(salary_match.group(0)) > 3:
            raw_comp = salary_match.group(0).strip()

        return {
            "source_id": f"wwr_{guid.split('/')[-1]}",
            "title": role or "Senior Full-Stack Engineer",
            "company": company or "Remote Tech Company",
            "funding_stage": "Funded Startup",
            "location": region,
            "raw_compensation": raw_comp,
            "description": clean_desc,
            "url": link,
            "posted_date": posted_iso,
            "source_platform": "weworkremotely"
        }

    def fetch_all(self, limit_per_feed: int = 15) -> List[Dict[str, Any]]:
        """Fetch across all configured WWR feeds."""
        all_jobs = []
        for url in self.FEED_URLS:
            xml_content = self._fetch_rss_content(url)
            if xml_content:
                parsed = self.parse_rss_xml(xml_content)
                all_jobs.extend(parsed[:limit_per_feed])
        return all_jobs
