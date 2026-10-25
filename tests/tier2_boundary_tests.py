"""
Tier 2: Boundary & Corner Cases Test Suite
==========================================
Master E2E Testing Suite - Milestone 4
Validates system behavior under boundary, extreme, and adversarial conditions:
1. Hunter: Timeouts, network errors, corrupt feeds, salary boundaries ($3,499.99 vs $3,500.00).
2. RAG & SafeSQL: SQL injection barrier, stacked queries, comments, empty & zero-match queries.
3. Scraper: Malformed/unclosed HTML, rapid token bucket exhaustion, quarantine of corrupt data.
4. Cockpit API: Zero-leads division by zero, invalid stage transitions (400), nonexistent IDs (404),
   negative monthly values (422), and extreme pitch input payloads.

Author: Eng. Abdelrahman Rashad & QA Automation Track
"""

import sys
import os
import unittest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch
import urllib.error

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contract_hunter.normalizer import (
    parse_salary,
    is_high_ticket_opportunity,
    compute_match_score,
)
from contract_hunter.remote_contract_hunter import RemoteContractHunter
from contract_hunter.cache_manager import (
    TokenBucketLimiter as HunterTokenLimiter,
    DiskCacheManager,
    ThreeTierFallbackManager,
)
from ai_solutions_suite.ai_agent_rag.rag_agent import EnterpriseRAGAgent
from ai_solutions_suite.ai_agent_rag.safe_sql_executor import (
    SafeSQLExecutor,
    SecurityViolationError,
)
from ai_solutions_suite.python_scraper_engine.rate_limiter import TokenBucketRateLimiter
from ai_solutions_suite.python_scraper_engine.scraper_engine import ScraperPipeline
from ai_solutions_suite.python_scraper_engine.normalizer import DataNormalizer
from cockpit.server import app, load_pipeline_data, atomic_save_json, PIPELINE_FILE
from starlette.testclient import TestClient


class TestHunterBoundaries(unittest.TestCase):
    """Tier 2: Hunter Boundary & Fault Tolerance Tests."""

    def test_salary_parsing_empty_and_garbage_input(self):
        # Empty string
        min_usd, max_usd, period, matched = parse_salary("")
        self.assertIsNone(min_usd)
        self.assertIsNone(max_usd)
        self.assertEqual(period, "unspecified")

        # None value
        min_usd, max_usd, period, matched = parse_salary(None)
        self.assertIsNone(min_usd)
        self.assertIsNone(max_usd)
        self.assertEqual(period, "unspecified")

        # Garbage / non-numeric text
        min_usd, max_usd, period, matched = parse_salary("Competitive package with equity and snacks")
        self.assertIsNone(min_usd)
        self.assertIsNone(max_usd)
        self.assertEqual(period, "unspecified")

    def test_high_ticket_threshold_boundary(self):
        # Boundary: $3,499.99 is below threshold; $3,500.00 is at threshold
        self.assertFalse(is_high_ticket_opportunity(3000.0, 3499.99, title="Software Engineer"))
        self.assertTrue(is_high_ticket_opportunity(3000.0, 3500.00, title="Software Engineer"))
        self.assertTrue(is_high_ticket_opportunity(3500.0, 4500.00, title="Software Engineer"))

    def test_match_score_bounds(self):
        # Empty inputs should yield minimum bounded score (clamped >= 0)
        score_min = compute_match_score([], 0.0, False, "Local Only", "UTC+12")
        self.assertGreaterEqual(score_min, 0)
        self.assertLessEqual(score_min, 100)

        # Extreme high-value inputs should be clamped at 100
        score_max = compute_match_score(
            ["next.js", "react", "node.js", "python", "ai", "sql", "full stack"],
            25000.0,
            True,
            "Worldwide",
            "Global Remote"
        )
        self.assertEqual(score_max, 100)

    def test_network_failure_emergency_fallback(self):
        # Simulating live HTTP 500 / DNS drop on remoteok fetch
        hunter = RemoteContractHunter()
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Simulated Network Timeout")):
            jobs = hunter.fetch_remoteok_jobs(limit=10) if hasattr(hunter, "fetch_remoteok_jobs") else hunter.fetch_jobs(limit=10)
            self.assertIsInstance(jobs, list)
            self.assertGreaterEqual(len(jobs), 1, "Must serve emergency fallback on network failure")
            # Verify jobs contain genuine high-ticket contracts
            first_job = jobs[0]
            title = first_job.get("title") or first_job.get("position", "")
            self.assertTrue(len(title) > 0)

    def test_fallback_manager_resilience(self):
        # Test ThreeTierFallbackManager with failing live function
        fallback_mgr = ThreeTierFallbackManager()

        def failing_live_fetch():
            raise TimeoutError("Network partition occurred")

        def emergency_fallback():
            return [{"id": "emerg-01", "title": "Emergency Fallback Lead"}]

        result, tier_used = fallback_mgr.execute_with_fallback(
            cache_key="test_emergency_key",
            network_call=failing_live_fetch,
            emergency_fallback_call=emergency_fallback,
            domain="test_domain",
            ttl_seconds=60
        )
        self.assertIn(tier_used, ["tier2_cached", "tier3_emergency"])
        self.assertGreaterEqual(len(result), 1)


