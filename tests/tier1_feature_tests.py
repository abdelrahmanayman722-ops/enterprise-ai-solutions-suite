"""
Tier 1: Feature Coverage Test Suite
===================================
Master E2E Testing Suite - Milestone 4
Validates primary feature behavior (happy path) across:
1. Startup & Remote Contract Hunter (M1)
2. Enterprise AI Agent / RAG Solution (M2)
3. Python Web Scraper & Data Pipeline (M2)
4. Executive SaaS Dashboard (M2)
5. Executive Pipeline Cockpit REST API (M3)

Author: Eng. Abdelrahman Rashad & QA Automation Track
"""

import sys
import os
import json
import tempfile
import unittest
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Module imports with defense-in-depth fallbacks
from contract_hunter.normalizer import (
    parse_salary,
    is_high_ticket_opportunity,
    extract_skills,
    infer_funding_stage,
    compute_match_score,
    ContractOpportunity,
)
from contract_hunter.pitch_generator import (
    generate_cto_pitch,
    generate_founder_pitch,
    generate_dual_pitches,
)
from contract_hunter.remote_contract_hunter import RemoteContractHunter
from ai_solutions_suite.ai_agent_rag.rag_agent import EnterpriseRAGAgent
from ai_solutions_suite.ai_agent_rag.safe_sql_executor import SafeSQLExecutor
from ai_solutions_suite.ai_agent_rag.conversational_memory import ConversationalMemory
from ai_solutions_suite.python_scraper_engine.anti_detection import AntiDetectionEngine
from ai_solutions_suite.python_scraper_engine.rate_limiter import TokenBucketRateLimiter
from ai_solutions_suite.python_scraper_engine.normalizer import DataNormalizer
from ai_solutions_suite.python_scraper_engine.scraper_engine import ScraperPipeline
from cockpit.server import app
from starlette.testclient import TestClient


