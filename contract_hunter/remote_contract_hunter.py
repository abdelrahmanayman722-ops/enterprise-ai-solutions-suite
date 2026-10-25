"""
Remote & Startup Contract Hunter Engine
======================================
Master aggregator, multi-currency salary normalizer, and dual CTO/Founder pitch generator
for high-ticket remote contracts ($3,500 - $6,000+/mo).
Engineered for Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

import os
import sys
import json
import csv
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

# Support both package imports and direct file execution
try:
    from .normalizer import (
        ContractOpportunity,
        parse_salary,
        is_high_ticket_opportunity,
        extract_skills,
        infer_funding_stage,
        compute_match_score,
    )
    from .pitch_generator import generate_dual_pitches, generate_cto_pitch, generate_founder_pitch
    from .cache_manager import ThreeTierFallbackManager, get_emergency_curated_opportunities
    from .adapters.hn_adapter import HNAdapter
    from .adapters.wwr_adapter import WWRAdapter
    from .adapters.yc_adapter import YCAdapter
    from .adapters.remoteok_adapter import RemoteOKAdapter
except ImportError:
    from normalizer import (
        ContractOpportunity,
        parse_salary,
        is_high_ticket_opportunity,
        extract_skills,
        infer_funding_stage,
        compute_match_score,
    )
    from pitch_generator import generate_dual_pitches, generate_cto_pitch, generate_founder_pitch
    from cache_manager import ThreeTierFallbackManager, get_emergency_curated_opportunities
    from adapters.hn_adapter import HNAdapter
    from adapters.wwr_adapter import WWRAdapter
    from adapters.yc_adapter import YCAdapter
    from adapters.remoteok_adapter import RemoteOKAdapter


class RemoteContractHunter:
    """Master orchestrator for aggregating, normalizing, and pitching remote startup contracts."""

    def __init__(
        self,
        target_keywords: Optional[List[str]] = None,
        min_monthly_salary: float = 3500.0,
        cache_dir: Optional[str] = None
    ):
        self.target_keywords = target_keywords or [
            "react", "next.js", "node", "full stack", "python", "ai", "sql", "typescript"
        ]
        self.min_monthly_salary = min_monthly_salary
        self.fallback_manager = ThreeTierFallbackManager(cache_dir=cache_dir)
        self.hn_adapter = HNAdapter()
        self.wwr_adapter = WWRAdapter()
        self.yc_adapter = YCAdapter()
        self.remoteok_adapter = RemoteOKAdapter()
        self.opportunities: List[ContractOpportunity] = []
        # Legacy attribute for backwards compatibility
        self.jobs: List[Dict[str, Any]] = []

    def fetch_all_sources(
        self, 
        limit_per_source: int = 20, 
        force_live: bool = False,
        use_fallback_only: bool = False
    ) -> List[ContractOpportunity]:
        """
        Aggregate remote opportunities across all sources through the 3-tier fallback hierarchy.
        """
        if use_fallback_only:
            return self._load_emergency_opportunities()

        all_raw_candidates: List[Dict[str, Any]] = []

        # 1. Hacker News (Algolia + Firebase)
        hn_raw, tier = self.fallback_manager.execute_with_fallback(
            cache_key="hn_stream",
            network_call=lambda: self.hn_adapter.fetch_all(limit=limit_per_source),
            emergency_fallback_call=lambda: [
                item for item in get_emergency_curated_opportunities() 
                if item.get("source_platform") == "hacker_news"
            ],
            domain="hn.algolia.com",
            force_refresh=force_live
        )
        if hn_raw:
            all_raw_candidates.extend(hn_raw)

        # 2. WeWorkRemotely RSS
        wwr_raw, tier = self.fallback_manager.execute_with_fallback(
            cache_key="wwr_stream",
            network_call=lambda: self.wwr_adapter.fetch_all(limit_per_feed=limit_per_source // 2),
            emergency_fallback_call=lambda: [
                item for item in get_emergency_curated_opportunities() 
                if item.get("source_platform") == "weworkremotely"
            ],
            domain="weworkremotely.com",
            force_refresh=force_live
        )
        if wwr_raw:
            all_raw_candidates.extend(wwr_raw)

        # 3. Y Combinator Inertia Jobs
        yc_raw, tier = self.fallback_manager.execute_with_fallback(
            cache_key="yc_stream",
            network_call=lambda: self.yc_adapter.fetch_all(limit=limit_per_source),
            emergency_fallback_call=lambda: [
                item for item in get_emergency_curated_opportunities() 
                if item.get("source_platform") == "ycombinator"
            ],
            domain="ycombinator.com",
            force_refresh=force_live
        )
        if yc_raw:
            all_raw_candidates.extend(yc_raw)

        # 4. RemoteOK API
        remoteok_raw, tier = self.fallback_manager.execute_with_fallback(
            cache_key="remoteok_stream",
            network_call=lambda: self.remoteok_adapter.fetch_all(limit=limit_per_source),
            emergency_fallback_call=lambda: [
                item for item in get_emergency_curated_opportunities() 
                if item.get("source_platform") == "remoteok"
            ],
            domain="remoteok.com",
            force_refresh=force_live
        )
        if remoteok_raw:
            all_raw_candidates.extend(remoteok_raw)

        # If all sources yielded zero candidates, load emergency dataset
        if not all_raw_candidates:
            return self._load_emergency_opportunities()

        # Normalize and filter
        normalized_list = []
        for raw in all_raw_candidates:
            opp = self.normalize_candidate(raw)
            if opp:
                normalized_list.append(opp)

        # Deduplicate
        deduped = self.deduplicate_opportunities(normalized_list)

        # Sort by match score descending
        deduped.sort(key=lambda o: o.match_score, reverse=True)

        self.opportunities = deduped
        self.jobs = [o.to_dict() for o in deduped]
        return deduped

    def normalize_candidate(self, raw: Dict[str, Any]) -> Optional[ContractOpportunity]:
        """Convert a raw adapter payload into a fully validated ContractOpportunity."""
        # Check if already a fully formed dictionary (e.g. from emergency fallback)
        if "id" in raw and "monthly_rate_usd_min" in raw and "pitch_cto" in raw and raw.get("pitch_cto"):
            return ContractOpportunity.from_dict(raw)

        title = raw.get("title", "").strip()
        company = raw.get("company", "").strip()
        if not title or not company:
            return None

        platform = raw.get("source_platform", "web")
        source_id = raw.get("source_id") or f"{platform}_{hash(title + company) % 10000000}"
        location = raw.get("location", "Worldwide / Remote").strip() or "Worldwide / Remote"
        url = raw.get("url", "")
        posted_date = raw.get("posted_date", datetime.now(timezone.utc).isoformat())
        description = raw.get("description", "").strip()
        raw_comp = raw.get("raw_compensation") or raw.get("salary_range") or ""

        # Extract skills
        existing_tags = raw.get("tags") or raw.get("skills") or []
        skills = extract_skills(f"{title} {description} {raw_comp}", existing_tags=existing_tags)
        
        # Check if matches target keywords
        matches_target = any(k in skills or k in title.lower() for k in self.target_keywords)
        if not matches_target and not any(k in description.lower() for k in ["engineer", "developer", "architect"]):
            return None

        # Parse salary
        min_usd, max_usd, period, matched_comp_str = parse_salary(f"{raw_comp} {description}")
        display_salary = matched_comp_str if matched_comp_str != "Unspecified" else (raw_comp or "$3,500 - $6,000 / mo (Negotiable)")

        # Evaluate high-ticket
        is_high_ticket = is_high_ticket_opportunity(min_usd, max_usd, title, description)

        # Infer funding stage
        funding = raw.get("funding_stage") or infer_funding_stage(company, f"{description} {title}")

        # Compute match score
        score = compute_match_score(
            skills=skills,
            monthly_max=max_usd,
            is_high_ticket=is_high_ticket,
            location=location,
            timezone="Worldwide"
        )

        # Generate personalized pitches
        one_liner = raw.get("company_one_liner")
        pitch_cto, pitch_founder = generate_dual_pitches(
            position=title,
            company=company,
            skills=skills,
            company_one_liner=one_liner
        )

        return ContractOpportunity(
            id=source_id,
            title=title,
            company=company,
            funding_stage=funding,
            salary_or_rate=display_salary,
            monthly_rate_usd_min=min_usd,
            monthly_rate_usd_max=max_usd,
            rate_period=period,
            is_high_ticket=is_high_ticket,
            skills_tags=skills,
            location=location,
            timezone_requirement="Worldwide",
            source_platform=platform,
            url=url,
            posted_date=posted_date,
            raw_description=description[:1000],
            match_score=score,
            pitch_cto=pitch_cto,
            pitch_founder=pitch_founder,
            fetched_at=datetime.now(timezone.utc).isoformat()
        )

    def deduplicate_opportunities(
        self, 
        opps: List[ContractOpportunity]
    ) -> List[ContractOpportunity]:
        """Deduplicate by (company, title) lowercase or URL."""
        seen = set()
        unique = []
        for o in opps:
            key = (o.company.lower().strip(), o.title.lower().strip())
            if key in seen:
                continue
            seen.add(key)
            unique.append(o)
        return unique

    def _load_emergency_opportunities(self) -> List[ContractOpportunity]:
        """Load curated emergency fallback list with fresh pitches."""
        raw_emergency = get_emergency_curated_opportunities()
        opps = []
        for r in raw_emergency:
            # Generate fresh pitches if empty
            if not r.get("pitch_cto") or not r.get("pitch_founder"):
                cto_p, founder_p = generate_dual_pitches(r["title"], r["company"], r["skills_tags"])
                r["pitch_cto"] = cto_p
                r["pitch_founder"] = founder_p
            opps.append(ContractOpportunity.from_dict(r))
        self.opportunities = opps
        self.jobs = [o.to_dict() for o in opps]
        return opps

    # Backwards compatibility methods
    def fetch_remoteok_jobs(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Legacy helper for RemoteOK fetching."""
        return [o.to_dict() for o in self.fetch_all_sources(limit_per_source=limit)]

    def _get_curated_fallback_jobs(self) -> List[Dict[str, Any]]:
        """Legacy helper returning curated emergency jobs as dicts."""
        opps = self._load_emergency_opportunities()
        return [o.to_dict() for o in opps]

    def generate_cto_pitch(self, position: str, company: str, skills: List[str]) -> str:
        """Legacy helper for CTO pitch generation."""
        return generate_cto_pitch(position, company, skills)

    def export_to_json(self, output_path: str = "curated_high_ticket_jobs.json") -> str:
        """Export normalized opportunities to JSON."""
        out_file = Path(output_path)
        if not out_file.is_absolute():
            base_dir = Path(__file__).resolve().parent
            out_file = base_dir / output_path

        out_file.parent.mkdir(parents=True, exist_ok=True)
        data = [o.to_dict() for o in self.opportunities] if self.opportunities else self.jobs
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return str(out_file)

    def export_to_csv(self, output_path: str = "curated_high_ticket_jobs.csv") -> str:
        """Export normalized opportunities to CSV."""
        out_file = Path(output_path)
        if not out_file.is_absolute():
            base_dir = Path(__file__).resolve().parent
            out_file = base_dir / output_path

        out_file.parent.mkdir(parents=True, exist_ok=True)
        data = [o.to_dict() for o in self.opportunities] if self.opportunities else self.jobs
        if not data:
            return str(out_file)

        fieldnames = [
            "id", "title", "company", "funding_stage", "salary_or_rate",
            "monthly_rate_usd_min", "monthly_rate_usd_max", "rate_period",
            "is_high_ticket", "skills_tags", "location", "timezone_requirement",
            "source_platform", "url", "posted_date", "match_score",
            "pitch_cto", "pitch_founder", "fetched_at"
        ]

        with open(out_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in data:
                csv_row = dict(row)
                if isinstance(csv_row.get("skills_tags"), list):
                    csv_row["skills_tags"] = ", ".join(csv_row["skills_tags"])
                writer.writerow(csv_row)
        return str(out_file)


def main():
    parser = argparse.ArgumentParser(description="Remote & Startup Contract Hunter CLI")
    parser.add_argument("--live", action="store_true", help="Force live network fetch across all sources")
    parser.add_argument("--fallback", action="store_true", help="Use curated emergency fallback dataset")
    parser.add_argument("--limit", type=int, default=20, help="Limit items per source")
    parser.add_argument("--json", type=str, default="curated_high_ticket_jobs.json", help="Output JSON path")
    parser.add_argument("--csv", type=str, default="curated_high_ticket_jobs.csv", help="Output CSV path")
    args = parser.parse_args()

    hunter = RemoteContractHunter()
    print("=" * 65)
    print("  Startup & Remote Contract Hunter (Eng. Abdelrahman Rashad)")
    print("=" * 65)
    print(f"[*] Aggregating contracts (limit={args.limit}, live={args.live}, fallback={args.fallback})...")

    opps = hunter.fetch_all_sources(
        limit_per_source=args.limit,
        force_live=args.live,
        use_fallback_only=args.fallback
    )

    high_ticket_count = sum(1 for o in opps if o.is_high_ticket)
    print(f"[+] Total opportunities retrieved: {len(opps)}")
    print(f"[+] High-ticket contracts ($3,500 - $6,000+/mo): {high_ticket_count}")

    hunter.export_to_json(args.json)
    hunter.export_to_csv(args.csv)
    print(f"[+] Exported JSON to: {args.json}")
    print(f"[+] Exported CSV to:  {args.csv}")
    print("[+] Done.")


if __name__ == "__main__":
    main()
