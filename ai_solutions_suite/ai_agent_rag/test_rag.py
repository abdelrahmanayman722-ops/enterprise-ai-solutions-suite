"""
Automated Test Suite: Enterprise AI Agent / RAG Solution
=========================================================
Verifies hybrid BM25/Dense RRF retrieval, Safe SQL AST/regex security barrier,
schema introspection, conversational memory, hallucination guardrails, and unified agent API.
Author: Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

import unittest
import sqlite3
import os
import sys

# Support direct test execution as well as package discovery
sys.path.insert(0, os.path.dirname(__file__))

from rag_agent import EnterpriseRAGAgent
from hybrid_retriever import HybridRetriever, DocumentChunk
from safe_sql_executor import SafeSQLExecutor, SecurityViolationError
from schema_introspector import SchemaIntrospector
from conversational_memory import ConversationalMemory

class TestEnterpriseRAGAgent(unittest.TestCase):
    def setUp(self):
        self.agent = EnterpriseRAGAgent(mock_mode=True)
        self.docs = [
            {"id": "doc1", "content": "Next.js 15 uses React Server Components by default with App Router and Turbopack."},
            {"id": "doc2", "content": "Node.js Express provides robust middleware handling for RESTful microservice APIs."},
            {"id": "doc3", "content": "Python Playwright enables fast web scraping, anti-detection, and headless browser automation."}
        ]
        self.agent.ingest_documents(self.docs)

    # 1. Backwards compatibility test cases
    def test_ingestion(self):
        self.assertEqual(len(self.agent.corpus), 3)

    def test_retrieval(self):
        results = self.agent.retrieve("Next.js App Router")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["doc_id"], "doc1")
        self.assertIn("React Server Components", results[0]["content"])

    def test_augmented_prompt_generation(self):
        res = self.agent.generate_augmented_prompt("How does Playwright work for scraping?")
        self.assertEqual(res["sources"][0], "doc3")
        self.assertIn("Python Playwright", res["augmented_prompt"])
        self.assertIn("USER QUERY:", res["augmented_prompt"])

    # 2. Hybrid Retrieval & RRF tests
    def test_hybrid_bm25_dense_rrf(self):
        retriever = HybridRetriever(rrf_k=60)
        retriever.ingest_documents(self.docs)
        results = retriever.retrieve("Playwright headless browser automation", top_k=2)

        self.assertGreaterEqual(len(results), 1)
        top = results[0]
        self.assertEqual(top["doc_id"], "doc3")
        self.assertGreater(top["bm25_score"], 0.0)
        self.assertGreater(top["dense_score"], 0.0)
        self.assertGreater(top["score"], 0.0)
        self.assertGreaterEqual(top["confidence"], 0.40)

    # 3. Schema Introspector tests
    def test_schema_introspection(self):
        introspector = SchemaIntrospector(self.agent.db_source)
        schema = introspector.introspect()

        self.assertIn("enterprise_orders", schema["tables"])
        self.assertIn("ai_agents", schema["tables"])

        order_cols = [c["name"] for c in schema["tables"]["enterprise_orders"]["columns"]]
        self.assertIn("total_usd", order_cols)
        self.assertIn("status", order_cols)

        ddl = introspector.format_schema_ddl(schema)
        self.assertIn("Table: `enterprise_orders`", ddl)
        self.assertIn("`total_usd` (REAL)", ddl)

        samples = introspector.get_sample_rows("enterprise_orders", limit=2)
        self.assertLessEqual(len(samples), 2)
        self.assertIn("customer_name", samples[0])

    # 4. Safe SQL Executor Barrier tests
    def test_safe_sql_allows_read_only(self):
        executor = SafeSQLExecutor(default_limit=50)
        res = executor.execute(self.agent.db_source, "SELECT customer_name, total_usd FROM enterprise_orders")
        self.assertIn("customer_name", res["columns"])
        self.assertIn("total_usd", res["columns"])
        self.assertGreaterEqual(res["row_count"], 1)
        self.assertIn("LIMIT 50", res["executed_sql"])

    def test_safe_sql_enforces_limit_clamping(self):
        executor = SafeSQLExecutor(default_limit=10, max_limit=100)
        res = executor.execute(self.agent.db_source, "SELECT * FROM enterprise_orders LIMIT 1000")
        self.assertIn("LIMIT 100", res["executed_sql"])

    def test_safe_sql_blocks_mutations(self):
        executor = SafeSQLExecutor()
        destructive_queries = [
            "INSERT INTO enterprise_orders (customer_name) VALUES ('Hacker')",
            "UPDATE enterprise_orders SET total_usd = 0",
            "DELETE FROM enterprise_orders WHERE order_id = 1",
            "DROP TABLE enterprise_orders",
            "ALTER TABLE enterprise_orders ADD COLUMN hacked TEXT",
            "TRUNCATE TABLE enterprise_orders",
            "ATTACH DATABASE 'malicious.db' AS mal",
            "PRAGMA table_info(enterprise_orders)"
        ]
        for query in destructive_queries:
            with self.subTest(query=query):
                with self.assertRaises(SecurityViolationError):
                    executor.execute(self.agent.db_source, query)

    def test_safe_sql_blocks_stacked_queries_and_comments(self):
        executor = SafeSQLExecutor()
        malicious = [
            "SELECT 1; DROP TABLE enterprise_orders;",
            "SELECT * FROM enterprise_orders; DELETE FROM ai_agents;",
            "SELECT * FROM enterprise_orders -- comment injection",
            "SELECT * FROM enterprise_orders /* block comment */"
        ]
        for query in malicious:
            with self.subTest(query=query):
                is_valid, reason = executor.validate_query(query)
                self.assertFalse(is_valid, f"Expected validation failure for: {query}")
                with self.assertRaises(SecurityViolationError):
                    executor.execute(self.agent.db_source, query)

    # 5. Conversational Memory tests
    def test_conversational_memory_sliding_window(self):
        memory = ConversationalMemory(window_size=4)
        for i in range(10):
            memory.add_turn(role="user", content=f"User message {i}")
            memory.add_turn(role="assistant", content=f"Assistant reply {i}")

        context = memory.get_context()
        self.assertEqual(len(context), 4)
        self.assertEqual(context[-1]["content"], "Assistant reply 9")

        history_text = memory.get_formatted_history()
        self.assertIn("Assistant: Assistant reply 9", history_text)

        search_res = memory.search_history("message 8")
        self.assertEqual(len(search_res), 1)

    # 6. Hallucination Guardrail & Fallback tests
    def test_hallucination_guardrail_triggers_fallback(self):
        # Query that has zero relevance in ingested corpus
        query = "What is the quantum telemetry flux capacitor frequency in Mars orbit?"
        res = self.agent.query(query)

        self.assertTrue(res["fallback_triggered"])
        self.assertIn("ERR_INSUFFICIENT_CONTEXT", res["answer"])
        self.assertLess(res["confidence"], 0.40)

    # 7. Unified Interface Contract test
    def test_unified_query_interface_contract(self):
        # Interface Contract:
        # agent.query(prompt: str) -> dict {"answer": str, "sources": list, "confidence": float, "executed_sql": Optional[str]}

        # Test RAG query
        rag_res = self.agent.query("What does Next.js 15 use for routing?")
        self.assertIn("answer", rag_res)
        self.assertIn("sources", rag_res)
        self.assertIn("confidence", rag_res)
        self.assertIn("executed_sql", rag_res)
        self.assertIn("doc1", rag_res["sources"])
        self.assertFalse(rag_res["fallback_triggered"])

        # Test Safe SQL query
        sql_res = self.agent.query("Calculate total revenue from completed orders")
        self.assertIn("answer", sql_res)
        self.assertIsNotNone(sql_res["executed_sql"])
        self.assertIn("SUM(total_usd)", sql_res["executed_sql"])
        self.assertIn("total revenue", sql_res["answer"].lower())
        self.assertFalse(sql_res["fallback_triggered"])

    def test_empty_query_handling(self):
        res = self.agent.query("   ")
        self.assertEqual(res["intent"], "empty")
        self.assertIn("non-empty", res["answer"])

if __name__ == "__main__":
    unittest.main()
