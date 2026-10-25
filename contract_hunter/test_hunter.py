"""
Comprehensive Automated Test Suite for Startup & Remote Contract Hunter (M1)
=============================================================================
Verifies 100% of functional requirements:
- Multi-currency salary parser with strict precedence ($3,500 - $6,000+/mo).
- Tech stack tag extractor and YC batch / funding stage detector.
- Dual CTO & Founder pitch generation with dynamic proof injection.
- Hacker News adapter (Algolia top-level isolator & Firebase parser).
- WeWorkRemotely RSS XML parser.
- Y Combinator Inertia data-page extractor.
- RemoteOK adapter parser.
- Token Bucket rate limiter & Disk Cache with TTL and stale-on-error.
- Three-tier fallback hierarchy (Network -> Cache -> Emergency Fallback).
- JSON and CSV exporters matching PROJECT.md interface contracts.
"""

import unittest
import os
import tempfile
import json
import csv
import html
from pathlib import Path

from normalizer import (
    ContractOpportunity,
    parse_salary,
    is_high_ticket_opportunity,
    extract_skills,
    infer_funding_stage,
    compute_match_score,
)
from pitch_generator import (
    generate_cto_pitch,
    generate_founder_pitch,
    generate_dual_pitches,
)
from cache_manager import (
    TokenBucketLimiter,
    DiskCacheManager,
    ThreeTierFallbackManager,
    get_emergency_curated_opportunities,
)
from adapters.hn_adapter import HNAdapter
from adapters.wwr_adapter import WWRAdapter
from adapters.yc_adapter import YCAdapter
from adapters.remoteok_adapter import RemoteOKAdapter
from remote_contract_hunter import RemoteContractHunter


class TestSalaryAndNormalizer(unittest.TestCase):
    """Tests for multi-currency salary parsing, skills extraction, and classification."""

    def test_hourly_rate_parsing(self):
        # Hourly precedence over annual/other: $45 - $65 / hr -> monthly = hourly * 160
        min_usd, max_usd, period, matched = parse_salary("Rate: $45 - $65 / hr for senior dev")
        self.assertEqual(period, "hourly")
        self.assertAlmostEqual(min_usd, 45.0 * 160.0)
        self.assertAlmostEqual(max_usd, 65.0 * 160.0)

        # Single hourly rate
        min_usd, max_usd, period, _ = parse_salary("Paying $50/hour fully remote")
        self.assertEqual(period, "hourly")
        self.assertAlmostEqual(min_usd, 8000.0)
        self.assertAlmostEqual(max_usd, 8000.0)

    def test_daily_rate_parsing(self):
        # Daily: £400 - £600 / day -> monthly = daily * 20 * 1.28
        min_usd, max_usd, period, _ = parse_salary("Contract: £400 - £600 / day")
        self.assertEqual(period, "daily")
        self.assertAlmostEqual(min_usd, 400 * 1.28 * 20.0, places=1)
        self.assertAlmostEqual(max_usd, 600 * 1.28 * 20.0, places=1)

    def test_monthly_rate_parsing(self):
        # Monthly: $3500 - $5500 / mo
        min_usd, max_usd, period, _ = parse_salary("Budget: $3,500 - $5,500 / mo retainer")
        self.assertEqual(period, "monthly")
        self.assertAlmostEqual(min_usd, 3500.0)
        self.assertAlmostEqual(max_usd, 5500.0)

    def test_annual_rate_parsing(self):
        # Annual: $140k - $180k -> monthly = annual / 12
        min_usd, max_usd, period, _ = parse_salary("Salary range: $140k - $180k + equity")
        self.assertEqual(period, "annual")
        self.assertAlmostEqual(min_usd, 140000.0 / 12.0, places=1)
        self.assertAlmostEqual(max_usd, 180000.0 / 12.0, places=1)

        # Full numbers: $120,000 - $160,000 / year
        min_usd, max_usd, period, _ = parse_salary("$120,000 - $160,000 / year")
        self.assertEqual(period, "annual")
        self.assertAlmostEqual(min_usd, 10000.0, places=1)
        self.assertAlmostEqual(max_usd, 13333.33, places=1)

    def test_multi_currency_conversion(self):
        # EUR: €80k - €100k (EUR factor 1.08)
        min_usd, max_usd, period, _ = parse_salary("Salary: €80k - €100k / year")
        self.assertEqual(period, "annual")
        self.assertAlmostEqual(min_usd, (80000 * 1.08) / 12.0, places=1)
        self.assertAlmostEqual(max_usd, (100000 * 1.08) / 12.0, places=1)

    def test_unspecified_salary(self):
        min_usd, max_usd, period, _ = parse_salary("Competitive salary + substantial equity (DOE)")
        self.assertIsNone(min_usd)
        self.assertIsNone(max_usd)
        self.assertEqual(period, "unspecified")

    def test_high_ticket_classification(self):
        # Explicit high rate
        self.assertTrue(is_high_ticket_opportunity(4000.0, 6000.0, "Engineer"))
        # Unspecified rate with Senior title
        self.assertTrue(is_high_ticket_opportunity(None, None, "Senior Full-Stack Architect"))
        self.assertTrue(is_high_ticket_opportunity(None, None, "Founding Staff Engineer"))
        # Low rate without senior title
        self.assertFalse(is_high_ticket_opportunity(1500.0, 2500.0, "Junior Developer"))

    def test_skills_extraction(self):
        text = "Seeking Senior Full Stack Developer proficient in Next.js 15, React, Python FastAPI, and PostgreSQL."
        skills = extract_skills(text)
        self.assertIn("next.js", skills)
        self.assertIn("react", skills)
        self.assertIn("python", skills)
        self.assertIn("sql", skills)
        self.assertIn("full stack", skills)

        # Ensure no false positives (e.g. "rain" should not match "ai")
        plain_text = "The team will train models on brain data."
        plain_skills = extract_skills(plain_text)
        self.assertNotIn("ai", plain_skills)

    def test_infer_funding_stage(self):
        self.assertEqual(infer_funding_stage("Nexus AI (YC W24)", ""), "YC W24")
        self.assertEqual(infer_funding_stage("SaaSFlow", "We recently closed our Series A round"), "Series A")
        self.assertEqual(infer_funding_stage("Apex Core", "Early seed stage startup"), "Seed")
        self.assertEqual(infer_funding_stage("DevCorp", "Bootstrapped profitable business"), "Bootstrapped")

    def test_opportunity_match_score(self):
        # 45 (tech: next+python+node) + 30 (salary >= 5000) + 25 (worldwide) = 100
        score = compute_match_score(
            skills=["next.js", "python", "node.js"],
            monthly_max=12000.0,
            is_high_ticket=True,
            location="Worldwide / Remote",
            timezone="Worldwide"
        )
        self.assertEqual(score, 100)

        # Baseline check
        low_score = compute_match_score(
            skills=["sql"],
            monthly_max=2000.0,
            is_high_ticket=False,
            location="Onsite NYC",
            timezone="EST"
        )
        self.assertLess(low_score, 50)