class TestHunterFeatures(unittest.TestCase):
    """Tier 1: Contract Hunter Feature Verification."""

    def test_hourly_rate_normalization(self):
        # Arrange
        raw_text = "Senior Full-Stack Engineer ($45 - $65 / hr) - Remote"
        # Act
        min_usd, max_usd, period, matched = parse_salary(raw_text)
        # Assert
        self.assertEqual(period, "hourly")
        self.assertAlmostEqual(min_usd, 45.0 * 160.0)
        self.assertAlmostEqual(max_usd, 65.0 * 160.0)
        self.assertIn("45", matched)

    def test_annual_rate_normalization(self):
        # Arrange
        raw_text = "Lead Architect: $140k - $180k per year"
        # Act
        min_usd, max_usd, period, matched = parse_salary(raw_text)
        # Assert
        self.assertEqual(period, "annual")
        self.assertAlmostEqual(min_usd, 140000.0 / 12.0, places=2)
        self.assertAlmostEqual(max_usd, 180000.0 / 12.0, places=2)

    def test_multi_currency_normalization_eur(self):
        # Arrange: 1 EUR = 1.08 USD
        raw_text = "€4,000 - €5,000 / mo Remote Europe"
        # Act
        min_usd, max_usd, period, matched = parse_salary(raw_text)
        # Assert
        self.assertEqual(period, "monthly")
        self.assertAlmostEqual(min_usd, 4000.0 * 1.08, places=2)
        self.assertAlmostEqual(max_usd, 5000.0 * 1.08, places=2)

    def test_high_ticket_classification(self):
        # Assert threshold boundary: >= $3,500/mo is high ticket
        self.assertTrue(is_high_ticket_opportunity(3500.0, 5000.0))
        self.assertTrue(is_high_ticket_opportunity(4000.0, 6000.0))
        self.assertFalse(is_high_ticket_opportunity(1500.0, 2500.0, title="Junior Dev"))
        # Senior title without salary qualifies by default
        self.assertTrue(is_high_ticket_opportunity(None, None, title="Senior Fullstack Architect"))

    def test_tech_stack_tag_extraction(self):
        # Arrange
        text = "We are seeking a senior engineer with Next.js 15, React, Python, and SQL capabilities."
        # Act
        tags = extract_skills(text)
        # Assert
        self.assertIn("next.js", tags)
        self.assertIn("react", tags)
        self.assertIn("python", tags)
        self.assertIn("sql", tags)

    def test_funding_stage_inference(self):
        # Assert YC batch recognition and standard venture rounds
        self.assertEqual(infer_funding_stage("HyperFlow (YC W24)", "AI workflow automation"), "YC W24")
        self.assertEqual(infer_funding_stage("CloudScale", "Series A funded startup"), "Series A")
        self.assertEqual(infer_funding_stage("Apex Studio", "Bootstrapped profitable agency"), "Bootstrapped")

    def test_opportunity_match_scoring(self):
        # Arrange: High-value role with top stack and worldwide remote
        skills = ["next.js", "python", "ai", "node.js"]
        monthly_max = 6000.0
        score = compute_match_score(skills, monthly_max, True, "Worldwide", "Worldwide")
        # Assert: should achieve high score (>= 85)
        self.assertGreaterEqual(score, 85)

    def test_cto_pitch_generation(self):
        # Arrange
        position = "Senior Full-Stack Engineer"
        company = "Nexus AI Labs"
        skills = ["next.js", "python", "ai"]
        # Act
        pitch = generate_cto_pitch(position, company, skills)
        # Assert
        self.assertIn("Nexus AI Labs", pitch)
        self.assertIn("Clean Architecture", pitch)
        self.assertIn("Abdelrahman Rashad", pitch)
        self.assertIn("Next.js", pitch)

    def test_founder_pitch_generation(self):
        # Arrange
        position = "Lead Full-Stack Developer"
        company = "HyperFlow"
        skills = ["next.js", "python"]
        # Act
        pitch = generate_founder_pitch(position, company, skills)
        # Assert
        self.assertIn("HyperFlow", pitch)
        self.assertIn("Roadmap", pitch)
        self.assertIn("Rapid Feature Shipping", pitch)
        self.assertIn("Abdelrahman Rashad", pitch)

    def test_hunter_curated_export(self):
        # Arrange
        hunter = RemoteContractHunter()
        jobs = hunter._get_curated_fallback_jobs() if hasattr(hunter, "_get_curated_fallback_jobs") else hunter.get_curated_fallback_jobs()
        self.assertGreaterEqual(len(jobs), 3)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "test_jobs.json")
            csv_path = os.path.join(tmpdir, "test_jobs.csv")

            hunter.export_to_json(json_path)
            hunter.export_to_csv(csv_path)

            self.assertTrue(os.path.exists(json_path))
            self.assertTrue(os.path.exists(csv_path))
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertGreaterEqual(len(data), 1)


class TestRAGAndAIAgentFeatures(unittest.TestCase):
    """Tier 1: Enterprise RAG Agent & SafeSQL Feature Verification."""

    def setUp(self):
        self.agent = EnterpriseRAGAgent(mock_mode=True)
        self.docs = [
            {"id": "doc1", "content": "Next.js 15 uses React Server Components by default with App Router and Turbopack."},
            {"id": "doc2", "content": "Node.js Express provides robust middleware handling for RESTful microservice APIs."},
            {"id": "doc3", "content": "Python Playwright enables fast web scraping, anti-detection, and headless browser automation."}
        ]
        self.agent.ingest_documents(self.docs)

    def test_document_ingestion_and_retrieval(self):
        # Act
        results = self.agent.retrieve("Next.js App Router")
        # Assert
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["doc_id"], "doc1")
        self.assertIn("React Server Components", results[0]["content"])

    def test_prompt_augmentation_synthesis(self):
        # Act
        res = self.agent.generate_augmented_prompt("How does Playwright work for scraping?")
        # Assert
        self.assertIn("doc3", res["sources"])
        self.assertIn("Python Playwright", res["augmented_prompt"])
        self.assertIn("RELEVANT ENTERPRISE CONTEXT", res["augmented_prompt"])

    def test_safe_sql_executor_read_only_success(self):
        # Arrange
        executor = SafeSQLExecutor(default_limit=25)
        # Act
        res = executor.execute(self.agent.db_source, "SELECT customer_name, total_usd FROM enterprise_orders")
        # Assert
        self.assertIn("customer_name", res["columns"])
        self.assertIn("total_usd", res["columns"])
        self.assertGreaterEqual(res["row_count"], 1)
        self.assertIn("LIMIT 25", res["executed_sql"])

    def test_conversational_memory_sliding_window(self):
        # Arrange
        memory = ConversationalMemory(window_size=4)
        # Act
        for i in range(5):
            memory.add_turn("user", f"Query {i+1}")
            memory.add_turn("assistant", f"Answer {i+1}")
        # Assert: window_size=4 retains at most 4 latest turns
        history = memory.get_context()
        self.assertEqual(len(history), 4)
        self.assertEqual(history[-1]["content"], "Answer 5")