class TestRAGAndSafeSQLSecurityBoundaries(unittest.TestCase):
    """Tier 2: RAG Empty/Alien Queries & SafeSQL Barrier Tests."""

    def setUp(self):
        self.agent = EnterpriseRAGAgent(mock_mode=True)
        self.executor = SafeSQLExecutor(default_limit=20, max_limit=100)

    def test_rag_empty_and_whitespace_query(self):
        # Empty query should return empty list gracefully without exception
        res_empty = self.agent.retrieve("")
        self.assertEqual(res_empty, [])

        res_spaces = self.agent.retrieve("     \n\t   ")
        self.assertEqual(res_spaces, [])

    def test_rag_alien_and_zero_match_query(self):
        # Query with unindexed symbols/gibberish should return empty list without index errors
        res_gibberish = self.agent.retrieve("qxzjjk128947 !@#$%^&*()_+")
        self.assertEqual(res_gibberish, [])

    def test_safesql_barrier_blocks_destructive_mutations(self):
        destructive_injections = [
            "DROP TABLE enterprise_orders",
            "DELETE FROM enterprise_orders WHERE 1=1",
            "UPDATE enterprise_orders SET total_usd = 999999",
            "INSERT INTO enterprise_orders (customer_name) VALUES ('Adversary')",
            "ALTER TABLE enterprise_orders ADD COLUMN pwned TEXT",
            "TRUNCATE TABLE enterprise_orders",
            "ATTACH DATABASE 'hacked.db' AS hacked",
            "PRAGMA table_info(enterprise_orders)",
        ]

        for query in destructive_injections:
            is_valid, reason = self.executor.validate_query(query)
            self.assertFalse(is_valid, f"Expected destructive query to be blocked: {query}")
            with self.assertRaises(SecurityViolationError):
                self.executor.execute(self.agent.db_source, query)

    def test_safesql_barrier_blocks_stacked_queries(self):
        # Multiple statements separated by semicolon
        stacked_query = "SELECT * FROM enterprise_orders; DROP TABLE enterprise_orders;"
        is_valid, reason = self.executor.validate_query(stacked_query)
        self.assertFalse(is_valid)
        self.assertIn("Stacked queries", reason)
        with self.assertRaises(SecurityViolationError):
            self.executor.execute(self.agent.db_source, stacked_query)

    def test_safesql_barrier_blocks_sql_comments(self):
        # SQL comments used to mask payloads
        commented_queries = [
            "SELECT * FROM enterprise_orders -- bypass comment",
            "SELECT * FROM enterprise_orders /* multiline comment */",
        ]
        for query in commented_queries:
            is_valid, reason = self.executor.validate_query(query)
            self.assertFalse(is_valid)
            self.assertIn("SQL comments", reason)
            with self.assertRaises(SecurityViolationError):
                self.executor.execute(self.agent.db_source, query)

    def test_safesql_limit_clamping_boundary(self):
        # When user requests 500 rows but max_limit is 100
        res = self.executor.execute(self.agent.db_source, "SELECT * FROM enterprise_orders LIMIT 500")
        self.assertIn("LIMIT 100", res["executed_sql"])


