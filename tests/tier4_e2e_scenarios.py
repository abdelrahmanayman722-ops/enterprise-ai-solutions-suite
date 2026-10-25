"""
Tier 4: Real-World Scenarios & Headless UI Smoke Test Suite
===========================================================
Master E2E Testing Suite - Milestone 4
Validates complete real-world business lifecycles and DOM integrity:
1. Full Contract Acquisition Lifecycle ($6,000/mo Startup Retainer).
2. Enterprise B2B Solution Sale Workflow (AI RAG + Scraper Package).
3. Headless Cockpit & SaaS Dashboard DOM Smoke Verification.

Author: Eng. Abdelrahman Rashad & QA Automation Track
"""

import sys
import os
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contract_hunter.normalizer import parse_salary, is_high_ticket_opportunity, extract_skills, compute_match_score
from contract_hunter.pitch_generator import generate_cto_pitch, generate_founder_pitch
from contract_hunter.remote_contract_hunter import RemoteContractHunter
from ai_solutions_suite.ai_agent_rag.rag_agent import EnterpriseRAGAgent
from ai_solutions_suite.ai_agent_rag.safe_sql_executor import SafeSQLExecutor
from ai_solutions_suite.python_scraper_engine.scraper_engine import ScraperPipeline
from ai_solutions_suite.python_scraper_engine.anti_detection import AntiDetectionEngine
from cockpit.server import app, load_pipeline_data, atomic_save_json, PIPELINE_FILE
from starlette.testclient import TestClient


class TestContractAcquisitionLifecycle(unittest.TestCase):
    """Scenario 1: Complete Startup Contract Acquisition Lifecycle ($6,000/mo)."""

    def setUp(self):
        self.client = TestClient(app)
        self.cleanup_deal_ids = []

    def tearDown(self):
        for deal_id in self.cleanup_deal_ids:
            try:
                self.client.delete(f"/api/pipeline/{deal_id}")
            except Exception:
                pass

    def test_full_contract_acquisition_lifecycle(self):
        # -------------------------------------------------------------
        # Step 1: Discovery & Aggregation
        # -------------------------------------------------------------
        hunter = RemoteContractHunter(target_keywords=["next.js", "react", "python", "ai", "node.js"])
        jobs = hunter._get_curated_fallback_jobs() if hasattr(hunter, "_get_curated_fallback_jobs") else hunter.get_curated_fallback_jobs()
        self.assertGreaterEqual(len(jobs), 1, "Aggregator must supply high-ticket opportunities")

        # -------------------------------------------------------------
        # Step 2: Ingestion & High-Ticket Filtering
        # -------------------------------------------------------------
        # Sync feeds into Cockpit
        sync_res = self.client.post("/api/opportunities/sync")
        self.assertEqual(sync_res.status_code, 200)

        # Query opportunities filtered for $3,500/mo minimum
        opps = self.client.get("/api/opportunities?min_salary=3500").json()
        self.assertGreaterEqual(len(opps), 1)

        # -------------------------------------------------------------
        # Step 3: Candidate Selection & Opportunity Matching
        # -------------------------------------------------------------
        # Find top candidate with Next.js and AI capabilities
        candidate = next(
            (o for o in opps if any("next" in s.lower() or "ai" in s.lower() for s in o.get("skills_tags", []))),
            opps[0]
        )
        self.assertIsNotNone(candidate)
        position = candidate.get("title", "Fractional CTO & AI Lead")
        company = candidate.get("company", "HyperFlow Systems")
        skills = candidate.get("skills_tags", ["next.js", "python", "ai"])
        monthly_rate = float(candidate.get("monthly_rate_usd_max", 6000.0))

        # -------------------------------------------------------------
        # Step 4: Tailored Proposal Generation
        # -------------------------------------------------------------
        pitch_payload = {
            "position": position,
            "company": company,
            "skills": skills,
            "tone": "cto",
            "custom_notes": "Focused on sub-30ms latency and high-concurrency microservices"
        }
        pitch_res = self.client.post("/api/pitch/generate", json=pitch_payload)
        self.assertEqual(pitch_res.status_code, 200)
        pitch_data = pitch_res.json()
        self.assertIn("subject", pitch_data)
        self.assertIn(company, pitch_data["body"])
        self.assertIn("Abdelrahman Rashad", pitch_data["body"])

        # -------------------------------------------------------------
        # Step 5: Deal Creation in Pipeline (Stage: 'leads')
        # -------------------------------------------------------------
        initial_metrics = self.client.get("/api/metrics").json()
        base_mrr = initial_metrics["active_monthly_revenue"]
        base_deals = initial_metrics["total_deals"]

        deal_payload = {
            "opportunity_id": candidate.get("id", "opp-lifecycle-01"),
            "title": position,
            "company": company,
            "stage": "leads",
            "monthly_value": monthly_rate,
            "source": candidate.get("source_platform", "Hacker News"),
            "skills": skills,
            "notes": f"Pitched via CTO proposal. Subject: {pitch_data['subject']}"
        }
        deal_res = self.client.post("/api/pipeline", json=deal_payload)
        self.assertEqual(deal_res.status_code, 201)
        deal = deal_res.json()
        deal_id = deal["id"]
        self.cleanup_deal_ids.append(deal_id)

        # -------------------------------------------------------------
        # Step 6: Deal Progression Through Sales Pipeline
        # -------------------------------------------------------------
        # Transition 1: Pitched
        res_pitch = self.client.put(f"/api/pipeline/{deal_id}", json={"stage": "pitched"})
        self.assertEqual(res_pitch.status_code, 200)
        self.assertEqual(res_pitch.json()["stage"], "pitched")

        # Transition 2: Interviewing (Founder / CTO Screening)
        res_interview = self.client.put(f"/api/pipeline/{deal_id}", json={
            "stage": "interviewing",
            "notes": "Intro call completed; scheduled technical design review."
        })
        self.assertEqual(res_interview.status_code, 200)
        metrics_interview = self.client.get("/api/metrics").json()
        self.assertGreaterEqual(metrics_interview["in_flight_pipeline_value"], monthly_rate)

        # Transition 3: Contract Sent (MSA & SOW delivered)
        res_contract = self.client.put(f"/api/pipeline/{deal_id}", json={
            "stage": "contract_sent",
            "notes": "SOW sent for $6,000/mo retainer."
        })
        self.assertEqual(res_contract.status_code, 200)

        # Transition 4: Won (Contract Signed & Retainer Activated)
        res_won = self.client.put(f"/api/pipeline/{deal_id}", json={
            "stage": "won",
            "notes": "Executed 6-month high-ticket retainer. Paid via Stripe."
        })
        self.assertEqual(res_won.status_code, 200)
        self.assertEqual(res_won.json()["stage"], "won")

        # -------------------------------------------------------------
        # Step 7: Revenue Analytics Recalculation Verification
        # -------------------------------------------------------------
        final_metrics = self.client.get("/api/metrics").json()
        self.assertEqual(final_metrics["active_monthly_revenue"], base_mrr + monthly_rate)
        self.assertEqual(final_metrics["annual_recurring_revenue"], (base_mrr + monthly_rate) * 12.0)
        self.assertEqual(final_metrics["total_deals"], base_deals + 1)
        self.assertGreater(final_metrics["win_rate"], 0.0)


