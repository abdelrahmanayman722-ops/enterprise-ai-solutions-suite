"""
Automated Test Suite for Executive Pipeline Cockpit (Milestone 3)
Verifies all REST API endpoints, atomic persistence, Kanban deal mutations,
pitch generation algorithms, revenue KPI metrics, and static asset serving.
"""

import json
import os
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from cockpit.server import app, VALID_STAGES, PIPELINE_FILE, atomic_save_json, load_pipeline_data


class TestCockpitAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Backup pipeline state if exists
        cls.backup_data = None
        if PIPELINE_FILE.exists():
            with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
                cls.backup_data = json.load(f)

    @classmethod
    def tearDownClass(cls):
        # Restore pipeline state
        if cls.backup_data is not None:
            atomic_save_json(PIPELINE_FILE, cls.backup_data)

    def test_health_check(self):
        """Validates /api/health provides accurate telemetry and status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "1.0.0")
        self.assertIn("active_pipeline_count", data)
        self.assertIn("active_mrr", data)
        self.assertIn("uptime_seconds", data)
        self.assertGreaterEqual(data["active_pipeline_count"], 0)

    def test_opportunities_feed_and_filtering(self):
        """Validates /api/opportunities filtering by min_salary, tags, source, and search."""
        # 1. Base query
        res = self.client.get("/api/opportunities")
        self.assertEqual(res.status_code, 200)
        all_opps = res.json()
        self.assertIsInstance(all_opps, list)
        self.assertGreater(len(all_opps), 0)

        # 2. Min salary filter ($5,000 threshold)
        res_high = self.client.get("/api/opportunities?min_salary=5000")
        self.assertEqual(res_high.status_code, 200)
        high_opps = res_high.json()
        for opp in high_opps:
            opp_max = opp.get("monthly_rate_usd_max", opp.get("monthly_rate_usd_min", 0))
            self.assertGreaterEqual(opp_max, 5000)

        # 3. Tags filter (python)
        res_py = self.client.get("/api/opportunities?tags=python")
        self.assertEqual(res_py.status_code, 200)
        py_opps = res_py.json()
        for opp in py_opps:
            skills = [s.lower() for s in opp.get("skills_tags", [])]
            self.assertTrue(any("python" in s for s in skills))

        # 4. Search filter
        res_search = self.client.get("/api/opportunities?search=DuckDuckGo")
        self.assertEqual(res_search.status_code, 200)
        search_opps = res_search.json()
        self.assertTrue(any("duckduckgo" in opp.get("company", "").lower() for opp in search_opps))

    def test_opportunities_sync(self):
        """Validates /api/opportunities/sync successfully reloads and reports sync status."""
        res = self.client.post("/api/opportunities/sync")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "synced")
        self.assertIn("count", data)
        self.assertGreaterEqual(data["count"], 1)

    def test_pipeline_kanban_grouping(self):
        """Validates /api/pipeline returns deals grouped correctly across 6 stages."""
        res = self.client.get("/api/pipeline")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("stages", data)
        self.assertIn("deals", data)
        stages = data["stages"]

        for stage in VALID_STAGES:
            self.assertIn(stage, stages)
            self.assertIsInstance(stages[stage], list)

        # Check top-level convenience stage keys
        for stage in VALID_STAGES:
            self.assertIn(stage, data)
            self.assertEqual(len(data[stage]), len(stages[stage]))

    def test_pipeline_deal_crud_lifecycle(self):
        """Validates full deal lifecycle: Create -> Read -> Update Stage -> Delete."""
        # 1. Create deal
        new_deal_payload = {
            "title": "Principal AI Architecture Contractor",
            "company": "VentureScale Systems",
            "stage": "leads",
            "monthly_value": 5800.0,
            "source": "Hacker News",
            "skills": ["next.js", "python", "ai", "fastapi"],
            "contact_name": "Alexander Hayes (CTO)",
            "contact_email": "a.hayes@venturescale.tech",
            "notes": "Fast-growing Series A startup needing principal architect to ship RAG enterprise system.",
        }

        res_create = self.client.post("/api/pipeline", json=new_deal_payload)
        self.assertEqual(res_create.status_code, 201)
        deal = res_create.json()
        deal_id = deal["id"]
        self.assertTrue(deal_id.startswith("deal-"))
        self.assertEqual(deal["stage"], "leads")
        self.assertEqual(deal["monthly_value"], 5800.0)

        # 2. Read single deal
        res_get = self.client.get(f"/api/pipeline/{deal_id}")
        self.assertEqual(res_get.status_code, 200)
        retrieved = res_get.json()
        self.assertEqual(retrieved["id"], deal_id)
        self.assertEqual(retrieved["company"], "VentureScale Systems")

        # 3. Update stage: leads -> interviewing
        res_update1 = self.client.put(
            f"/api/pipeline/{deal_id}",
            json={"stage": "interviewing", "notes": "Intro call finished. Deep technical interview booked."},
        )
        self.assertEqual(res_update1.status_code, 200)
        updated1 = res_update1.json()
        self.assertEqual(updated1["stage"], "interviewing")
        self.assertIn("Deep technical", updated1["notes"])

        # 4. Update stage: interviewing -> won ($6,000/mo)
        res_update2 = self.client.put(
            f"/api/pipeline/{deal_id}",
            json={"stage": "won", "monthly_value": 6000.0},
        )
        self.assertEqual(res_update2.status_code, 200)
        updated2 = res_update2.json()
        self.assertEqual(updated2["stage"], "won")
        self.assertEqual(updated2["monthly_value"], 6000.0)

        # 5. Delete deal
        res_delete = self.client.delete(f"/api/pipeline/{deal_id}")
        self.assertEqual(res_delete.status_code, 200)
        self.assertEqual(res_delete.json()["status"], "deleted")

        # 6. Verify 404 after deletion
        res_verify_gone = self.client.get(f"/api/pipeline/{deal_id}")
        self.assertEqual(res_verify_gone.status_code, 404)

    def test_pipeline_invalid_stage_validation(self):
        """Validates that invalid Kanban stages are rejected with 400 Bad Request."""
        # 1. Invalid creation stage
        bad_create = {
            "title": "Invalid Role",
            "company": "Bad Stage Inc",
            "stage": "non_existent_stage",
            "monthly_value": 4000.0,
        }
        res_create = self.client.post("/api/pipeline", json=bad_create)
        self.assertEqual(res_create.status_code, 400)

        # 2. Invalid update stage
        # First create valid deal
        res_valid = self.client.post(
            "/api/pipeline",
            json={"title": "Valid Role", "company": "Good Stage Inc", "stage": "leads", "monthly_value": 4000.0},
        )
        deal_id = res_valid.json()["id"]

        try:
            res_bad_update = self.client.put(f"/api/pipeline/{deal_id}", json={"stage": "bogus_stage"})
            self.assertEqual(res_bad_update.status_code, 400)
        finally:
            self.client.delete(f"/api/pipeline/{deal_id}")

    def test_pitch_generator_all_personas(self):
        """Validates dynamic pitch generation for CTO, Founder, and Freelance personas."""
        req_base = {
            "position": "Lead Next.js & AI Solutions Architect",
            "company": "Kinetix Cloud",
            "skills": ["next.js 15", "react 19", "python", "rag", "sql"],
            "custom_notes": "Client requested sub-50ms API response time.",
            "contact_name": "Sarah Connor",
        }

        # 1. CTO tone
        cto_req = dict(req_base, tone="cto")
        res_cto = self.client.post("/api/pitch/generate", json=cto_req)
        self.assertEqual(res_cto.status_code, 200)
        cto_pitch = res_cto.json()
        self.assertIn("subject", cto_pitch)
        self.assertIn("body", cto_pitch)
        self.assertIn("Sarah Connor", cto_pitch["body"])
        self.assertIn("Architecture", cto_pitch["subject"])
        self.assertIn("sub-30ms", cto_pitch["body"])
        self.assertIn("Core Web Vitals", cto_pitch["body"])
        self.assertGreater(cto_pitch["char_count"], 100)

        # 2. Founder tone
        founder_req = dict(req_base, tone="founder")
        res_founder = self.client.post("/api/pitch/generate", json=founder_req)
        self.assertEqual(res_founder.status_code, 200)
        founder_pitch = res_founder.json()
        self.assertIn("Velocity", founder_pitch["subject"])
        self.assertIn("MVP-to-Scale", founder_pitch["body"])
        self.assertIn("Abdelrahman Rashad", founder_pitch["body"])

        # 3. Freelance tone
        freelance_req = dict(req_base, tone="freelance")
        res_free = self.client.post("/api/pitch/generate", json=freelance_req)
        self.assertEqual(res_free.status_code, 200)
        free_pitch = res_free.json()
        self.assertIn("Contract Availability", free_pitch["subject"])
        self.assertIn("retainer", free_pitch["body"].lower())

    def test_metrics_calculation_and_consistency(self):
        """Validates real-time calculation of active MRR, in-flight pipeline, and win rate."""
        res_metrics = self.client.get("/api/metrics")
        self.assertEqual(res_metrics.status_code, 200)
        metrics = res_metrics.json()

        self.assertIn("active_monthly_revenue", metrics)
        self.assertIn("annual_recurring_revenue", metrics)
        self.assertIn("in_flight_pipeline_value", metrics)
        self.assertIn("total_pipeline_value", metrics)
        self.assertIn("win_rate", metrics)
        self.assertIn("stage_breakdown", metrics)

        # Consistency checks
        self.assertEqual(metrics["annual_recurring_revenue"], metrics["active_monthly_revenue"] * 12.0)
        self.assertGreaterEqual(metrics["win_rate"], 0.0)
        self.assertLessEqual(metrics["win_rate"], 100.0)

        # Stage breakdown integrity
        breakdown = metrics["stage_breakdown"]
        for stage in VALID_STAGES:
            self.assertIn(stage, breakdown)
            self.assertGreaterEqual(breakdown[stage]["count"], 0)
            self.assertGreaterEqual(breakdown[stage]["subtotal_value"], 0.0)

        # Cross-check that active MRR equals won subtotal
        self.assertEqual(metrics["active_monthly_revenue"], breakdown["won"]["subtotal_value"])

    def test_export_pipeline_formats(self):
        """Validates /api/export in JSON and CSV formats."""
        # 1. JSON export
        res_json = self.client.get("/api/export?format=json")
        self.assertEqual(res_json.status_code, 200)
        self.assertEqual(res_json.headers.get("content-type"), "application/json")
        json_data = res_json.json()
        self.assertIn("deals", json_data)

        # 2. CSV export
        res_csv = self.client.get("/api/export?format=csv")
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn("text/csv", res_csv.headers.get("content-type", ""))
        csv_text = res_csv.text
        self.assertIn("id,title,company,stage,monthly_value", csv_text)
        self.assertGreater(len(csv_text.splitlines()), 1)

    def test_pipeline_negative_value_rejected(self):
        """Validates that negative monthly deal values are rejected with 422 Unprocessable Entity."""
        bad_val_payload = {
            "title": "Invalid Negative Value",
            "company": "Bogus Corp",
            "stage": "leads",
            "monthly_value": -1500.0,
        }
        res = self.client.post("/api/pipeline", json=bad_val_payload)
        self.assertEqual(res.status_code, 422)

    def test_pipeline_nonexistent_deal_404(self):
        """Validates 404 errors when reading, updating, or deleting nonexistent deal IDs."""
        nonexistent_id = "deal-nonexistent-99999"
        res_get = self.client.get(f"/api/pipeline/{nonexistent_id}")
        self.assertEqual(res_get.status_code, 404)

        res_put = self.client.put(f"/api/pipeline/{nonexistent_id}", json={"notes": "new note"})
        self.assertEqual(res_put.status_code, 404)

        res_del = self.client.delete(f"/api/pipeline/{nonexistent_id}")
        self.assertEqual(res_del.status_code, 404)

    def test_opportunities_boundary_filtering(self):
        """Validates boundary conditions: impossible salary threshold and empty search query."""
        # Unattainable salary threshold
        res_extreme = self.client.get("/api/opportunities?min_salary=500000")
        self.assertEqual(res_extreme.status_code, 200)
        self.assertEqual(len(res_extreme.json()), 0)

        # Empty search query
        res_empty = self.client.get("/api/opportunities?search=")
        self.assertEqual(res_empty.status_code, 200)
        self.assertGreater(len(res_empty.json()), 0)

    def test_static_asset_serving(self):
        """Validates that frontend entrypoints (HTML, CSS, JS) are properly served."""
        # Root index.html
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)
        self.assertIn("text/html", res_root.headers.get("content-type", ""))
        self.assertIn("<!DOCTYPE html>", res_root.text)

        # styles.css
        res_css = self.client.get("/styles.css")
        self.assertEqual(res_css.status_code, 200)
        self.assertIn("text/css", res_css.headers.get("content-type", ""))
        self.assertIn("--bg-app", res_css.text)

        # app.js
        res_js = self.client.get("/app.js")
        self.assertEqual(res_js.status_code, 200)
        self.assertIn("javascript", res_js.headers.get("content-type", ""))
        self.assertIn("Executive Pipeline Cockpit", res_js.text)

    def test_dom_id_consistency(self):
        """Validates that every document.getElementById queried in app.js exists in index.html."""
        import re
        html_file = Path(__file__).resolve().parent / "index.html"
        js_file = Path(__file__).resolve().parent / "app.js"

        self.assertTrue(html_file.exists())
        self.assertTrue(js_file.exists())

        html_content = html_file.read_text(encoding="utf-8")
        js_content = js_file.read_text(encoding="utf-8")

        # Find all getElementById calls
        pattern = re.compile(r"document\.getElementById\(['\"]([^'\"]+)['\"]\)")
        queried_ids = set(pattern.findall(js_content))

        self.assertGreater(len(queried_ids), 10)
        missing = [elem_id for elem_id in queried_ids if f'id="{elem_id}"' not in html_content and f"id='{elem_id}'" not in html_content]

        self.assertEqual(missing, [], f"The following DOM IDs queried in app.js are missing from index.html: {missing}")


if __name__ == "__main__":
    unittest.main()
