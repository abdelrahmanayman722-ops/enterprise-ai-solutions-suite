"""
Adversarial Stress Test Suite & Security Validation Harness
===========================================================
Empirical challenger stress-testing SafeSQLExecutor, Scraper Rate Limiter & Anti-Detection,
and Hunter Salary Normalization Edge Cases.

Author: Challenger 1 (Empirical Challenger & Adversarial Specialist)
"""

import unittest
import sqlite3
import threading
import time
import re
import math
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_solutions_suite.ai_agent_rag.safe_sql_executor import (
    SafeSQLExecutor,
    SecurityViolationError
)
from ai_solutions_suite.ai_agent_rag.rag_agent import EnterpriseRAGAgent
from ai_solutions_suite.python_scraper_engine.rate_limiter import TokenBucketRateLimiter
from ai_solutions_suite.python_scraper_engine.anti_detection import AntiDetectionEngine
from contract_hunter.normalizer import (
    parse_salary,
    is_high_ticket_opportunity,
    extract_skills,
    infer_funding_stage,
    compute_match_score,
    CURRENCY_RATES
)


class TestSafeSQLExecutorAdversarial(unittest.TestCase):
    """Adversarial security audit & stress testing of SafeSQLExecutor."""

    def setUp(self):
        self.agent = EnterpriseRAGAgent(mock_mode=True)
        self.db = self.agent.db_source
        self.executor = SafeSQLExecutor(default_limit=50, max_limit=200)

    # 1. Stacked Queries & Multiple Statement Attacks
    def test_stacked_queries_semicolon_variations(self):
        stacked_payloads = [
            "SELECT 1; DROP TABLE enterprise_orders",
            "SELECT 1;\nDROP TABLE enterprise_orders",
            "SELECT 1;\tDROP TABLE enterprise_orders",
            "SELECT 1;\r\nDROP TABLE enterprise_orders",
            "SELECT 1; ; DROP TABLE enterprise_orders",
            "SELECT 1;;DROP TABLE enterprise_orders",
            "SELECT * FROM enterprise_orders; DELETE FROM ai_agents;",
            "SELECT 1; SELECT 2;",
            "SELECT 1; VACUUM;",
            "SELECT 1; PRAGMA foreign_keys = OFF;",
        ]
        for payload in stacked_payloads:
            with self.subTest(payload=payload):
                is_valid, reason = self.executor.validate_query(payload)
                self.assertFalse(is_valid, f"Expected stacked query to be rejected: {payload}")
                with self.assertRaises(SecurityViolationError):
                    self.executor.execute(self.db, payload)

    def test_trailing_semicolon_normalization(self):
        # Single trailing semicolon should be permitted as standard SQL practice
        valid_query = "SELECT order_id, customer_name FROM enterprise_orders WHERE status = 'completed';"
        is_valid, reason = self.executor.validate_query(valid_query)
        self.assertTrue(is_valid, f"Trailing semicolon should be accepted: {reason}")
        res = self.executor.execute(self.db, valid_query)
        self.assertGreaterEqual(res["row_count"], 1)

        # Multiple trailing semicolons must be rejected
        double_semicolon = "SELECT order_id FROM enterprise_orders;;"
        is_valid, reason = self.executor.validate_query(double_semicolon)
        self.assertFalse(is_valid, "Multiple trailing semicolons must be rejected")

    def test_embedded_semicolon_in_string_literal(self):
        # Strict defense-in-depth: semicolons are forbidden anywhere to prevent stacked escapes
        query = "SELECT 'item1;item2' AS test_col FROM enterprise_orders"
        is_valid, reason = self.executor.validate_query(query)
        self.assertFalse(is_valid, "Strict rule should reject any embedded semicolon")

    # 2. Nested Comments and Token Obfuscation Attacks
    def test_nested_and_varied_sql_comments(self):
        comment_payloads = [
            "SELECT * FROM enterprise_orders -- bypass comment",
            "SELECT * FROM enterprise_orders /* multiline comment */",
            "SELECT /* inner comment */ total_usd FROM enterprise_orders",
            "SELECT /* outer /* nested */ outer */ total_usd FROM enterprise_orders",
            "SELECT * FROM enterprise_orders /*!",
            "SELECT * FROM enterprise_orders */",
            "SELECT 1 /*!50000 SELECT 2 */",
            "SELECT 1 --\nWHERE 1=1",
            "SELECT 1 /* comment \n with \n newlines */ FROM enterprise_orders",
        ]
        for payload in comment_payloads:
            with self.subTest(payload=payload):
                is_valid, reason = self.executor.validate_query(payload)
                self.assertFalse(is_valid, f"SQL comment injection must be blocked: {payload}")
                self.assertIn("SQL comments", reason)
                with self.assertRaises(SecurityViolationError):
                    self.executor.execute(self.db, payload)

    # 3. Disguised Keywords & Identifier Boundary Attacks
    def test_disguised_keywords_and_case_manipulation(self):
        destructive_keywords = [
            "select 1; dRoP tAbLe enterprise_orders",
            "select 1; uPdAtE enterprise_orders SET total_usd = 0",
            "select 1; dElEtE FROM enterprise_orders",
            "select 1; iNsErT INTO enterprise_orders VALUES (1,'hacked',0,'x')",
            "select 1; aLtEr TABLE enterprise_orders ADD COLUMN x INT",
            "select 1; tRuNcAtE TABLE enterprise_orders",
            "select 1; aTtAcH DATABASE 'malicious.db' AS mal",
            "select 1; pRaGmA integrity_check",
            "select 1; eXeCuTe ('DROP TABLE enterprise_orders')",
        ]
        for payload in destructive_keywords:
            with self.subTest(payload=payload):
                is_valid, reason = self.executor.validate_query(payload)
                self.assertFalse(is_valid, f"Case-variant destructive keyword must be blocked: {payload}")
                with self.assertRaises(SecurityViolationError):
                    self.executor.execute(self.db, payload)

    def test_legitimate_columns_with_embedded_keyword_substrings(self):
        # Column names containing keyword substrings (e.g. drop_rate, create_time, insert_count)
        # MUST NOT be falsely blocked if word boundaries are respected.
        valid_queries = [
            "SELECT customer_name AS created_by FROM enterprise_orders",
            "SELECT total_usd AS updated_amount FROM enterprise_orders",
        ]
        for query in valid_queries:
            with self.subTest(query=query):
                is_valid, reason = self.executor.validate_query(query)
                self.assertTrue(is_valid, f"False positive blocked query: {query} (Reason: {reason})")
                res = self.executor.execute(self.db, query)
                self.assertGreaterEqual(res["row_count"], 1)

    # 4. UNION Extractions & Compound Queries
    def test_union_query_read_only_and_limit_enforcement(self):
        # Read-only UNION query between tables
        union_query = (
            "SELECT customer_name AS name, total_usd AS val FROM enterprise_orders "
            "UNION SELECT agent_name AS name, throughput_rps AS val FROM ai_agents"
        )
        is_valid, reason = self.executor.validate_query(union_query)
        self.assertTrue(is_valid, f"Read-only UNION query should be valid: {reason}")
        res = self.executor.execute(self.db, union_query)
        self.assertGreater(res["row_count"], 0)
        self.assertIn("LIMIT 50", res["executed_sql"])

        # Destructive statement disguised in UNION must be blocked
        malicious_union = "SELECT 1 UNION INSERT INTO enterprise_orders (customer_name) VALUES ('Adversary')"
        is_valid, reason = self.executor.validate_query(malicious_union)
        self.assertFalse(is_valid, "Malicious UNION with INSERT must be blocked")

    def test_union_query_limit_clamping(self):
        # Even with UNION, excessive LIMIT must be clamped to max_limit (200)
        query = (
            "SELECT customer_name AS name FROM enterprise_orders "
            "UNION SELECT agent_name AS name FROM ai_agents LIMIT 99999"
        )
        is_valid, reason = self.executor.validate_query(query)
        self.assertTrue(is_valid)
        res = self.executor.execute(self.db, query)
        self.assertIn("LIMIT 200", res["executed_sql"])

    def test_schema_exfiltration_via_sqlite_master(self):
        # Reading schema via UNION is syntactically a read-only SELECT
        query = "SELECT name, type FROM sqlite_master WHERE type='table'"
        is_valid, reason = self.executor.validate_query(query)
        self.assertTrue(is_valid)
        res = self.executor.execute(self.db, query)
        table_names = [row["name"] for row in res["rows"]]
        self.assertIn("enterprise_orders", table_names)

    # 5. Buffer Overflow, Extreme Length & Non-SELECT Statements
    def test_large_buffer_query(self):
        # 50,000 character query should not cause ReDoS or stack overflow
        long_string = "A" * 50000
        query = f"SELECT '{long_string}' AS buffer_test FROM enterprise_orders"
        is_valid, reason = self.executor.validate_query(query)
        self.assertTrue(is_valid)
        start = time.perf_counter()
        res = self.executor.execute(self.db, query)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 1.0, "Large query execution took too long (possible ReDoS)")
        self.assertEqual(len(res["rows"][0]["buffer_test"]), 50000)

    def test_non_select_statements_rejected(self):
        invalid_statements = [
            "EXPLAIN SELECT * FROM enterprise_orders",
            "SHOW TABLES",
            "CALL my_procedure()",
            "GRANT ALL PRIVILEGES ON *.* TO 'user'@'localhost'",
            "SET foreign_key_checks = 0",
            "",
            "   \t\n  ",
        ]
        for stmt in invalid_statements:
            with self.subTest(stmt=stmt):
                is_valid, reason = self.executor.validate_query(stmt)
                self.assertFalse(is_valid, f"Statement should be rejected: '{stmt}'")


