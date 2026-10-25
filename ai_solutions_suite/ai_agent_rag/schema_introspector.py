"""
Enterprise Relational Database Schema Introspector
===================================================
Dynamic schema extraction, table/column metadata inspection, and DDL prompt generation
for enterprise NL-to-SQL agents.
Author: Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

import sqlite3
from typing import Dict, List, Any, Optional, Union

class SchemaIntrospector:
    """Introspects relational databases to extract tables, columns, types, and constraints."""

    def __init__(self, db_source: Optional[Union[str, sqlite3.Connection]] = None):
        self.db_source = db_source
        self._cached_schema: Optional[Dict[str, Any]] = None

    def _get_connection(self) -> sqlite3.Connection:
        if isinstance(self.db_source, sqlite3.Connection):
            return self.db_source
        if isinstance(self.db_source, str) and self.db_source:
            return sqlite3.connect(self.db_source)
        return sqlite3.connect(":memory:")

    def introspect(self, db_source: Optional[Union[str, sqlite3.Connection]] = None) -> Dict[str, Any]:
        """Inspects all user tables, columns, data types, primary keys, and foreign keys."""
        source = db_source or self.db_source
        if source is not None:
            self.db_source = source

        conn = self._get_connection()
        schema: Dict[str, Any] = {"database_type": "sqlite", "tables": {}}

        try:
            cursor = conn.cursor()
            # Fetch user tables (exclude internal sqlite system tables)
            cursor.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            tables = cursor.fetchall()

            for table_name, create_sql in tables:
                # Introspect columns
                cursor.execute(f"PRAGMA table_info('{table_name}');")
                columns_info = cursor.fetchall()
                # col_info: (cid, name, type, notnull, dflt_value, pk)
                columns = []
                for col in columns_info:
                    columns.append({
                        "name": col[1],
                        "type": col[2] or "ANY",
                        "not_null": bool(col[3]),
                        "default_value": col[4],
                        "is_primary_key": bool(col[5])
                    })

                # Introspect foreign keys
                cursor.execute(f"PRAGMA foreign_key_list('{table_name}');")
                fk_info = cursor.fetchall()
                # (id, seq, table, from, to, on_update, on_delete, match)
                foreign_keys = []
                for fk in fk_info:
                    foreign_keys.append({
                        "referred_table": fk[2],
                        "from_column": fk[3],
                        "to_column": fk[4]
                    })

                schema["tables"][table_name] = {
                    "name": table_name,
                    "columns": columns,
                    "foreign_keys": foreign_keys,
                    "create_sql": create_sql
                }

            self._cached_schema = schema
            return schema
        finally:
            if not isinstance(self.db_source, sqlite3.Connection):
                conn.close()

    def format_schema_ddl(self, schema: Optional[Dict[str, Any]] = None) -> str:
        """Formats the schema into a concise, readable Markdown/DDL summary for LLM prompt injection."""
        target_schema = schema or self._cached_schema or self.introspect()
        lines = ["### ENTERPRISE DATABASE SCHEMA DEFINITIONS:"]

        for table_name, table_meta in target_schema.get("tables", {}).items():
            lines.append(f"\nTable: `{table_name}`")
            lines.append("Columns:")
            for col in table_meta["columns"]:
                pk_flag = " [PRIMARY KEY]" if col["is_primary_key"] else ""
                nn_flag = " [NOT NULL]" if col["not_null"] else ""
                lines.append(f"  - `{col['name']}` ({col['type']}){pk_flag}{nn_flag}")

            if table_meta.get("foreign_keys"):
                lines.append("Relations:")
                for fk in table_meta["foreign_keys"]:
                    lines.append(
                        f"  - References `{fk['referred_table']}({fk['to_column']})` via `{fk['from_column']}`"
                    )

        return "\n".join(lines)

    def get_sample_rows(self, table_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Safely fetches sample rows from an introspected table for context few-shotting."""
        # Sanitize table name to prevent SQL injection in internal introspection
        schema = self._cached_schema or self.introspect()
        if table_name not in schema.get("tables", {}):
            raise ValueError(f"Table '{table_name}' does not exist in schema.")

        conn = self._get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {int(limit)};")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            if not isinstance(self.db_source, sqlite3.Connection):
                conn.close()

    @staticmethod
    def create_sample_database(db_path: str = ":memory:") -> sqlite3.Connection:
        """Generates a rich enterprise mock SQLite database for development and verification."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS enterprise_orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            service_tier TEXT NOT NULL,
            total_usd REAL NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('completed', 'pending', 'cancelled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ai_agents (
            agent_id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            model_provider TEXT NOT NULL,
            throughput_rps REAL NOT NULL,
            error_rate REAL NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS api_metrics (
            metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            latency_ms REAL NOT NULL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO enterprise_orders (customer_name, service_tier, total_usd, status) VALUES
            ('Acme Corp', 'Enterprise', 12500.0, 'completed'),
            ('Nexus Health', 'Enterprise Plus', 24000.0, 'completed'),
            ('Apex Logistics', 'Standard', 4500.0, 'pending'),
            ('Solaria AI', 'Custom Tier', 38000.0, 'completed'),
            ('Vanguard Security', 'Enterprise', 15000.0, 'cancelled');

        INSERT INTO ai_agents (agent_id, agent_name, model_provider, throughput_rps, error_rate, status) VALUES
            ('agent_rag_01', 'Enterprise RAG Agent', 'Anthropic Claude 3.5', 42.5, 0.001, 'active'),
            ('agent_sql_02', 'Safe SQL Query Synthesizer', 'OpenAI GPT-4o', 35.8, 0.002, 'active'),
            ('agent_scraper_03', 'Resilient Data Miner', 'Local LLM / Regex', 120.0, 0.005, 'active');

        INSERT INTO api_metrics (endpoint, status_code, latency_ms) VALUES
            ('/api/v1/rag/query', 200, 24.5),
            ('/api/v1/sql/execute', 200, 18.2),
            ('/api/v1/telemetry/stream', 200, 12.0),
            ('/api/v1/auth/jwt', 200, 9.8);
        """)
        conn.commit()
        return conn