class TestEnterpriseSolutionSaleWorkflow(unittest.TestCase):
    """Scenario 2: Enterprise B2B Solution Sale (AI Agent + Scraper Package)."""

    def setUp(self):
        self.client = TestClient(app)
        self.cleanup_deal_ids = []

    def tearDown(self):
        for deal_id in self.cleanup_deal_ids:
            try:
                self.client.delete(f"/api/pipeline/{deal_id}")
            except Exception:
                pass

    def test_enterprise_solution_sale_workflow(self):
        # -------------------------------------------------------------
        # Step 1: Client Requirements & Solution Assembly
        # -------------------------------------------------------------
        # Ingest client proprietary documentation into Enterprise RAG Agent
        client_docs = [
            {"id": "doc_arch", "content": "Our distributed microservices run on Kubernetes with PostgreSQL and Redis."},
            {"id": "doc_sla", "content": "Target SLA requires sub-50ms query latency and read-only analytical isolation."},
            {"id": "doc_pipeline", "content": "Daily web scraping extracts competitor pricing across 50,000 SKUs."}
        ]
        rag_agent = EnterpriseRAGAgent(mock_mode=True)
        rag_agent.ingest_documents(client_docs)

        # Verify accurate synthesis for client query
        qa_result = rag_agent.generate_augmented_prompt("What is our target SLA and database architecture?")
        self.assertIn("doc_sla", qa_result["sources"])
        self.assertIn("doc_arch", qa_result["sources"])
        self.assertIn("sub-50ms", qa_result["augmented_prompt"])

        # -------------------------------------------------------------
        # Step 2: Database Safety Validation
        # -------------------------------------------------------------
        sql_barrier = SafeSQLExecutor(default_limit=50)
        valid_query = "SELECT * FROM enterprise_orders LIMIT 10"
        exec_result = sql_barrier.execute(rag_agent.db_source, valid_query)
        self.assertGreaterEqual(exec_result["row_count"], 1)

        # -------------------------------------------------------------
        # Step 3: Resilient Extraction Demo
        # -------------------------------------------------------------
        scraper = ScraperPipeline(target_domain="target-supplier.com")
        mock_html = '<div class="item-card"><span class="title">Enterprise API Gateway</span><span class="price">$3,500</span></div>'
        scraped_items = scraper.process_raw_html(mock_html)
        self.assertEqual(len(scraped_items), 1)

        # -------------------------------------------------------------
        # Step 4: Register B2B Deal in Cockpit Pipeline ($3,500/mo Package)
        # -------------------------------------------------------------
        solution_deal = {
            "title": "Enterprise RAG & Data Automation Solution Package",
            "company": "Apex Global Logistics",
            "stage": "leads",
            "monthly_value": 3500.0,
            "source": "Direct Enterprise Outreach",
            "skills": ["python", "ai", "sql", "rag", "scraping"],
            "notes": "Turnkey Enterprise RAG agent + Python anti-detection scraper delivery."
        }
        res_create = self.client.post("/api/pipeline", json=solution_deal)
        self.assertEqual(res_create.status_code, 201)
        deal_id = res_create.json()["id"]
        self.cleanup_deal_ids.append(deal_id)

        # Progress to Won
        res_won = self.client.put(f"/api/pipeline/{deal_id}", json={"stage": "won"})
        self.assertEqual(res_won.status_code, 200)

        # Verify Pipeline Metrics reflect enterprise expansion
        metrics = self.client.get("/api/metrics").json()
        self.assertGreaterEqual(metrics["active_monthly_revenue"], 3500.0)


