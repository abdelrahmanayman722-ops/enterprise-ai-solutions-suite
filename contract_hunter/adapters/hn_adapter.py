"""
Hacker News Adapter (Algolia & Firebase)
========================================
Harvests startup and remote opportunities from:
1. HN Algolia Search API: Locates latest monthly "Who is hiring?" thread from user `whoishiring`
   and streams top-level comments (enforcing parent_id == story_id).
2. HN Firebase REST API: Direct stream from /v0/jobstories.json and item resolvers.
"""

import json
import urllib.request
import urllib.parse
import html
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


class HNAdapter:
    ALGOLIA_SEARCH_BY_DATE = "https://hn.algolia.com/api/v1/search_by_date"
    ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search"
    FIREBASE_BASE = "https://hacker-news.firebaseio.com/v0"
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def _http_get_json(self, url: str) -> Any:
        req = urllib.request.Request(url, headers=self.DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)

    def find_latest_who_is_hiring_thread(self) -> Optional[Dict[str, Any]]:
        """
        Locates the latest monthly 'Ask HN: Who is hiring?' thread published by user `whoishiring`.
        """
        params = urllib.parse.urlencode({
            "tags": "story,author_whoishiring",
            "query": "Ask HN: Who is hiring",
            "hitsPerPage": 5
        })
        url = f"{self.ALGOLIA_SEARCH_BY_DATE}?{params}"
        try:
            data = self._http_get_json(url)
            hits = data.get("hits", [])
            for hit in hits:
                title = hit.get("title", "")
                if "who is hiring?" in title.lower():
                    return hit
            if hits:
                return hits[0]
            return None
        except Exception as e:
            print(f"[HNAdapter] Warning: Failed to query Algolia monthly thread: {e}")
            return None

    def fetch_algolia_thread_comments(
        self, 
        story_id: str, 
        query: str = "remote", 
        hits_per_page: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Fetches comments within a target monthly thread.
        CRITICAL FILTER: Strictly rejects replies where parent_id != story_id to filter out candidate noise.
        """
        params = urllib.parse.urlencode({
            "tags": f"comment,story_{story_id}",
            "query": query,
            "hitsPerPage": hits_per_page
        })
        url = f"{self.ALGOLIA_SEARCH}?{params}"
        raw_jobs = []

        try:
            data = self._http_get_json(url)
            hits = data.get("hits", [])
            story_id_int = int(story_id)

            for hit in hits:
                parent_id = hit.get("parent_id")
                # Enforce parent_id == story_id (must be top-level post)
                if parent_id != story_id_int:
                    continue

                comment_html = hit.get("comment_text", "")
                if not comment_html:
                    continue

                parsed = self._parse_hn_comment(hit, story_id)
                if parsed:
                    raw_jobs.append(parsed)

            return raw_jobs
        except Exception as e:
            print(f"[HNAdapter] Warning: Failed to fetch thread comments for {story_id}: {e}")
            return []

    def _parse_hn_comment(self, hit: Dict[str, Any], story_id: str) -> Optional[Dict[str, Any]]:
        """Parse raw top-level HN comment into candidate opportunity structure."""
        comment_id = hit.get("objectID", "")
        raw_html = hit.get("comment_text", "")
        created_at = hit.get("created_at", datetime.now(timezone.utc).isoformat())
        
        # Clean HTML
        clean_text = html.unescape(raw_html)
        clean_text = re.sub(r"<p>", "\n\n", clean_text)
        clean_text = re.sub(r"<br\s*/?>", "\n", clean_text)
        clean_text = re.sub(r"<[^>]+>", "", clean_text).strip()

        lines = [line.strip() for line in clean_text.split("\n") if line.strip()]
        if not lines:
            return None

        header = lines[0]
        company = ""
        role = ""
        location = "Worldwide / Remote"
        compensation = ""

        # Attempt 1: Standard pipe-delimited format
        if "|" in header:
            parts = [p.strip() for p in header.split("|") if p.strip()]
            if len(parts) >= 2:
                company = parts[0]
                role = parts[1]
            if len(parts) >= 3:
                location = parts[2]
            if len(parts) >= 4:
                compensation = parts[3]
        elif " - " in header or " – " in header:
            parts = re.split(r"\s+[-–]\s+", header)
            if len(parts) >= 2:
                company = parts[0]
                role = parts[1]
            if len(parts) >= 3:
                location = parts[2]
        else:
            # Fallback heuristic
            company = header[:40]
            role = header[40:100] if len(header) > 40 else "Software Engineer"

        # Scan all lines for salary indicators if not in header
        if not compensation:
            for l in lines[1:4]:
                if any(c in l for c in ["$", "€", "£", "/yr", "/hr", "k", "USD"]):
                    compensation = l
                    break

        item_url = f"https://news.ycombinator.com/item?id={comment_id}"

        return {
            "source_id": f"hn_comment_{comment_id}",
            "title": role or "Senior Software Engineer",
            "company": company or "YC Startup",
            "location": location,
            "raw_compensation": compensation or "Competitive",
            "description": clean_text,
            "url": item_url,
            "posted_date": created_at,
            "source_platform": "hacker_news"
        }

    def fetch_firebase_job_stories(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Streams active verified YC startup jobs from Firebase /v0/jobstories.json.
        """
        url = f"{self.FIREBASE_BASE}/jobstories.json"
        results = []
        try:
            story_ids = self._http_get_json(url)
            if not isinstance(story_ids, list):
                return []
            
            for story_id in story_ids[:limit]:
                item_url = f"{self.FIREBASE_BASE}/item/{story_id}.json"
                try:
                    item = self._http_get_json(item_url)
                    if not item or item.get("type") != "job":
                        continue
                    parsed = self._parse_firebase_job(item)
                    if parsed:
                        results.append(parsed)
                except Exception:
                    continue
            return results
        except Exception as e:
            print(f"[HNAdapter] Warning: Failed to fetch Firebase job stories: {e}")
            return []

    def _parse_firebase_job(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Firebase job item format into structured candidate dict."""
        raw_title = item.get("title", "")
        item_id = item.get("id", "")
        item_time = item.get("time")
        posted_iso = datetime.fromtimestamp(item_time, timezone.utc).isoformat() if item_time else datetime.now(timezone.utc).isoformat()
        item_url = item.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
        raw_text = item.get("text", "") or raw_title

        # Title pattern typically: "Company (YC W24) is hiring a Senior Fullstack Engineer..."
        company = ""
        role = ""
        batch = ""

        # Extract batch e.g. (YC W24)
        batch_match = re.search(r"\((YC\s*[WSP]?\d{2})\)", raw_title, re.IGNORECASE)
        if batch_match:
            batch = batch_match.group(1).upper()

        if " is hiring " in raw_title:
            parts = raw_title.split(" is hiring ")
            company = parts[0]
            role = parts[1]
        elif " is looking for " in raw_title:
            parts = raw_title.split(" is looking for ")
            company = parts[0]
            role = parts[1]
        else:
            company = raw_title[:30]
            role = raw_title[30:] or "Software Engineer"

        # Clean batch code from company name if present
        company = re.sub(r"\s*\((?:YC\s*)?[WSP]?\d{2}\)", "", company).strip()

        return {
            "source_id": f"hn_firebase_{item_id}",
            "title": role.strip() or "Senior Software Engineer",
            "company": company.strip() or "YC Startup",
            "funding_stage": batch or "YC Startup",
            "location": "Worldwide / Remote",
            "raw_compensation": "Competitive ($3,500 - $6,000/mo)",
            "description": raw_text,
            "url": item_url,
            "posted_date": posted_iso,
            "source_platform": "hacker_news"
        }

    def fetch_all(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Unified fetch combining latest Algolia Who is Hiring comments and Firebase job stories."""
        combined = []
        # 1. Algolia
        thread = self.find_latest_who_is_hiring_thread()
        if thread:
            story_id = thread.get("objectID")
            comments = self.fetch_algolia_thread_comments(story_id=str(story_id), hits_per_page=limit)
            combined.extend(comments)

        # 2. Firebase
        fb_jobs = self.fetch_firebase_job_stories(limit=limit // 2)
        combined.extend(fb_jobs)
        return combined