class TestScraperFeatures(unittest.TestCase):
    """Tier 1: Python Scraper Pipeline Feature Verification."""

    def test_anti_detection_headers(self):
        # Arrange
        engine = AntiDetectionEngine()
        # Act
        headers = engine.get_headers()
        # Assert
        self.assertIn("User-Agent", headers)
        self.assertIn("Accept", headers)
        self.assertIn("Accept-Language", headers)
        self.assertTrue(any(browser in headers["User-Agent"] for browser in ["Chrome", "Safari", "Firefox"]))

    def test_token_bucket_rate_limiter_acquisition(self):
        # Arrange: 10 tokens/sec, capacity 20
        limiter = TokenBucketRateLimiter(rate=10.0, capacity=20.0)
        # Act & Assert
        acquired = limiter.acquire(tokens=5.0, block=False)
        self.assertTrue(acquired)
        self.assertLessEqual(limiter.tokens_available(), 16.0)

    def test_data_normalizer_text_and_currency(self):
        # Arrange
        normalizer = DataNormalizer()
        raw_html = "<div class='item'>&amp; Enterprise Cloud <b>Server</b> &#39;v2&#39;</div>"
        # Act
        cleaned = normalizer.clean_text(raw_html)
        currency_info = normalizer.parse_currency("$2,450.00 / mo")
        # Assert
        self.assertEqual(cleaned, "& Enterprise Cloud Server 'v2'")
        self.assertEqual(currency_info["amount"], 2450.0)
        self.assertEqual(currency_info["currency"], "USD")
        self.assertEqual(currency_info["interval"], "monthly")

    def test_data_normalizer_sha256_fingerprint(self):
        # Arrange
        normalizer = DataNormalizer()
        payload = {"title": "Full-Stack AI Solutions Developer", "company": "Nexus AI Labs"}
        # Act
        fp1 = normalizer.compute_fingerprint(payload) if hasattr(normalizer, "compute_fingerprint") else normalizer.is_duplicate(payload)
        # Assert
        self.assertTrue(bool(fp1))

    def test_scraper_pipeline_parsing_and_export(self):
        # Arrange
        scraper = ScraperPipeline(target_domain="example.com")
        html_sample = """
        <div class="item-card"><span class="title">Enterprise RAG Engine</span><span class="price">$3,500</span></div>
        <div class="item-card"><span class="title">Resilient Web Scraper</span><span class="price">$2,200</span></div>
        """
        # Act
        records = scraper.process_raw_html(html_sample)
        # Assert
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["title"], "Enterprise RAG Engine")

        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, "scraped.json")
            csv_file = os.path.join(tmpdir, "scraped.csv")
            scraper.export_json(json_file)
            scraper.export_csv(csv_file)
            self.assertTrue(os.path.exists(json_file))
            self.assertTrue(os.path.exists(csv_file))


class TestDashboardFeatures(unittest.TestCase):
    """Tier 1: Executive SaaS Dashboard Feature Verification."""

    def test_dashboard_preview_structure_and_telemetry(self):
        # Arrange
        dashboard_preview_path = REPO_ROOT / "ai_solutions_suite" / "saas_dashboard" / "dashboard_preview.html"
        self.assertTrue(dashboard_preview_path.exists(), "dashboard_preview.html must exist")
        # Act
        content = dashboard_preview_path.read_text(encoding="utf-8")
        # Assert essential executive metrics and visual components
        self.assertIn("Apex Enterprise Telemetry Command", content)
        self.assertIn("Annual Recurring Revenue (ARR)", content)
        self.assertIn("API Throughput", content)
        self.assertIn("Real-Time Pipeline Execution", content)