class TestScraperRateLimiterAndAntiDetectionAdversarial(unittest.TestCase):
    """Stress testing Token Bucket rate limiter and Anti-Detection Engine under extreme load."""

    # 1. TokenBucket Concurrent Burst & Depletion Stress
    def test_token_bucket_high_concurrency_burst(self):
        rate = 20.0
        capacity = 25.0
        limiter = TokenBucketRateLimiter(rate=rate, capacity=capacity)

        acquired_count = 0
        lock = threading.Lock()

        def worker():
            nonlocal acquired_count
            # Attempt to acquire 1 token non-blocking
            if limiter.acquire(tokens=1.0, block=False):
                with lock:
                    acquired_count += 1

        # Launch 100 concurrent threads simultaneously
        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Acquired tokens must never exceed initial capacity in instantaneous burst
        self.assertLessEqual(acquired_count, int(capacity) + 1)
        self.assertGreaterEqual(limiter.tokens_available(), 0.0, "Bucket must never overdraft")

    def test_token_bucket_replenishment_rate_accuracy(self):
        rate = 10.0  # 10 tokens per second
        capacity = 10.0
        limiter = TokenBucketRateLimiter(rate=rate, capacity=capacity)

        # Deplete all tokens
        limiter.acquire(tokens=10.0, block=False)
        self.assertLess(limiter.tokens_available(), 1.0)

        # Sleep 0.25 seconds -> expected ~2.5 tokens added
        time.sleep(0.25)
        available = limiter.tokens_available()
        self.assertGreaterEqual(available, 1.8)
        self.assertLessEqual(available, 3.5)

    def test_token_bucket_rapid_blocking_timeout(self):
        limiter = TokenBucketRateLimiter(rate=1.0, capacity=2.0)
        # Drain bucket
        limiter.acquire(tokens=2.0, block=False)

        # Try to acquire 2 tokens with 0.05s timeout (requires 2.0s to replenish)
        start = time.perf_counter()
        success = limiter.acquire(tokens=2.0, block=True, timeout=0.05)
        elapsed = time.perf_counter() - start

        self.assertFalse(success, "Should fail when timeout is shorter than replenishment time")
        self.assertLess(elapsed, 0.2, "Timeout must return promptly")

    def test_token_bucket_invalid_arguments(self):
        with self.assertRaises(ValueError):
            TokenBucketRateLimiter(rate=0.0, capacity=10.0)
        with self.assertRaises(ValueError):
            TokenBucketRateLimiter(rate=5.0, capacity=0.5)

        limiter = TokenBucketRateLimiter(rate=5.0, capacity=10.0)
        with self.assertRaises(ValueError):
            limiter.acquire(tokens=15.0)  # Exceeds total capacity

        # Zero or negative tokens should return True immediately without consuming
        tokens_before = limiter.tokens_available()
        self.assertTrue(limiter.acquire(tokens=0.0))
        self.assertTrue(limiter.acquire(tokens=-2.0))
        self.assertAlmostEqual(limiter.tokens_available(), tokens_before, places=1)

    # 2. AntiDetectionEngine Burst & Header Consistency
    def test_antidetection_burst_header_generation(self):
        engine = AntiDetectionEngine()
        seen_user_agents = set()
        total_runs = 500

        for i in range(total_runs):
            referer = "https://example.com/source" if i % 2 == 0 else None
            headers = engine.get_headers(referer=referer)

            # Mandatory browser fidelity headers
            self.assertIn("User-Agent", headers)
            self.assertIn("Accept", headers)
            self.assertIn("Accept-Language", headers)
            self.assertIn("Accept-Encoding", headers)
            self.assertIn("Connection", headers)
            self.assertIn("Sec-Fetch-Dest", headers)
            self.assertIn("Sec-Fetch-Mode", headers)
            self.assertEqual(headers["DNT"], "1")

            ua = headers["User-Agent"]
            seen_user_agents.add(ua)

            # Synchronized Client Hints verification
            if "Chrome" in ua and "Safari" in ua and "Firefox" not in ua and "Version/" not in ua:
                self.assertIn("Sec-CH-UA", headers, "Chromium must emit Sec-CH-UA")
                self.assertIn("Sec-CH-UA-Mobile", headers)
                self.assertIn("Sec-CH-UA-Platform", headers)
            elif "Firefox" in ua or "Version/" in ua:
                # Firefox and Safari do not emit Chromium Sec-CH-UA headers
                self.assertNotIn("Sec-CH-UA", headers, "Safari/Firefox must NOT emit Sec-CH-UA")

            # Referer and Fetch-Site validation
            if referer:
                self.assertEqual(headers["Referer"], referer)
                self.assertEqual(headers["Sec-Fetch-Site"], "same-origin")
            else:
                self.assertNotIn("Referer", headers)
                self.assertEqual(headers["Sec-Fetch-Site"], "none")

        # Confirm all 5 browser profiles are actively sampled
        self.assertEqual(len(seen_user_agents), len(AntiDetectionEngine.BROWSER_PROFILES))

    def test_human_jitter_distribution_bounds(self):
        engine = AntiDetectionEngine()
        min_s = 0.5
        max_s = 2.0
        samples = [engine.calculate_human_jitter(min_s, max_s) for _ in range(1000)]

        # Every sample must strictly respect the clamped boundaries
        self.assertTrue(all(min_s <= s <= max_s for s in samples))

        # Mean should be roughly centered around (0.5 + 2.0) / 2 = 1.25
        mean_val = sum(samples) / len(samples)
        self.assertAlmostEqual(mean_val, 1.25, delta=0.1)

    def test_429_exponential_backoff_recovery_simulation(self):
        engine = AntiDetectionEngine(base_delay=1.0, max_delay=30.0)

        # Simulate 10 retry attempts under a sustained 429 Too Many Requests storm
        for attempt in range(10):
            samples = [engine.calculate_exponential_backoff(attempt) for _ in range(200)]
            expected_cap = min(30.0, 1.0 * (2 ** attempt))

            # Minimum delay must be >= 0.1s
            self.assertTrue(all(s >= 0.1 for s in samples))
            # Maximum delay must never exceed expected cap
            self.assertTrue(all(s <= expected_cap for s in samples))

            # Full jitter dispersion: variance must be positive (not deterministic)
            variance = sum((s - (sum(samples) / len(samples))) ** 2 for s in samples) / len(samples)
            self.assertGreater(variance, 0.01, f"Attempt {attempt} backoff lacked full jitter variance")