class TestScraperBoundaries(unittest.TestCase):
    """Tier 2: Scraper Pipeline Fault Tolerance & Limit Tests."""

    def test_scraper_corrupted_and_empty_html(self):
        scraper = ScraperPipeline(target_domain="resilient-test.com")

        # 1. Empty HTML
        res_empty = scraper.process_raw_html("")
        self.assertEqual(res_empty, [])

        # 2. Corrupt / unclosed HTML snippet
        corrupt_html = '<div class="item-card"><span class="title">Unclosed Card without closing tags...'
        res_corrupt = scraper.process_raw_html(corrupt_html)
        self.assertIsInstance(res_corrupt, list)

        # 3. HTML with no matching entities
        plain_html = "<html><body><p>Just plain text with no structured cards or headings.</p></body></html>"
        res_plain = scraper.process_raw_html(plain_html)
        self.assertIsInstance(res_plain, list)

    def test_rate_limiter_excessive_token_request_rejection(self):
        limiter = TokenBucketRateLimiter(rate=5.0, capacity=10.0)
        # Requesting 15 tokens when capacity is 10 must raise ValueError
        with self.assertRaises(ValueError):
            limiter.acquire(tokens=15.0)

    def test_rate_limiter_rapid_depletion(self):
        limiter = TokenBucketRateLimiter(rate=1.0, capacity=2.0)
        # Acquire all available tokens
        acquired_first = limiter.acquire(tokens=2.0, block=False)
        self.assertTrue(acquired_first)

        # Subsequent immediate acquisition should fail without blocking
        acquired_second = limiter.acquire(tokens=1.0, block=False)
        self.assertFalse(acquired_second)


class TestCockpitAPIBoundaries(unittest.TestCase):
    """Tier 2: Cockpit REST API Edge Cases & Defensive Invariants."""

    def setUp(self):
        self.client = TestClient(app)

    def test_pipeline_zero_leads_division_by_zero_prevention(self):
        # Temporarily test metrics with zero deals
        original_data = load_pipeline_data()
        try:
            # Emulate clean empty pipeline
            empty_state = {"version": "1.0.0", "updated_at": "2026-10-23T00:00:00Z", "deals": []}
            atomic_save_json(PIPELINE_FILE, empty_state)

            res = self.client.get("/api/metrics")
            self.assertEqual(res.status_code, 200)
            metrics = res.json()
            self.assertEqual(metrics["total_deals"], 0)
            self.assertEqual(metrics["active_monthly_revenue"], 0.0)
            self.assertEqual(metrics["in_flight_pipeline_value"], 0.0)
            self.assertEqual(metrics["win_rate"], 0.0)  # Must be 0.0, NOT NaN or ZeroDivisionError
        finally:
            atomic_save_json(PIPELINE_FILE, original_data)

    def test_pipeline_invalid_stage_transition_returns_400(self):
        # Act: Try to create a deal with an illegitimate stage
        invalid_deal = {
            "title": "Invalid Role",
            "company": "Fictional Corp",
            "stage": "fictional_unsupported_stage",
            "monthly_value": 4500.0
        }
        res = self.client.post("/api/pipeline", json=invalid_deal)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid stage", res.json()["detail"])

    def test_pipeline_update_nonexistent_deal_returns_404(self):
        # Act: Update a non-existent deal ID
        res = self.client.put("/api/pipeline/deal-non-existent-9999", json={"stage": "won"})
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"])

    def test_pipeline_delete_nonexistent_deal_returns_404(self):
        # Act: Delete a non-existent deal ID
        res = self.client.delete("/api/pipeline/deal-non-existent-9999")
        self.assertEqual(res.status_code, 404)

    def test_pipeline_negative_monthly_value_returns_422(self):
        # Act: Monthly value cannot be negative
        invalid_deal = {
            "title": "Negative Contract",
            "company": "Bad Data Corp",
            "stage": "leads",
            "monthly_value": -1500.0
        }
        res = self.client.post("/api/pipeline", json=invalid_deal)
        self.assertEqual(res.status_code, 422)

    def test_pitch_generator_extreme_notes_payload(self):
        # Act: Provide massive 15,000-character custom notes
        massive_notes = "Scalable high-availability distributed architecture. " * 300
        payload = {
            "position": "Staff Engineer",
            "company": "DeepTech Enterprise",
            "skills": ["next.js", "python", "ai"],
            "tone": "founder",
            "custom_notes": massive_notes
        }
        res = self.client.post("/api/pitch/generate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("DeepTech Enterprise", data["body"])
        self.assertGreater(data["char_count"], len(massive_notes))


if __name__ == "__main__":
    unittest.main()