class TestCockpitAPIFeatures(unittest.TestCase):
    """Tier 1: Executive Pipeline Cockpit REST API Feature Verification."""

    def setUp(self):
        self.client = TestClient(app)

    def test_api_health_endpoint(self):
        # Act
        response = self.client.get("/api/health")
        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "1.0.0")
        self.assertIn("active_pipeline_count", data)
        self.assertIn("active_mrr", data)

    def test_api_opportunities_endpoint_and_filters(self):
        # Act 1: Get all opportunities
        res = self.client.get("/api/opportunities")
        self.assertEqual(res.status_code, 200)
        opps = res.json()
        self.assertIsInstance(opps, list)
        self.assertGreaterEqual(len(opps), 1)

        # Act 2: Filter by minimum salary
        res_filtered = self.client.get("/api/opportunities?min_salary=5000")
        self.assertEqual(res_filtered.status_code, 200)
        filtered_opps = res_filtered.json()
        for o in filtered_opps:
            max_sal = o.get("monthly_rate_usd_max", o.get("monthly_rate_usd_min", 0))
            self.assertGreaterEqual(max_sal, 5000.0)

    def test_api_pipeline_grouped_stages(self):
        # Act
        res = self.client.get("/api/pipeline")
        # Assert
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("stages", data)
        for stage in ["leads", "pitched", "interviewing", "contract_sent", "won", "closed"]:
            self.assertIn(stage, data["stages"])

    def test_api_pipeline_deal_crud_lifecycle(self):
        # Act 1: Create deal
        payload = {
            "title": "Fractional CTO & AI Lead",
            "company": "Test Ventures Q4",
            "stage": "leads",
            "monthly_value": 5500.0,
            "source": "Hacker News",
            "skills": ["next.js", "python", "ai"],
            "notes": "Testing pipeline creation"
        }
        create_res = self.client.post("/api/pipeline", json=payload)
        self.assertEqual(create_res.status_code, 201)
        deal = create_res.json()
        deal_id = deal["id"]
        self.assertEqual(deal["title"], "Fractional CTO & AI Lead")
        self.assertEqual(deal["monthly_value"], 5500.0)

        # Act 2: Retrieve single deal
        get_res = self.client.get(f"/api/pipeline/{deal_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["company"], "Test Ventures Q4")

        # Act 3: Update deal stage
        update_res = self.client.put(f"/api/pipeline/{deal_id}", json={"stage": "interviewing", "monthly_value": 6000.0})
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["stage"], "interviewing")
        self.assertEqual(update_res.json()["monthly_value"], 6000.0)

        # Act 4: Clean up deal
        del_res = self.client.delete(f"/api/pipeline/{deal_id}")
        self.assertEqual(del_res.status_code, 200)

    def test_api_pitch_generation(self):
        # Arrange
        payload = {
            "position": "Senior Full-Stack Engineer",
            "company": "RapidScale AI",
            "skills": ["next.js", "python", "ai"],
            "tone": "cto",
            "custom_notes": "Special focus on sub-100ms TTFB"
        }
        # Act
        res = self.client.post("/api/pitch/generate", json=payload)
        # Assert
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("subject", data)
        self.assertIn("body", data)
        self.assertIn("RapidScale AI", data["body"])
        self.assertIn("Abdelrahman Rashad", data["body"])
        self.assertGreater(data["char_count"], 100)

    def test_api_metrics_endpoint(self):
        # Act
        res = self.client.get("/api/metrics")
        # Assert
        self.assertEqual(res.status_code, 200)
        metrics = res.json()
        self.assertIn("active_monthly_revenue", metrics)
        self.assertIn("annual_recurring_revenue", metrics)
        self.assertIn("in_flight_pipeline_value", metrics)
        self.assertIn("win_rate", metrics)
        self.assertIn("stage_breakdown", metrics)

    def test_api_export_formats(self):
        # Act 1: JSON Export
        res_json = self.client.get("/api/export?format=json")
        self.assertEqual(res_json.status_code, 200)

        # Act 2: CSV Export
        res_csv = self.client.get("/api/export?format=csv")
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn("text/csv", res_csv.headers.get("content-type", ""))


if __name__ == "__main__":
    unittest.main()