class TestHunterSalaryNormalizerAdversarial(unittest.TestCase):
    """Adversarial stress testing of Hunter's Salary & Rate Normalizer."""

    # 1. Negative & Zero Values
    def test_negative_salary_handling(self):
        negative_cases = [
            "- $50 / hr",
            "-$100k - -$150k",
            "Salary: -5000 / month",
            "-£40 / hour",
        ]
        for case in negative_cases:
            with self.subTest(case=case):
                # The normalizer regex (\d+) extracts positive digit magnitude.
                # It must parse safely without exception.
                min_usd, max_usd, period, matched = parse_salary(case)
                self.assertIsNotNone(min_usd)
                self.assertGreaterEqual(min_usd, 0.0)

    def test_zero_and_micro_rates(self):
        zero_cases = [
            ("$0 / hr", 0.0, 0.0, "hourly"),
            ("$0k - $0k", 0.0, 0.0, "annual"),
            ("$0 / month", 0.0, 0.0, "monthly"),
        ]
        for text, exp_min, exp_max, exp_period in zero_cases:
            with self.subTest(text=text):
                min_usd, max_usd, period, matched = parse_salary(text)
                self.assertEqual(min_usd, exp_min)
                self.assertEqual(max_usd, exp_max)
                self.assertEqual(period, exp_period)
                # Zero salary must never be classified as high-ticket
                self.assertFalse(is_high_ticket_opportunity(min_usd, max_usd, title="Junior Dev"))

    def test_naked_numbers_without_unit_treated_as_unspecified(self):
        # Without a rate unit ($/hr, $/mo, k), naked ranges are ambiguous
        unspecified_cases = [
            "$0 - $0",
            "$500 - $600",
            "100 - 200",
        ]
        for text in unspecified_cases:
            with self.subTest(text=text):
                min_usd, max_usd, period, matched = parse_salary(text)
                self.assertIsNone(min_usd)
                self.assertIsNone(max_usd)
                self.assertEqual(period, "unspecified")

    # 2. Multi-Currency Normalization Accuracy
    def test_multi_currency_exchange_rates(self):
        test_matrix = [
            # EUR (€): 1.08
            ("€5,000 - €7,000 / mo", 5400.0, 7560.0, "monthly"),
            ("€100k - €120k", round(100000 * 1.08 / 12, 2), round(120000 * 1.08 / 12, 2), "annual"),
            # GBP (£): 1.28
            ("£400 - £500 / day", 400 * 1.28 * 20, 500 * 1.28 * 20, "daily"),
            ("£60 / hr", 60 * 1.28 * 160, 60 * 1.28 * 160, "hourly"),
            # CAD: 0.74
            ("CAD 100k - 120k", round(100000 * 0.74 / 12, 2), round(120000 * 0.74 / 12, 2), "annual"),
            # AUD: 0.65
            ("AUD 120k - 140k", round(120000 * 0.65 / 12, 2), round(140000 * 0.65 / 12, 2), "annual"),
        ]
        for text, exp_min, exp_max, exp_period in test_matrix:
            with self.subTest(text=text):
                min_usd, max_usd, period, matched = parse_salary(text)
                self.assertEqual(period, exp_period)
                self.assertAlmostEqual(min_usd, exp_min, delta=1.0)
                self.assertAlmostEqual(max_usd, exp_max, delta=1.0)
                # Verify high-ticket classification
                self.assertTrue(is_high_ticket_opportunity(min_usd, max_usd))

    # 3. Inverted Ranges, Micro-values, and Extreme Numbers
    def test_inverted_ranges_self_correction(self):
        # Range where high is listed before low: e.g. "$180k - $140k" or "$80 - $50 / hr"
        min_usd, max_usd, period, matched = parse_salary("$180k - $140k")
        self.assertLess(min_usd, max_usd, "Inverted range must be auto-corrected (min <= max)")
        self.assertAlmostEqual(min_usd, 140000 / 12, delta=0.5)
        self.assertAlmostEqual(max_usd, 180000 / 12, delta=0.5)

        min_hr, max_hr, period_hr, _ = parse_salary("$80 - $50 / hr")
        self.assertLess(min_hr, max_hr)
        self.assertEqual(min_hr, 50 * 160)
        self.assertEqual(max_hr, 80 * 160)

    def test_truncated_shorthand_ranges(self):
        # Shorthand notation: "140 - 180k" (where 140 lacks explicit 'k')
        min_usd, max_usd, period, matched = parse_salary("$140 - $180k")
        self.assertAlmostEqual(min_usd, 140000 / 12, delta=0.5)
        self.assertAlmostEqual(max_usd, 180000 / 12, delta=0.5)
        self.assertEqual(period, "annual")

    def test_extreme_and_alien_strings(self):
        alien_cases = [
            "We offer competitive salary + equity in Mars colonization",
            "DOE (Depends on experience) + free lunch",
            "NaN - Infinity",
            "💰 Great package with 401(k) match!",  # 401(k) should not be treated as $401k salary
            "Series A with $15M in funding looking for founding engineer",
            "Equity: 0.5% - 2.0%",
            "",
            "   ",
        ]
        for alien in alien_cases:
            with self.subTest(alien=alien):
                min_usd, max_usd, period, matched = parse_salary(alien)
                if period != "unspecified":
                    # If any match occurred (e.g. 401k), verify it doesn't cause overflow or crash
                    self.assertIsInstance(min_usd, (float, int))
                    self.assertIsInstance(max_usd, (float, int))
                else:
                    self.assertIsNone(min_usd)
                    self.assertIsNone(max_usd)

    def test_emoji_and_noise_surrounded_salary(self):
        text = "🚀 Senior Fullstack Role! 💰 Paying $150,000 - $200,000 / year with full remote benefits 🎉"
        min_usd, max_usd, period, matched = parse_salary(text)
        self.assertEqual(period, "annual")
        self.assertAlmostEqual(min_usd, 150000 / 12, delta=0.5)
        self.assertAlmostEqual(max_usd, 200000 / 12, delta=0.5)
        self.assertTrue(is_high_ticket_opportunity(min_usd, max_usd))

    def test_single_figure_k_salary_normalization(self):
        """
        Verifies that single-figure annual salaries with 'k' notation (e.g., '$140k')
        are correctly parsed to normalized monthly USD ($11,666.67/mo) rather than mangled.
        """
        min_usd, max_usd, period, matched = parse_salary("$140k")
        self.assertAlmostEqual(min_usd, 140000.0 / 12.0, delta=1.0)
        self.assertAlmostEqual(max_usd, 140000.0 / 12.0, delta=1.0)
        self.assertEqual(period, "annual")
        self.assertTrue(is_high_ticket_opportunity(min_usd, max_usd, title="Fullstack Developer"))

    def test_single_figure_multi_currency_matrix(self):
        """
        Verifies multi-currency single-figure salaries ($100k, $120k/yr, $150k/year, €90k, £80k, CAD 120k)
        correctly normalize to monthly USD without range splitting.
        """
        cases = [
            ("$100k", 100000.0 / 12.0, 100000.0 / 12.0, "annual"),
            ("$120k/yr", 120000.0 / 12.0, 120000.0 / 12.0, "annual"),
            ("$150k / year", 150000.0 / 12.0, 150000.0 / 12.0, "annual"),
            ("€90k", (90000.0 * 1.08) / 12.0, (90000.0 * 1.08) / 12.0, "annual"),
            ("£80k", (80000.0 * 1.28) / 12.0, (80000.0 * 1.28) / 12.0, "annual"),
            ("CAD 120k", (120000.0 * 0.74) / 12.0, (120000.0 * 0.74) / 12.0, "annual"),
        ]
        for raw, exp_min, exp_max, exp_period in cases:
            with self.subTest(raw=raw):
                min_usd, max_usd, period, matched = parse_salary(raw)
                self.assertEqual(period, exp_period)
                self.assertAlmostEqual(min_usd, exp_min, delta=1.0)
                self.assertAlmostEqual(max_usd, exp_max, delta=1.0)
                self.assertTrue(is_high_ticket_opportunity(min_usd, max_usd))


if __name__ == "__main__":
    unittest.main()

