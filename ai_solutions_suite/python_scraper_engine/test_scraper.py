"""
Automated Test Suite: Resilient Python Scraper Engine
======================================================
Verifies anti-detection headers, Client Hints, token bucket rate limiter,
data normalization, SHA-256 deduplication, schema validation quarantine,
storage exporters (JSON, CSV, SQLite UPSERT), and unified pipeline run.
Author: Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

import unittest
import os
import sys
import sqlite3
import time

# Support direct test execution as well as package discovery
sys.path.insert(0, os.path.dirname(__file__))

from scraper_engine import ScraperPipeline
from anti_detection import AntiDetectionEngine
from rate_limiter import TokenBucketRateLimiter
from normalizer import DataNormalizer
from schema_validator import SchemaValidator
from storage_exporter import StorageExporter

class TestScraperPipeline(unittest.TestCase):
    def setUp(self):
        self.scraper = ScraperPipeline("test-target.com", enable_jitter=False)
        self.test_files = []

    def tearDown(self):
        for path in self.test_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    # 1. Backwards compatibility test cases
    def test_headers_generation(self):
        h = self.scraper.get_headers()
        self.assertIn("User-Agent", h)
        self.assertIn("Accept", h)

    def test_html_parsing(self):
        mock_html = '<div class="item-card"><span class="title">Product Alpha</span><span class="price">$199</span></div>'
        records = self.scraper.process_raw_html(mock_html)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "Product Alpha")
        self.assertEqual(records[0]["price"], 199.0)

    def test_csv_export(self):
        self.scraper.extracted_records = [{"id": "1", "title": "Test", "price": 10.0}]
        path = "test_export_tmp.csv"
        self.test_files.append(path)
        self.scraper.export_csv(path)
        self.assertTrue(os.path.exists(path))

    # 2. Anti-Detection & Client Hints
    def test_anti_detection_client_hints_and_jitter(self):
        engine = AntiDetectionEngine()
        headers = engine.get_headers(referer="https://example.com")
        self.assertIn("User-Agent", headers)
        self.assertIn("Sec-Fetch-Dest", headers)
        self.assertEqual(headers["Referer"], "https://example.com")

        jitter = engine.calculate_human_jitter(0.1, 0.5)
        self.assertGreaterEqual(jitter, 0.1)
        self.assertLessEqual(jitter, 0.5)

        backoff = engine.calculate_exponential_backoff(attempt=2, base=0.1, max_b=5.0)
        self.assertGreaterEqual(backoff, 0.1)
        self.assertLessEqual(backoff, 5.0)

    # 3. Token Bucket Rate Limiter
    def test_rate_limiter_acquire_and_burst(self):
        limiter = TokenBucketRateLimiter(rate=100.0, capacity=5.0)
        # Should acquire up to capacity immediately
        for _ in range(5):
            self.assertTrue(limiter.acquire(tokens=1.0, block=False))
        # 6th should fail non-blocking when depleted
        self.assertFalse(limiter.acquire(tokens=1.0, block=False))

        # Reset should restore capacity
        limiter.reset()
        self.assertGreaterEqual(limiter.tokens_available(), 4.9)

    # 4. Data Normalizer & SHA-256 Deduplication
    def test_data_normalizer_currency_and_cleaning(self):
        normalizer = DataNormalizer()
        dirty_html = "<span>&quot;Special&quot; Enterprise &amp; Cloud&#39;s Server \n\t</span>"
        clean = normalizer.clean_text(dirty_html)
        self.assertEqual(clean, '"Special" Enterprise & Cloud\'s Server')

        # Test currency parsing
        p1 = normalizer.parse_currency("$2,450.00 / mo")
        self.assertEqual(p1["amount"], 2450.0)
        self.assertEqual(p1["currency"], "USD")
        self.assertEqual(p1["interval"], "monthly")

        p2 = normalizer.parse_currency("€120k / yr")
        self.assertEqual(p2["amount"], 120000.0)
        self.assertEqual(p2["currency"], "EUR")
        self.assertEqual(p2["interval"], "annual")

        p3 = normalizer.parse_currency("£45/hr")
        self.assertEqual(p3["amount"], 45.0)
        self.assertEqual(p3["currency"], "GBP")
        self.assertEqual(p3["interval"], "hourly")

    def test_sha256_fingerprint_deduplication(self):
        normalizer = DataNormalizer()
        rec1 = {"domain": "site.com", "title": "Senior Engineer", "url": "/job/1", "price": 5000.0}
        rec2 = {"domain": "site.com", "title": "Senior Engineer", "url": "/job/1", "price": 5000.0}

        is_new1, fp1 = normalizer.register_record(rec1)
        self.assertTrue(is_new1)
        self.assertEqual(len(fp1), 64)

        is_new2, fp2 = normalizer.register_record(rec2)
        self.assertFalse(is_new2)
        self.assertEqual(fp1, fp2)

    # 5. Schema Validator and Quarantine
    def test_schema_validator_and_quarantine(self):
        validator = SchemaValidator(min_title_len=3, max_title_len=100)
        valid_rec = {"title": "Valid Enterprise Tool", "price": 450.0}
        invalid_short = {"title": "A", "price": 450.0}
        invalid_price = {"title": "Negative Price Item", "price": -50.0}

        val_list, quar_list = validator.process([valid_rec, invalid_short, invalid_price])
        self.assertEqual(len(val_list), 1)
        self.assertEqual(val_list[0]["title"], "Valid Enterprise Tool")
        self.assertEqual(len(quar_list), 2)

        report = validator.get_quarantine_report()
        self.assertEqual(report["total_quarantined"], 2)

    # 6. Storage Exporters (JSON, CSV, SQLite UPSERT)
    def test_sqlite_upsert_storage(self):
        db_path = "test_scraped_storage_tmp.db"
        self.test_files.append(db_path)

        exporter = StorageExporter()
        records = [
            {"fingerprint": "fp_001", "id": "1", "title": "Cloud Node", "price": 120.0, "currency": "USD"},
            {"fingerprint": "fp_002", "id": "2", "title": "RAG Server", "price": 350.0, "currency": "USD"}
        ]
        inserted = exporter.export_sqlite(records, db_path=db_path)
        self.assertEqual(inserted, 2)

        # Update record with same fingerprint (UPSERT test)
        updated_records = [
            {"fingerprint": "fp_001", "id": "1", "title": "Cloud Node v2", "price": 150.0, "currency": "USD"}
        ]
        exporter.export_sqlite(updated_records, db_path=db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scraped_records")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)

        cursor.execute("SELECT title, price FROM scraped_records WHERE fingerprint = 'fp_001'")
        row = cursor.fetchone()
        self.assertEqual(row[0], "Cloud Node v2")
        self.assertEqual(row[1], 150.0)
        conn.close()

    # 7. Unified Pipeline Run Contract
    def test_pipeline_run_interface_contract(self):
        db_path = "test_pipeline_run_tmp.db"
        self.test_files.append(db_path)

        # Mock transport simulating 1 transient 429 followed by 200 OK
        call_count = [0]
        def mock_transport(url, headers):
            call_count[0] += 1
            if call_count[0] == 1:
                return 429, "Rate limited"
            return 200, '<div class="item-card"><span class="title">Next.js SaaS Boilerplate</span><span class="price">$1,800.00</span></div>'

        pipeline = ScraperPipeline(
            target_domain="saas-hub.io",
            max_retries=2,
            enable_jitter=False,
            http_transport=mock_transport
        )

        # Interface Contract: pipeline.run(target_urls: list, output_sqlite: str = "scraped_data.db") -> list[dict]
        results = pipeline.run(["https://saas-hub.io/catalog"], output_sqlite=db_path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Next.js SaaS Boilerplate")
        self.assertEqual(results[0]["price"], 1800.0)
        self.assertIn("fingerprint", results[0])

        # Verify persisted into SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scraped_records")
        db_count = cursor.fetchone()[0]
        self.assertEqual(db_count, 1)
        conn.close()

if __name__ == "__main__":
    unittest.main()
