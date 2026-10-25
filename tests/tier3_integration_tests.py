"""
Tier 3: Cross-Feature Integration Test Suite
============================================
Master E2E Testing Suite - Milestone 4
Validates end-to-end data flow and contracts across subsystems:
1. Hunter Export -> Cockpit Sync (`/api/opportunities/sync`).
2. Pipeline Stage Mutation -> Real-time Revenue KPI Recalculation (`/api/metrics`).
3. Atomic State Persistence on Reload (`pipeline_state.json`).
4. Cross-Subsystem Dynamic Pitch Generation.
5. Scraper Pipeline Output -> RAG Agent Ingestion & Hybrid Retrieval.

Author: Eng. Abdelrahman Rashad & QA Automation Track
"""

import sys
import os
import json
import unittest
import tempfile
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contract_hunter.remote_contract_hunter import RemoteContractHunter
from ai_solutions_suite.ai_agent_rag.rag_agent import EnterpriseRAGAgent
from ai_solutions_suite.python_scraper_engine.scraper_engine import ScraperPipeline
from cockpit.server import app, load_pipeline_data, atomic_save_json, PIPELINE_FILE, HUNTER_EXPORT_FILE
from starlette.testclient import TestClient


class TestCrossFeatureIntegration(unittest.TestCase):
    """Tier 3: Subsystem Integration & Cross-Cutting Flows."""

    def setUp(self):
        self.client = TestClient(app)
        self.created_deal_ids = []

    def tearDown(self):
        # Clean up any created test deals
        for deal_id in self.created_deal_ids:
            try:
                self.client.delete(f"/api/pipeline/{deal_id}")
            except Exception:
                pass

    def test_hunter_export_to_cockpit_sync_flow(self):
        # 1. Hunter generates or verifies export exists
        hunter = RemoteContractHunter()
        hunter._get_curated_fallback_jobs() if hasattr(hunter, "_get_curated_fallback_jobs") else hunter.get_curated_fallback_jobs()
        export_path = REPO_ROOT / "contract_hunter" / "curated_high_ticket_jobs.json"
        hunter.export_to_json(str(export_path))
        self.assertTrue(export_path.exists())

        # 2. Cockpit API syncs opportunities
        sync_res = self.client.post("/api/opportunities/sync")
        self.assertEqual(sync_res.status_code, 200)
        sync_data = sync_res.json()
        self.assertEqual(sync_data["status"], "synced")
        self.assertGreaterEqual(sync_data["count"], 1)

        # 3. Cockpit opportunities endpoint serves the ingested leads
        opps_res = self.client.get("/api/opportunities")
        self.assertEqual(opps_res.status_code, 200)
        opps = opps_res.json()
        self.assertGreaterEqual(len(opps), 1)

        # Verify opportunity fields comply with M1-M3 interface contract
        first = opps[0]
        self.assertIn("id", first)
        self.assertIn("title", first)
        self.assertIn("company", first)
        self.assertIn("monthly_rate_usd_min", first)
        self.assertIn("skills_tags", first)

    def test_pipeline_mutation_to_revenue_kpi_flow(self):
        # 1. Baseline metrics
        initial_metrics = self.client.get("/api/metrics").json()
        base_mrr = initial_metrics["active_monthly_revenue"]
        base_in_flight = initial_metrics["in_flight_pipeline_value"]

        # 2. Add deal in 'leads' ($5,000/mo)
        deal_payload = {
            "title": "Fractional Architecture Retainer",
            "company": "Integration Flow Systems",
            "stage": "leads",
            "monthly_value": 5000.0,
            "source": "Hacker News",
            "skills": ["next.js", "python", "ai"]
        }
        create_res = self.client.post("/api/pipeline", json=deal_payload)
        self.assertEqual(create_res.status_code, 201)
        deal_id = create_res.json()["id"]
        self.created_deal_ids.append(deal_id)

        # 3. Move to 'interviewing' -> Should expand in_flight_pipeline_value
        put_interview = self.client.put(f"/api/pipeline/{deal_id}", json={"stage": "interviewing"})
        self.assertEqual(put_interview.status_code, 200)

        interview_metrics = self.client.get("/api/metrics").json()
        self.assertEqual(interview_metrics["in_flight_pipeline_value"], base_in_flight + 5000.0)

        # 4. Advance to 'contract_sent' -> Still in-flight
        put_contract = self.client.put(f"/api/pipeline/{deal_id}", json={"stage": "contract_sent"})
        self.assertEqual(put_contract.status_code, 200)

        contract_metrics = self.client.get("/api/metrics").json()
        self.assertEqual(contract_metrics["in_flight_pipeline_value"], base_in_flight + 5000.0)

        # 5. Advance to 'won' -> In-flight drops back, active MRR gains $5,000, ARR gains $60,000
        put_won = self.client.put(f"/api/pipeline/{deal_id}", json={"stage": "won"})
        self.assertEqual(put_won.status_code, 200)

        won_metrics = self.client.get("/api/metrics").json()
        self.assertEqual(won_metrics["active_monthly_revenue"], base_mrr + 5000.0)
        self.assertEqual(won_metrics["annual_recurring_revenue"], (base_mrr + 5000.0) * 12.0)
        self.assertEqual(won_metrics["in_flight_pipeline_value"], base_in_flight)

    def test_state_persistence_reload_across_restarts(self):
        # 1. Create a persistent deal via API
        deal_payload = {
            "title": "Persistent Cloud Architecture",
            "company": "ColdRestart Corp",
            "stage": "pitched",
            "monthly_value": 4800.0,
            "source": "RemoteOK"
        }
        res = self.client.post("/api/pipeline", json=deal_payload)
        self.assertEqual(res.status_code, 201)
        deal_id = res.json()["id"]
        self.created_deal_ids.append(deal_id)

        # 2. Directly inspect the JSON file on disk (bypassing in-memory cache)
        self.assertTrue(PIPELINE_FILE.exists())
        with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
            disk_data = json.load(f)

        disk_deal = next((d for d in disk_data["deals"] if d["id"] == deal_id), None)
        self.assertIsNotNone(disk_deal, "Deal must be immediately flushed to disk via atomic persistence")
        self.assertEqual(disk_deal["company"], "ColdRestart Corp")
        self.assertEqual(disk_deal["monthly_value"], 4800.0)

    def test_cross_subsystem_pitch_generation(self):
        # 1. Query an ingested opportunity
        opps = self.client.get("/api/opportunities").json()
        self.assertGreaterEqual(len(opps), 1)
        selected_opp = opps[0]

        # 2. Generate pitch using opportunity's extracted metadata
        pitch_payload = {
            "position": selected_opp["title"],
            "company": selected_opp["company"],
            "skills": selected_opp.get("skills_tags", ["next.js", "python"]),
            "tone": "cto",
            "custom_notes": "Identified in fresh feed sync"
        }
        pitch_res = self.client.post("/api/pitch/generate", json=pitch_payload)
        self.assertEqual(pitch_res.status_code, 200)
        pitch_data = pitch_res.json()

        # 3. Assert pitch contains target company and matched skills
        self.assertIn(selected_opp["company"], pitch_data["body"])
        self.assertIn("resilient architectures", pitch_data["body"])
        self.assertIn("Abdelrahman Rashad", pitch_data["body"])

    def test_scraper_to_rag_ingestion_pipeline(self):
        # 1. Run Scraper Pipeline to extract structured entities
        scraper = ScraperPipeline(target_domain="saas-directory.com")
        html_input = """
        <div class="item-card"><span class="title">Enterprise RAG API</span><span class="price">$3,500</span></div>
        <div class="item-card"><span class="title">Automated Data Mining Pipeline</span><span class="price">$2,800</span></div>
        """
        extracted = scraper.process_raw_html(html_input)
        self.assertEqual(len(extracted), 2)

        # 2. Ingest scraped records into Enterprise RAG Agent
        agent = EnterpriseRAGAgent(mock_mode=True)
        rag_docs = [
            {
                "id": f"doc_{item.get('id', idx+1)}",
                "content": f"Product: {item['title']} - Verified Market Price: {item['price']}. Enterprise high-ticket solution."
            }
            for idx, item in enumerate(extracted)
        ]
        agent.ingest_documents(rag_docs)

        # 3. Retrieve relevant knowledge through RAG hybrid engine
        retrieval = agent.retrieve("Market Price Enterprise RAG API")
        self.assertGreaterEqual(len(retrieval), 1)
        self.assertEqual(retrieval[0]["doc_id"], f"doc_{extracted[0].get('id', 1)}")
        self.assertIn("3500", retrieval[0]["content"])


if __name__ == "__main__":
    unittest.main()