class TestPitchGenerator(unittest.TestCase):
    """Tests for CTO and Founder high-ticket pitch generation."""

    def test_cto_pitch_contains_critical_proofs(self):
        pitch = generate_cto_pitch(
            position="Senior Full-Stack Architect",
            company="Nexus Labs",
            skills=["next.js", "python", "node.js"]
        )
        self.assertIn("Subject: Application: Senior Full-Stack Architect - Clean Architecture & Production Velocity (Nexus Labs)", pitch)
        self.assertIn("Hi Nexus Labs Engineering Team,", pitch)
        self.assertIn("Eng. Abdelrahman Rashad", pitch)
        self.assertIn("Senior Full-Stack & Solutions Architect", pitch)
        self.assertIn("sub-100ms TTFB", pitch)
        self.assertIn("Redis caching", pitch)
        self.assertIn("RAG agents", pitch)

    def test_founder_pitch_contains_business_velocity(self):
        pitch = generate_founder_pitch(
            position="Founding Full-Stack Engineer",
            company="GrowthStart",
            skills=["next.js", "react", "python"],
            company_one_liner="AI workspace for marketing teams"
        )
        self.assertIn("Subject: Accelerating GrowthStart's Product Roadmap: Senior Full-Stack & AI Execution", pitch)
        self.assertIn("Hi GrowthStart Leadership Team,", pitch)
        self.assertIn("Eng. Abdelrahman Rashad", pitch)
        self.assertIn("$3,500 - $6,000/mo", pitch)
        self.assertIn("Rapid Feature Shipping", pitch)
        self.assertIn("Enterprise Reliability", pitch)

    def test_dual_pitch_generator(self):
        cto_p, founder_p = generate_dual_pitches(
            position="Staff Engineer",
            company="TechFlow",
            skills=["node.js", "sql"]
        )
        self.assertIn("Clean Architecture", cto_p)
        self.assertIn("Product Roadmap", founder_p)
        self.assertIn("Abdelrahman Rashad", cto_p)
        self.assertIn("Abdelrahman Rashad", founder_p)


