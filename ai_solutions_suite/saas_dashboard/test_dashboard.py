"""
Automated Test Suite: Executive SaaS Dashboard Solution
========================================================
Verifies DOM structure of standalone dashboard_app.html, Anti-Slop UI styles,
telemetry calculations, interactive JS event routines, and modular React component suite.
Author: Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

import unittest
import os
import re
from html.parser import HTMLParser

DASHBOARD_DIR = os.path.dirname(__file__)
HTML_PATH = os.path.join(DASHBOARD_DIR, "dashboard_app.html")
COMPONENTS_DIR = os.path.join(DASHBOARD_DIR, "components")

class SimpleDOMParser(HTMLParser):
    """Extracts tag names, IDs, classes, and text elements for DOM validation."""
    def __init__(self):
        super().__init__()
        self.tags = []
        self.ids = set()
        self.classes = set()
        self.buttons = []
        self.inputs = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        attr_dict = dict(attrs)
        if "id" in attr_dict:
            self.ids.add(attr_dict["id"])
        if "class" in attr_dict:
            for c in attr_dict["class"].split():
                self.classes.add(c)
        if tag == "button":
            self.buttons.append(attr_dict)
        if tag == "input":
            self.inputs.append(attr_dict)

class TestExecutiveSaaSDashboard(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.exists(HTML_PATH), f"File {HTML_PATH} does not exist.")
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            self.html_content = f.read()

        self.parser = SimpleDOMParser()
        self.parser.feed(self.html_content)

    # 1. Structural HTML & Meta Tests
    def test_html_document_structure(self):
        self.assertIn("<!DOCTYPE html>", self.html_content)
        self.assertIn("<html lang=\"en\">", self.html_content)
        self.assertIn("<meta name=\"viewport\"", self.html_content)
        self.assertIn("<title>Apex Executive Operations & SaaS Telemetry Command Center</title>", self.html_content)

    # 2. Anti-Slop UI & Color Palette Tests
    def test_anti_slop_dark_mode_palette(self):
        # Must enforce refined dark palette without generic neon AI slop
        self.assertIn("--bg-canvas: #09090b", self.html_content)
        self.assertIn("--bg-card:", self.html_content)
        self.assertIn("--border-subtle:", self.html_content)
        self.assertIn("--emerald-glow: #10b981", self.html_content)
        self.assertIn("--cyan-glow: #06b6d4", self.html_content)

        # Ensure no garish neon purple background gradients
        self.assertNotIn("linear-gradient(to right, #ff00ff", self.html_content)

    # 3. Telemetry KPI Grid Tests
    def test_telemetry_kpi_card_elements(self):
        required_ids = ["val-arr", "val-mrr", "val-throughput", "val-fleet", "val-cache"]
        for elem_id in required_ids:
            self.assertIn(elem_id, self.parser.ids, f"Missing KPI element ID: {elem_id}")

        self.assertIn("$482,500", self.html_content)
        self.assertIn("4,820 req/s", self.html_content)
        self.assertIn("18 / 18 Active", self.html_content)
        self.assertIn("96.4%", self.html_content)

    # 4. Revenue Trajectory Visualizer Chart Tests
    def test_revenue_chart_svg_rendering(self):
        self.assertIn("<svg", self.html_content)
        self.assertIn("viewBox=\"0 0 1000 220\"", self.html_content)
        self.assertIn("<linearGradient id=\"areaGradient\"", self.html_content)
        self.assertIn("Nov", self.html_content)
        self.assertIn("Oct", self.html_content)
        self.assertIn("stroke=\"#3b82f6\"", self.html_content)
        self.assertIn("stroke=\"#10b981\"", self.html_content)

    # 5. Active AI Agent Fleet Monitor Table Tests
    def test_agent_fleet_table_structure(self):
        self.assertIn("fleet-table", self.parser.ids)
        self.assertIn("RAG-Worker-Alpha", self.html_content)
        self.assertIn("SafeSQL-Barrier-01", self.html_content)
        self.assertIn("Scraper-Crawler-09", self.html_content)
        self.assertIn("Contract-Hunter-Bot", self.html_content)
        self.assertIn("Anomaly-Sentinel", self.html_content)

    # 6. Real-Time Transaction Stream & Filter Tests
    def test_transaction_stream_and_controls(self):
        self.assertIn("transactions-table", self.parser.ids)
        self.assertIn("stream-search", self.parser.ids)

        # Check filter buttons
        filter_buttons = [b.get("data-filter") for b in self.parser.buttons if "data-filter" in b]
        self.assertIn("all", filter_buttons)
        self.assertIn("success", filter_buttons)
        self.assertIn("latency", filter_buttons)

        # Check export triggers
        self.assertIn("exportData('csv')", self.html_content)
        self.assertIn("exportData('json')", self.html_content)

    # 7. JavaScript Telemetry Engine Tests
    def test_javascript_event_handlers(self):
        required_js_functions = [
            "toggleTelemetry",
            "startTelemetrySimulation",
            "appendSimulatedTransaction",
            "setFilter",
            "handleSearch",
            "applyFilters",
            "exportData"
        ]
        for func_name in required_js_functions:
            pattern = rf"\bfunction\s+{func_name}\b"
            self.assertTrue(
                bool(re.search(pattern, self.html_content)),
                f"Missing JS function: {func_name}"
            )

    # 8. Telemetry Logic & Financial Sanity Tests
    def test_telemetry_financial_calculations(self):
        # Extract numerical ARR and MRR
        arr_match = re.search(r'\$([0-9,]+)', self.html_content)
        self.assertIsNotNone(arr_match)
        arr_val = float(arr_match.group(1).replace(",", ""))

        mrr_match = re.search(r'\$([0-9,]+)/mo', self.html_content)
        self.assertIsNotNone(mrr_match)
        mrr_val = float(mrr_match.group(1).replace(",", ""))

        # ARR should equal MRR * 12 (within 0.5% variance due to rounding)
        expected_arr = mrr_val * 12
        variance = abs(arr_val - expected_arr) / arr_val
        self.assertLess(variance, 0.01, f"ARR ({arr_val}) and MRR ({mrr_val}) are inconsistent.")

    # 9. Next.js 15 Modular React Components Tests
    def test_modular_react_components_exist(self):
        expected_components = [
            "ExecutiveDashboard.tsx",
            "TelemetryGrid.tsx",
            "RevenueChart.tsx",
            "AgentFleetTable.tsx",
            "TransactionStream.tsx",
            "index.ts"
        ]
        for comp in expected_components:
            path = os.path.join(COMPONENTS_DIR, comp)
            self.assertTrue(os.path.exists(path), f"Missing modular component: {path}")

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                # Verify export statement
                self.assertIn("export ", content, f"Component {comp} does not export anything.")
                # Verify dark mode tailwind styles on tsx components
                if comp.endswith(".tsx"):
                    self.assertIn("zinc-", content, f"Component {comp} missing zinc color tokens.")

if __name__ == "__main__":
    unittest.main()
