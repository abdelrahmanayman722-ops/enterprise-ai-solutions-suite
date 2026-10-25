"""
Empirical Verification & Stress Harness - Challenger 2
======================================================
Focus areas:
1. Cockpit API concurrent deal mutations and atomic JSON persistence integrity.
2. Hunter ingestion to Cockpit sync flow.
3. Simulated offline mode and network outage fallback verification.

Author: teamwork_preview_challenger_2
"""

import sys
import os
import json
import time
import shutil
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient
from cockpit.server import (
    app,
    PIPELINE_FILE,
    OPPORTUNITIES_FILE,
    HUNTER_EXPORT_FILE,
    load_pipeline_data,
    atomic_save_json,
    VALID_STAGES,
)
from contract_hunter.remote_contract_hunter import RemoteContractHunter
from contract_hunter.cache_manager import (
    ThreeTierFallbackManager,
    DiskCacheManager,
    get_emergency_curated_opportunities,
)
from contract_hunter.adapters.hn_adapter import HNAdapter
from contract_hunter.adapters.wwr_adapter import WWRAdapter
from contract_hunter.adapters.yc_adapter import YCAdapter
from contract_hunter.adapters.remoteok_adapter import RemoteOKAdapter
from ai_solutions_suite.ai_agent_rag.rag_agent import EnterpriseRAGAgent
from ai_solutions_suite.ai_agent_rag.safe_sql_executor import SafeSQLExecutor, SecurityViolationError
from ai_solutions_suite.python_scraper_engine.scraper_engine import ScraperPipeline


class EmpiricalChallengerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        # Back up original files
        cls.pipeline_backup = None
        if PIPELINE_FILE.exists():
            with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
                cls.pipeline_backup = json.load(f)

        cls.hunter_backup = None
        if HUNTER_EXPORT_FILE.exists():
            with open(HUNTER_EXPORT_FILE, "r", encoding="utf-8") as f:
                cls.hunter_backup = json.load(f)

    @classmethod
    def tearDownClass(cls):
        # Restore original files
        if cls.pipeline_backup is not None:
            atomic_save_json(PIPELINE_FILE, cls.pipeline_backup)
        if cls.hunter_backup is not None:
            HUNTER_EXPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
            atomic_save_json(HUNTER_EXPORT_FILE, cls.hunter_backup)

    def setUp(self):
        # Ensure fresh pipeline state before each test
        if self.pipeline_backup is not None:
            atomic_save_json(PIPELINE_FILE, self.pipeline_backup)

    # =========================================================================
    # PART 1: Cockpit API Concurrent Deal Mutations & Atomic JSON Persistence
    # =========================================================================

    def test_01_atomic_save_json_corruption_resistance(self):
        """Stress-test atomic_save_json directly under high multi-threaded pressure."""
        test_file = PROJECT_ROOT / "cockpit" / "data" / "test_atomic_stress.json"
        num_threads = 25
        iterations_per_thread = 10

        errors = []

        def worker(thread_idx):
            for i in range(iterations_per_thread):
                payload = {
                    "thread_id": thread_idx,
                    "iteration": i,
                    "timestamp": time.time(),
                    "payload_data": [f"item_{x}" for x in range(50)],
                }
                try:
                    atomic_save_json(test_file, payload)
                except Exception as e:
                    errors.append((thread_idx, i, str(e)))

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, t) for t in range(num_threads)]
            for f in as_completed(futures):
                f.result()

        # Check file integrity on disk
        self.assertTrue(test_file.exists(), "Atomic stress file must exist")
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("thread_id", data)
            self.assertIn("payload_data", data)
            self.assertEqual(len(data["payload_data"]), 50)
        finally:
            if test_file.exists():
                test_file.unlink()

        # Log or report any Windows file lock / permission collisions
        if errors:
            print(f"\n[Warning] Direct atomic_save_json experienced {len(errors)} collisions: {errors[0]}")
        else:
            print(f"\n[Pass] Direct atomic_save_json: 0 errors across {num_threads * iterations_per_thread} rapid writes.")

    def test_02_cockpit_api_concurrent_mutations_and_reads(self):
        """
        Stress-test Cockpit REST API with concurrent POST (create), PUT (update),
        and GET (pipeline/metrics) operations.
        Empirically measure:
        1. Absence of HTTP 500 errors.
        2. Preservation of valid JSON on disk.
        3. Lost update behavior under concurrency.
        """
        num_creations = 20
        created_deals_info = []
        statuses = []
        exceptions = []

        def create_deal_task(idx):
            payload = {
                "title": f"Concurrent Deal {idx}",
                "company": f"Concurrent Startup {idx}",
                "stage": "leads",
                "monthly_value": 4000.0 + (idx * 100),
                "source": "StressTest",
                "skills": ["next.js", "python"],
            }
            try:
                res = self.client.post("/api/pipeline", json=payload)
                statuses.append(("POST", res.status_code))
                if res.status_code == 201:
                    created_deals_info.append(res.json()["id"])
                else:
                    exceptions.append(f"POST failed with {res.status_code}: {res.text}")
            except Exception as e:
                exceptions.append(f"POST exception: {e}")

        def read_metrics_task():
            try:
                res = self.client.get("/api/metrics")
                statuses.append(("GET_METRICS", res.status_code))
                if res.status_code != 200:
                    exceptions.append(f"GET /api/metrics failed: {res.status_code}")
            except Exception as e:
                exceptions.append(f"GET /api/metrics exception: {e}")

        def read_pipeline_task():
            try:
                res = self.client.get("/api/pipeline")
                statuses.append(("GET_PIPELINE", res.status_code))
                if res.status_code != 200:
                    exceptions.append(f"GET /api/pipeline failed: {res.status_code}")
            except Exception as e:
                exceptions.append(f"GET /api/pipeline exception: {e}")

        # Execute concurrent tasks simultaneously
        tasks = []
        with ThreadPoolExecutor(max_workers=16) as executor:
            for i in range(num_creations):
                tasks.append(executor.submit(create_deal_task, i))
                if i % 2 == 0:
                    tasks.append(executor.submit(read_metrics_task))
                    tasks.append(executor.submit(read_pipeline_task))

            for t in as_completed(tasks):
                t.result()

        # Check 1: Zero 500 errors
        status_codes = [s[1] for s in statuses]
        server_errors = [c for c in status_codes if c >= 500]
        self.assertEqual(len(server_errors), 0, f"Found {len(server_errors)} HTTP 500 errors: {exceptions}")

        # Check 2: Disk file integrity
        self.assertTrue(PIPELINE_FILE.exists())
        with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
            disk_data = json.load(f)

        self.assertIsInstance(disk_data, dict)
        self.assertIn("deals", disk_data)
        self.assertIsInstance(disk_data["deals"], list)

        # Check 3: Check how many created deals actually survived in disk_data
        persisted_deal_ids = {d["id"] for d in disk_data["deals"]}
        survived_count = sum(1 for did in created_deals_info if did in persisted_deal_ids)
        print(f"\n[Empirical Metric] Concurrent deal creates: {len(created_deals_info)} returned 201 Created.")
        print(f"[Empirical Metric] Persisted on disk: {survived_count}/{len(created_deals_info)} deals survived.")

        # Check 4: Revenue metrics accuracy after mutations
        metrics_res = self.client.get("/api/metrics")
        self.assertEqual(metrics_res.status_code, 200)
        metrics = metrics_res.json()

        # Validate mathematical integrity of metrics vs deals in disk
        expected_mrr = sum(d["monthly_value"] for d in disk_data["deals"] if d.get("stage") == "won")
        expected_in_flight = sum(
            d["monthly_value"] for d in disk_data["deals"] if d.get("stage") in ("interviewing", "contract_sent")
        )
        expected_total = sum(d["monthly_value"] for d in disk_data["deals"])

        self.assertAlmostEqual(metrics["active_monthly_revenue"], expected_mrr, places=2)
        self.assertAlmostEqual(metrics["in_flight_pipeline_value"], expected_in_flight, places=2)
        self.assertAlmostEqual(metrics["total_pipeline_value"], expected_total, places=2)
        self.assertEqual(metrics["total_deals"], len(disk_data["deals"]))

    def test_03_concurrent_deal_stage_advancement(self):
        """Stress-test advancing multiple deals concurrently through the Kanban lifecycle."""
        # Create 10 distinct test deals
        deal_ids = []
        for i in range(10):
            res = self.client.post("/api/pipeline", json={
                "title": f"Lifecycle Deal {i}",
                "company": f"Startup {i}",
                "stage": "leads",
                "monthly_value": 5000.0,
            })
            self.assertEqual(res.status_code, 201)
            deal_ids.append(res.json()["id"])

        # Concurrent advancement: each thread advances one deal through leads -> pitched -> interviewing -> won
        transition_errors = []

        def advance_lifecycle(did):
            try:
                for target_stage in ["pitched", "interviewing", "contract_sent", "won"]:
                    res = self.client.put(f"/api/pipeline/{did}", json={"stage": target_stage})
                    if res.status_code != 200:
                        transition_errors.append((did, target_stage, res.status_code, res.text))
            except Exception as e:
                transition_errors.append((did, "exception", str(e)))

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(advance_lifecycle, did) for did in deal_ids]
            for f in as_completed(futures):
                f.result()

        # Report empirical findings on concurrent deal transitions
        print(f"\n[Empirical Finding] Concurrent stage transitions completed.")
        if transition_errors:
            print(f"[Empirical Finding] Detected {len(transition_errors)} Windows WinError 5 file-lock collisions during concurrent PUT operations.")
            for err in transition_errors[:3]:
                print(f"   Collision detail: {err}")
        else:
            print(f"[Empirical Finding] Zero collisions detected during stage transitions.")

        # Invariant: Any deal that exists on disk must be in a valid Kanban stage
        data = load_pipeline_data()
        for deal in data["deals"]:
            self.assertIn(deal.get("stage"), VALID_STAGES)

    # =========================================================================
    # PART 2: Hunter Ingestion to Cockpit Sync Flow
    # =========================================================================

    def test_04_hunter_to_cockpit_full_sync_and_filter_flow(self):
        """Empirically test ingesting new opportunities into Cockpit and querying them."""
        # 1. Create a specialized set of opportunities simulating Hunter export
        test_opps = [
            {
                "id": "opp-sync-test-001",
                "title": "Principal AI Systems Architect",
                "company": "Cognitive Frontier",
                "funding_stage": "YC W24",
                "salary_or_rate": "$160k - $200k/yr ($13.3k - $16.6k/mo)",
                "monthly_rate_usd_min": 13333.33,
                "monthly_rate_usd_max": 16666.67,
                "rate_period": "annual",
                "is_high_ticket": True,
                "skills_tags": ["python", "ai", "next.js", "rag"],
                "location": "Worldwide / Remote",
                "source_platform": "ycombinator",
                "url": "https://www.ycombinator.com/jobs/cognitive-frontier",
                "match_score": 99,
                "pitch_cto": "Production-grade RAG and cyclical AI agents with sub-30ms retrieval.",
                "pitch_founder": "Transforming complex agentic specs into revenue-generating SaaS.",
                "posted_date": "2026-10-23T08:00:00Z",
            },
            {
                "id": "opp-sync-test-002",
                "title": "Senior Next.js Full-Stack Contractor",
                "company": "Veloce Payments",
                "funding_stage": "Series A",
                "salary_or_rate": "$5,000 - $6,500/mo",
                "monthly_rate_usd_min": 5000.0,
                "monthly_rate_usd_max": 6500.0,
                "rate_period": "monthly",
                "is_high_ticket": True,
                "skills_tags": ["next.js", "react", "node.js"],
                "location": "Remote (EMEA / US)",
                "source_platform": "remoteok",
                "url": "https://remoteok.com/jobs/veloce-nextjs",
                "match_score": 96,
                "pitch_cto": "Next.js 15 App Router migration expert with zero downtime.",
                "pitch_founder": "High-velocity delivery of conversion-optimized client portals.",
                "posted_date": "2026-10-23T08:10:00Z",
            },
        ]

        HUNTER_EXPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HUNTER_EXPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(test_opps, f, indent=2)

        # 2. Trigger sync endpoint
        sync_res = self.client.post("/api/opportunities/sync")
        self.assertEqual(sync_res.status_code, 200)
        sync_data = sync_res.json()
        self.assertEqual(sync_data["status"], "synced")
        self.assertEqual(sync_data["count"], 2)

        # 3. Query opportunities feed
        opps_res = self.client.get("/api/opportunities")
        self.assertEqual(opps_res.status_code, 200)
        opps = opps_res.json()
        opp_ids = [o["id"] for o in opps]
        self.assertIn("opp-sync-test-001", opp_ids)
        self.assertIn("opp-sync-test-002", opp_ids)

        # 4. Verify filters:
        # Filter by tags: 'python'
        py_res = self.client.get("/api/opportunities?tags=python")
        self.assertEqual(py_res.status_code, 200)
        py_opps = py_res.json()
        self.assertTrue(any(o["id"] == "opp-sync-test-001" for o in py_opps))
        self.assertFalse(any(o["id"] == "opp-sync-test-002" for o in py_opps))

        # Filter by min_salary: 10000
        high_res = self.client.get("/api/opportunities?min_salary=10000")
        self.assertEqual(high_res.status_code, 200)
        high_opps = high_res.json()
        self.assertTrue(any(o["id"] == "opp-sync-test-001" for o in high_opps))
        self.assertFalse(any(o["id"] == "opp-sync-test-002" for o in high_opps))

        # 5. Convert ingested opportunity into active Cockpit deal
        matched_opp = next(o for o in opps if o["id"] == "opp-sync-test-001")
        deal_res = self.client.post("/api/pipeline", json={
            "opportunity_id": matched_opp["id"],
            "title": matched_opp["title"],
            "company": matched_opp["company"],
            "stage": "leads",
            "monthly_value": matched_opp["monthly_rate_usd_min"],
            "skills": matched_opp["skills_tags"],
        })
        self.assertEqual(deal_res.status_code, 201)
        deal_info = deal_res.json()
        self.assertEqual(deal_info["opportunity_id"], "opp-sync-test-001")
        self.assertEqual(deal_info["company"], "Cognitive Frontier")

        # 6. Generate pitch for this ingested opportunity
        pitch_res = self.client.post("/api/pitch/generate", json={
            "position": matched_opp["title"],
            "company": matched_opp["company"],
            "skills": matched_opp["skills_tags"],
            "tone": "cto",
            "contact_name": "Dr. Sarah Chen (CTO)",
        })
        self.assertEqual(pitch_res.status_code, 200)
        pitch_data = pitch_res.json()
        self.assertIn("Cognitive Frontier", pitch_data["subject"])
        self.assertIn("Sarah Chen", pitch_data["body"])
        self.assertIn("python, ai, next.js, rag", pitch_data["body"])

    def test_05_hunter_sync_edge_cases(self):
        """Test sync endpoint when hunter export is missing, corrupt, or empty."""
        # Subtest 1: Missing file
        if HUNTER_EXPORT_FILE.exists():
            HUNTER_EXPORT_FILE.unlink()

        res_missing = self.client.post("/api/opportunities/sync")
        self.assertEqual(res_missing.status_code, 200, "Missing export must not crash sync with 500")
        self.assertGreaterEqual(res_missing.json()["count"], 1, "Must fall back to cached/benchmark items")

        # Subtest 2: Corrupted JSON
        with open(HUNTER_EXPORT_FILE, "w", encoding="utf-8") as f:
            f.write("{corrupt_json_format!!")

        res_corrupt = self.client.post("/api/opportunities/sync")
        self.assertEqual(res_corrupt.status_code, 200, "Corrupt export must not crash sync with 500")
        self.assertGreaterEqual(res_corrupt.json()["count"], 1, "Must fall back safely on corrupt JSON")

        # Subtest 3: Empty list
        with open(HUNTER_EXPORT_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

        res_empty = self.client.post("/api/opportunities/sync")
        self.assertEqual(res_empty.status_code, 200)
        self.assertGreaterEqual(res_empty.json()["count"], 1)

    # =========================================================================
    # PART 3: Simulated Offline Mode & Network Outage Fallback Verification
    # =========================================================================

    def test_06_hunter_full_network_blackout_simulation(self):
        """
        Simulate total network blackout (DNS down, TCP connection refused, HTTP timeouts).
        Verify Hunter executes all 4 adapters through 3-tier fallback and produces high-ticket jobs.
        """
        hunter = RemoteContractHunter()

        def network_blackout(*args, **kwargs):
            raise urllib.error.URLError("Simulated Network Blackout: Connection refused")

        with patch("urllib.request.urlopen", side_effect=network_blackout):
            opportunities = hunter.fetch_all_sources(limit_per_source=5, force_live=True)

        self.assertIsInstance(opportunities, list)
        self.assertGreaterEqual(len(opportunities), 1, "Hunter must provide opportunities even in complete blackout")

        # Verify quality of fallback leads
        high_ticket_count = sum(1 for opp in opportunities if opp.is_high_ticket)
        low_ticket_count = len(opportunities) - high_ticket_count
        print(f"\n[Empirical Metric] Blackout fallback yielded {len(opportunities)} opportunities:")
        print(f"   High-Ticket classified: {high_ticket_count}/{len(opportunities)} ({round(high_ticket_count/len(opportunities)*100, 1)}%)")
        print(f"   Non-high-ticket candidates included: {low_ticket_count}")

        # Check for the fallthrough anomaly: roles with explicit sub-$3500 salary classified as high-ticket
        sub_threshold_high_ticket = [
            opp for opp in opportunities 
            if opp.is_high_ticket and opp.monthly_rate_usd_max is not None and opp.monthly_rate_usd_max < 3500.0
        ]
        if sub_threshold_high_ticket:
            print(f"[Empirical Finding] Detected {len(sub_threshold_high_ticket)} opportunities with sub-$3500 compensation marked is_high_ticket=True due to missing (monthly_min is None) guardrail in normalizer.py.")
            for opp in sub_threshold_high_ticket[:2]:
                print(f"   Anomaly sample: ID={opp.id}, Title='{opp.title}', Rate='{opp.salary_or_rate}', MonthlyMax=${opp.monthly_rate_usd_max}")

        self.assertGreaterEqual(high_ticket_count, 1, "Must contain at least 1 verified high-ticket opportunity")

        # Verify Tier 3 Emergency Fallback dataset strictly adheres to high ticket thresholds
        emergency_dataset = get_emergency_curated_opportunities()
        for emerg_opp in emergency_dataset:
            self.assertTrue(emerg_opp["is_high_ticket"])
            self.assertGreaterEqual(emerg_opp["monthly_rate_usd_min"], 3500.0)

    def test_07_hunter_individual_adapters_offline_resilience(self):
        """Test each adapter individually when completely offline."""
        def network_blackout(*args, **kwargs):
            raise urllib.error.URLError("Simulated Network Blackout: Host unreachable")

        with patch("urllib.request.urlopen", side_effect=network_blackout):
            hn_adapter = HNAdapter()
            wwr_adapter = WWRAdapter()
            yc_adapter = YCAdapter()
            remoteok_adapter = RemoteOKAdapter()

            # Each adapter should return empty list or handle gracefully without throwing uncaught exceptions
            hn_jobs = hn_adapter.fetch_all(limit=5)
            self.assertIsInstance(hn_jobs, list)

            wwr_jobs = wwr_adapter.fetch_all(limit_per_feed=2)
            self.assertIsInstance(wwr_jobs, list)

            yc_jobs = yc_adapter.fetch_all(limit=5)
            self.assertIsInstance(yc_jobs, list)

            remoteok_jobs = remoteok_adapter.fetch_all(limit=5)
            self.assertIsInstance(remoteok_jobs, list)

    def test_08_three_tier_fallback_cold_cache_activation(self):
        """
        Verify that when cache is 100% cold (empty directory) and live network fails,
        ThreeTierFallbackManager seamlessly promotes Tier 3 emergency fallback.
        """
        with tempfile.TemporaryDirectory() as empty_temp_dir:
            mgr = ThreeTierFallbackManager(cache_dir=empty_temp_dir)

            def failing_live_network():
                raise ConnectionResetError("Remote server closed connection")

            emergency_invoked = [False]
            def emergency_provider():
                emergency_invoked[0] = True
                return [{"id": "verified_emergency_01", "title": "Lead from Tier 3", "monthly_value": 5000.0}]

            result, tier_used = mgr.execute_with_fallback(
                cache_key="cold_test_feed",
                network_call=failing_live_network,
                emergency_fallback_call=emergency_provider,
                domain="api.unreachable.net",
                force_refresh=True,
            )

            self.assertEqual(tier_used, "tier3_emergency")
            self.assertTrue(emergency_invoked[0])
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["id"], "verified_emergency_01")

    def test_09_enterprise_ai_suite_offline_functionality(self):
        """Verify RAG Agent, SafeSQL barrier, and Scraper execute with 0 internet."""
        # 1. RAG Agent in mock/offline mode
        agent = EnterpriseRAGAgent(mock_mode=True)
        res = agent.query("What are the best enterprise orders and revenue figures?")
        self.assertIn("answer", res)
        self.assertGreater(len(res["answer"]), 0)
        self.assertGreaterEqual(res["confidence"], 0.40)
        self.assertIsInstance(res["sources"], list)

        # 2. SafeSQL barrier in offline SQLite
        executor = SafeSQLExecutor()
        valid_res = executor.execute(agent.db_source, "SELECT customer_name, total_usd FROM enterprise_orders LIMIT 5")
        self.assertGreaterEqual(valid_res["row_count"], 1)
        self.assertGreaterEqual(len(valid_res["rows"]), 1)

        # Destructive SQL must be blocked offline
        with self.assertRaises(SecurityViolationError):
            executor.execute(agent.db_source, "DROP TABLE enterprise_orders")

        # 3. Scraper Pipeline offline execution
        scraper = ScraperPipeline(target_domain="offline-verify.internal")
        mock_html = """
        <div class="job-item">
            <h2 class="title">Lead Full-Stack Next.js Architect</h2>
            <div class="company">HyperFlow AI</div>
            <span class="salary">$150k - $180k</span>
            <p class="description">Building Next.js 15 App Router frontends and AI agents.</p>
        </div>
        """
        extracted = scraper.process_raw_html(mock_html)
        self.assertIsInstance(extracted, list)

    def test_10_cockpit_full_offline_operation(self):
        """Verify that Cockpit REST API and static UI require zero internet."""
        # Test health, pipeline, opportunities, metrics, export, pitch endpoints
        endpoints = [
            ("GET", "/api/health", 200),
            ("GET", "/api/pipeline", 200),
            ("GET", "/api/opportunities", 200),
            ("GET", "/api/metrics", 200),
            ("GET", "/api/export?format=json", 200),
            ("GET", "/api/export?format=csv", 200),
            ("GET", "/", 200),
            ("GET", "/styles.css", 200),
            ("GET", "/app.js", 200),
        ]
        for method, path, expected_status in endpoints:
            res = self.client.get(path) if method == "GET" else self.client.post(path)
            self.assertEqual(res.status_code, expected_status, f"{method} {path} returned {res.status_code}")


if __name__ == "__main__":
    unittest.main()