class TestHeadlessDOMSmoke(unittest.TestCase):
    """Scenario 3: Headless Cockpit & Dashboard DOM Smoke Test."""

    class SimpleTagCollector(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tags = []
            self.ids = set()
            self.classes = set()
            self.scripts = []
            self.links = []

        def handle_starttag(self, tag, attrs):
            self.tags.append(tag)
            attr_dict = dict(attrs)
            if "id" in attr_dict:
                self.ids.add(attr_dict["id"])
            if "class" in attr_dict:
                for c in attr_dict["class"].split():
                    self.classes.add(c)
            if tag == "script" and "src" in attr_dict:
                self.scripts.append(attr_dict["src"])
            if tag == "link" and "href" in attr_dict:
                self.links.append(attr_dict["href"])

    def test_cockpit_index_html_dom_integrity(self):
        cockpit_html_path = REPO_ROOT / "cockpit" / "index.html"
        self.assertTrue(cockpit_html_path.exists(), "cockpit/index.html must exist")
        raw_html = cockpit_html_path.read_text(encoding="utf-8")

        # 1. HTML5 document declaration and meta tags
        self.assertTrue(raw_html.strip().startswith("<!DOCTYPE html>") or "<!DOCTYPE html>" in raw_html[:100])
        self.assertIn("viewport", raw_html)
        self.assertIn("utf-8", raw_html.lower())

        # 2. Parse tags and verify key interactive components
        parser = self.SimpleTagCollector()
        parser.feed(raw_html)

        # Main view containers
        self.assertIn("kanban-board", parser.ids)
        self.assertIn("view-kanban", parser.ids)
        self.assertIn("view-explorer", parser.ids)
        self.assertIn("tab-kanban", parser.ids)
        self.assertIn("tab-explorer", parser.ids)

        # Executive Metrics Cards IDs
        self.assertIn("kpi-mrr-value", parser.ids)
        self.assertIn("kpi-inflight-value", parser.ids)
        self.assertIn("kpi-winrate-value", parser.ids)
        self.assertIn("kpi-total-value", parser.ids)

        # Pitch generator drawer & modal
        self.assertIn("pitch-drawer-overlay", parser.ids)
        self.assertIn("pitch-subject", parser.ids)
        self.assertIn("pitch-body", parser.ids)
        self.assertIn("add-deal-modal", parser.ids)

        # Script inclusion of app.js and CSS styles.css
        self.assertTrue(any("app.js" in s for s in parser.scripts) or "app.js" in raw_html)
        self.assertTrue(any("styles.css" in l for l in parser.links) or "styles.css" in raw_html)

        # Verify app.js defines the 6 standard stages
        app_js_path = REPO_ROOT / "cockpit" / "app.js"
        self.assertTrue(app_js_path.exists(), "cockpit/app.js must exist")
        app_js_code = app_js_path.read_text(encoding="utf-8")
        for stage in ["leads", "pitched", "interviewing", "contract_sent", "won", "closed"]:
            self.assertIn(f"'{stage}'", app_js_code)

        # Zero unescaped template syntax
        self.assertNotIn("{{", raw_html)
        self.assertNotIn("{%", raw_html)

    def test_saas_dashboard_dom_integrity(self):
        dashboard_app_path = REPO_ROOT / "ai_solutions_suite" / "saas_dashboard" / "dashboard_app.html"
        if not dashboard_app_path.exists():
            dashboard_app_path = REPO_ROOT / "ai_solutions_suite" / "saas_dashboard" / "dashboard_preview.html"

        self.assertTrue(dashboard_app_path.exists(), "Executive SaaS dashboard HTML must exist")
        raw_html = dashboard_app_path.read_text(encoding="utf-8")

        self.assertIn("<!DOCTYPE html>", raw_html)
        self.assertIn("Revenue", raw_html)
        self.assertIn("Telemetry", raw_html)

        # Check for card/grid structure
        parser = self.SimpleTagCollector()
        parser.feed(raw_html)
        self.assertIn("div", parser.tags)
        self.assertIn("table", parser.tags)


if __name__ == "__main__":
    unittest.main()