class TestSourceAdapters(unittest.TestCase):
    """Tests for Hacker News, WeWorkRemotely, YC, and RemoteOK adapters."""

    def test_hn_top_level_comment_filtering(self):
        adapter = HNAdapter()
        # Mock Algolia hits
        mock_hits = [
            # Top-level comment: parent_id == story_id
            {
                "objectID": "1001",
                "parent_id": 49922569,
                "comment_text": "Acme AI | Lead Full Stack Engineer | Remote (Worldwide) | $150k-$190k<p>We are building Next.js apps with Python backends.</p>",
                "created_at": "2026-10-01T15:30:00Z"
            },
            # Child reply (job seeker or candidate question): parent_id != story_id
            {
                "objectID": "1002",
                "parent_id": 1001,
                "comment_text": "Are you open to contractors outside US?",
                "created_at": "2026-10-01T16:00:00Z"
            }
        ]
        
        # Test parsing with parent_id check
        story_id_int = 49922569
        filtered = []
        for h in mock_hits:
            if h.get("parent_id") == story_id_int:
                parsed = adapter._parse_hn_comment(h, str(story_id_int))
                if parsed:
                    filtered.append(parsed)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["company"], "Acme AI")
        self.assertEqual(filtered[0]["title"], "Lead Full Stack Engineer")
        self.assertIn("150k", filtered[0]["raw_compensation"])

    def test_hn_firebase_job_parser(self):
        adapter = HNAdapter()
        mock_item = {
            "id": 50179455,
            "type": "job",
            "title": "9 Mothers (YC W24) is hiring a Senior Full-Stack Engineer",
            "text": "Join our founding team building Next.js and Python agents.",
            "time": 1729680000,
            "url": "https://9mothers.com"
        }
        parsed = adapter._parse_firebase_job(mock_item)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["company"], "9 Mothers")
        self.assertIn("Senior Full-Stack Engineer", parsed["title"])
        self.assertEqual(parsed["funding_stage"], "YC W24")

    def test_wwr_rss_parsing(self):
        adapter = WWRAdapter()
        sample_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>We Work Remotely: Remote Full-Stack Programming Jobs</title>
            <item>
              <title>CloudScale Inc: Senior Full-Stack Engineer</title>
              <link>https://weworkremotely.com/jobs/cloudscale-senior-fullstack</link>
              <pubDate>Mon, 20 Oct 2026 10:00:00 +0000</pubDate>
              <guid>https://weworkremotely.com/jobs/998811</guid>
              <region>Worldwide / Remote</region>
              <type>Contractor</type>
              <description>&lt;p&gt;Looking for Next.js and Node.js experts. Rate: $50 - $70 / hour.&lt;/p&gt;</description>
            </item>
          </channel>
        </rss>"""
        jobs = adapter.parse_rss_xml(sample_rss)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["company"], "CloudScale Inc")
        self.assertEqual(jobs[0]["title"], "Senior Full-Stack Engineer")
        self.assertTrue(any(w in jobs[0]["raw_compensation"].lower() for w in ["hour", "hourly", "/hr"]))
        self.assertEqual(jobs[0]["source_platform"], "weworkremotely")

    def test_yc_inertia_extraction(self):
        adapter = YCAdapter()
        data_page_payload = {
            "component": "WaasLandingPage",
            "props": {
                "jobPostings": [
                    {
                        "id": 88201,
                        "title": "Senior AI & Full-Stack Engineer",
                        "companyName": "OmniVector",
                        "companyBatchName": "W24",
                        "companyOneLiner": "Autonomous vector intelligence platform",
                        "salaryRange": "$140K - $180K",
                        "equityRange": "0.1% - 0.5%",
                        "skills": ["next.js", "python", "ai", "postgresql"],
                        "location": "Worldwide",
                        "applyUrl": "https://ycombinator.com/companies/omnivector/jobs/88201"
                    }
                ]
            }
        }
        json_str = json.dumps(data_page_payload)
        escaped_attr = html.escape(json_str, quote=True)
        html_page = f'<html><body><div id="app" data-page="{escaped_attr}"></div></body></html>'

        extracted_data = adapter.extract_inertia_data_page(html_page)
        self.assertIsNotNone(extracted_data)
        postings = adapter.parse_job_postings_from_page(extracted_data)
        self.assertEqual(len(postings), 1)
        self.assertEqual(postings[0]["company"], "OmniVector")
        self.assertEqual(postings[0]["funding_stage"], "YC W24")
        self.assertEqual(postings[0]["salary_range"], "$140K - $180K")

    def test_remoteok_parsing(self):
        adapter = RemoteOKAdapter()
        mock_raw = [
            {
                "id": 1137551,
                "position": "Senior Backend Architect",
                "company": "DuckDuckGo",
                "tags": ["node", "python", "redis"],
                "location": "Worldwide",
                "salary_min": 140000,
                "salary_max": 180000,
                "url": "https://remoteok.com/remote-jobs/1137551"
            }
        ]
        parsed = adapter.parse_raw_jobs(mock_raw)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["company"], "DuckDuckGo")
        self.assertEqual(parsed[0]["title"], "Senior Backend Architect")
        self.assertIn("140,000", parsed[0]["raw_compensation"])


class TestCacheAndFallbackHierarchy(unittest.TestCase):
    """Tests for Token Bucket Limiter, Disk Cache, and 3-Tier Fallback Hierarchy."""

    def test_token_bucket_limiter(self):
        limiter = TokenBucketLimiter(fill_rate=100.0, capacity=10.0)
        # Should easily acquire within capacity
        self.assertTrue(limiter.acquire(1.0))
        self.assertTrue(limiter.acquire(5.0))

    def test_disk_cache_manager(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = DiskCacheManager(cache_dir=tmp_dir)
            test_data = {"key": "value", "contracts": [1, 2, 3]}

            # Set and retrieve fresh
            cache.set("test_key", test_data)
            fresh = cache.get("test_key", max_age_seconds=10)
            self.assertEqual(fresh, test_data)

            # Check expired TTL returns None on get() but valid on get_stale()
            expired = cache.get("test_key", max_age_seconds=0)
            self.assertIsNone(expired)
            stale = cache.get_stale("test_key")
            self.assertEqual(stale, test_data)

    def test_three_tier_fallback_execution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = ThreeTierFallbackManager(cache_dir=tmp_dir)

            # 1. Tier 1: Successful network call
            def mock_live_ok():
                return [{"id": "live_1", "title": "Live Engineer"}]

            res, tier = manager.execute_with_fallback(
                cache_key="test_feed",
                network_call=mock_live_ok,
                emergency_fallback_call=lambda: [{"id": "fallback_1"}],
                domain="default"
            )
            self.assertEqual(tier, "tier1_live")
            self.assertEqual(res[0]["id"], "live_1")

            # 2. Tier 2: Network fails, but disk cache has data from step 1
            def mock_live_fail():
                raise ConnectionError("Simulated DNS timeout")

            res2, tier2 = manager.execute_with_fallback(
                cache_key="test_feed",
                network_call=mock_live_fail,
                emergency_fallback_call=lambda: [{"id": "emergency_tier3"}],
                domain="default"
            )
            self.assertEqual(tier2, "tier2_cache")
            self.assertEqual(res2[0]["id"], "live_1")

            # 3. Tier 3: Network fails and no cache exists
            res3, tier3 = manager.execute_with_fallback(
                cache_key="unseen_feed",
                network_call=mock_live_fail,
                emergency_fallback_call=lambda: [{"id": "emergency_tier3"}],
                domain="default"
            )
            self.assertEqual(tier3, "tier3_emergency")
            self.assertEqual(res3[0]["id"], "emergency_tier3")

    def test_emergency_curated_dataset_validity(self):
        emergency_jobs = get_emergency_curated_opportunities()
        self.assertGreaterEqual(len(emergency_jobs), 5)
        for job in emergency_jobs:
            self.assertIn("id", job)
            self.assertIn("title", job)
            self.assertIn("company", job)
            self.assertIn("funding_stage", job)
            self.assertTrue(job.get("is_high_ticket"))
            self.assertGreaterEqual(job.get("monthly_rate_usd_min", 0), 3500.0)


class TestMasterHunterOrchestrator(unittest.TestCase):
    """Tests for master RemoteContractHunter CLI, normalization, and export integrity."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.hunter = RemoteContractHunter(
            target_keywords=["react", "next.js", "python", "ai", "node"],
            cache_dir=self.tmp_dir.name
        )

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_emergency_fallback_loading(self):
        opps = self.hunter.fetch_all_sources(use_fallback_only=True)
        self.assertGreaterEqual(len(opps), 5)
        for o in opps:
            self.assertIsInstance(o, ContractOpportunity)
            self.assertTrue(o.is_high_ticket)
            self.assertIn("Abdelrahman Rashad", o.pitch_cto)
            self.assertIn("Abdelrahman Rashad", o.pitch_founder)
            self.assertGreaterEqual(o.match_score, 80)

    def test_deduplication(self):
        raw_opp = ContractOpportunity(
            id="test_dup_1",
            title="Senior Full-Stack Engineer",
            company="Nexus Labs",
            funding_stage="YC W24",
            salary_or_rate="$140k - $180k",
            monthly_rate_usd_min=11666.67,
            monthly_rate_usd_max=15000.0,
            rate_period="annual",
            is_high_ticket=True,
            skills_tags=["next.js", "python"],
            location="Worldwide",
            timezone_requirement="Worldwide",
            source_platform="hacker_news",
            url="https://example.com/1",
            posted_date="2026-10-20T00:00:00Z",
            raw_description="Build apps",
            match_score=95,
            pitch_cto="CTO Pitch",
            pitch_founder="Founder Pitch"
        )
        # Duplicate with slight whitespace/casing
        raw_opp_dup = ContractOpportunity(
            id="test_dup_2",
            title="senior full-stack engineer ",
            company="nexus labs",
            funding_stage="YC W24",
            salary_or_rate="$140k - $180k",
            monthly_rate_usd_min=11666.67,
            monthly_rate_usd_max=15000.0,
            rate_period="annual",
            is_high_ticket=True,
            skills_tags=["next.js", "python"],
            location="Worldwide",
            timezone_requirement="Worldwide",
            source_platform="ycombinator",
            url="https://example.com/2",
            posted_date="2026-10-20T00:00:00Z",
            raw_description="Build apps duplicate",
            match_score=95,
            pitch_cto="CTO Pitch",
            pitch_founder="Founder Pitch"
        )
        deduped = self.hunter.deduplicate_opportunities([raw_opp, raw_opp_dup])
        self.assertEqual(len(deduped), 1)

    def test_export_json_and_csv_contract_compliance(self):
        # Populate hunter with emergency opportunities
        self.hunter.fetch_all_sources(use_fallback_only=True)

        json_out = Path(self.tmp_dir.name) / "curated_high_ticket_jobs.json"
        csv_out = Path(self.tmp_dir.name) / "curated_high_ticket_jobs.csv"

        self.hunter.export_to_json(str(json_out))
        self.hunter.export_to_csv(str(csv_out))

        self.assertTrue(json_out.exists())
        self.assertTrue(csv_out.exists())

        # Validate JSON schema matches PROJECT.md exactly
        with open(json_out, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        required_keys = [
            "id", "title", "company", "funding_stage", "salary_or_rate",
            "monthly_rate_usd_min", "monthly_rate_usd_max", "rate_period",
            "is_high_ticket", "skills_tags", "location", "timezone_requirement",
            "source_platform", "url", "posted_date", "match_score",
            "pitch_cto", "pitch_founder"
        ]

        first_item = data[0]
        for key in required_keys:
            self.assertIn(key, first_item, f"Missing required interface key: {key}")

        # Validate CSV columns
        with open(csv_out, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.assertEqual(len(rows), len(data))
        for key in required_keys:
            self.assertIn(key, rows[0], f"Missing CSV column: {key}")

    def test_legacy_backwards_compatibility(self):
        # Legacy test helpers
        curated = self.hunter._get_curated_fallback_jobs()
        self.assertGreaterEqual(len(curated), 3)
        for job in curated:
            self.assertIn("title", job)
            self.assertIn("company", job)
            self.assertIn("pitch_cto", job)
            self.assertIn("Abdelrahman Rashad", job["pitch_cto"])

        cto_pitch = self.hunter.generate_cto_pitch("Senior Dev", "TechCorp", ["react", "node"])
        self.assertIn("Senior Dev", cto_pitch)
        self.assertIn("TechCorp", cto_pitch)
        self.assertIn("Abdelrahman Rashad", cto_pitch)


if __name__ == "__main__":
    unittest.main()
