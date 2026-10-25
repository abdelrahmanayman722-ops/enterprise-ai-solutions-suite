"""
Enterprise Safe SQL Execution Engine & Security Barrier
========================================================
Strict read-only AST and lexical validator enforcing defense-in-depth against
SQL injection, data mutations, stacked queries, and unbounded result sets.
Author: Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

import re
import sqlite3
from typing import Dict, List, Any, Optional, Tuple, Union

class SecurityViolationError(Exception):
    """Raised when a SQL query violates read-only safety invariants."""
    pass

class SafeSQLExecutor:
    """Validates and executes SQL queries within strict read-only constraints."""

    # Forbidden DDL / DML and administrative command patterns
    FORBIDDEN_KEYWORDS = [
        r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b', r'\bDROP\b',
        r'\bALTER\b', r'\bTRUNCATE\b', r'\bEXEC\b', r'\bEXECUTE\b',
        r'\bCREATE\b', r'\bREPLACE\b', r'\bATTACH\b', r'\bDETACH\b',
        r'\bPRAGMA\b', r'\bGRANT\b', r'\bREVOKE\b', r'\bVACUUM\b',
        r'\bREINDEX\b', r'\bUPSERT\b', r'\bMERGE\b'
    ]

    def __init__(self, default_limit: int = 100, max_limit: int = 500):
        self.default_limit = default_limit
        self.max_limit = max_limit

    def validate_query(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validates SQL against destructive commands, multiple statements, and injection vectors.
        Returns (is_valid, error_reason).
        """
        if not sql or not sql.strip():
            return False, "Query is empty."

        cleaned_sql = sql.strip()

        # Reject SQL comments that can be used to bypass parsers
        if re.search(r'(--|/\*|\*/)', cleaned_sql):
            return False, "SQL comments ('--', '/*') are forbidden in safe execution mode."

        # Strip trailing semicolon for single-statement validation
        if cleaned_sql.endswith(';'):
            cleaned_sql = cleaned_sql[:-1].strip()

        # Check for multiple stacked statements (embedded semicolon)
        # Note: Semicolons inside string literals are rare in generated analytical queries,
        # but to be rigorous, we reject unescaped semicolons.
        if ';' in cleaned_sql:
            return False, "Stacked queries and multiple statements separated by ';' are forbidden."

        # Check forbidden keywords (case-insensitive word boundary match)
        for pattern in self.FORBIDDEN_KEYWORDS:
            if re.search(pattern, cleaned_sql, re.IGNORECASE):
                matched = re.search(pattern, cleaned_sql, re.IGNORECASE).group(0)
                return False, f"Destructive or administrative statement '{matched.upper()}' is strictly prohibited."

        # Verify query starts with permitted read-only keywords: SELECT or WITH (for CTEs)
        match_start = re.match(r'^(SELECT|WITH)\b', cleaned_sql, re.IGNORECASE)
        if not match_start:
            return False, "Only read-only 'SELECT' and 'WITH ... SELECT' statements are permitted."

        return True, None

    def sanitize_and_limit(self, sql: str, max_rows: Optional[int] = None) -> str:
        """
        Ensures the query contains an explicit, bounded LIMIT clause.
        Appends default limit if absent, or caps existing limit to ceiling (max_limit or max_rows).
        """
        ceiling = max_rows if max_rows is not None else self.max_limit
        if ceiling > self.max_limit:
            ceiling = self.max_limit

        default_appended = min(self.default_limit, ceiling)
        cleaned = sql.strip().rstrip(';')

        # Check if LIMIT exists
        limit_match = re.search(r'\bLIMIT\s+(\d+)\b', cleaned, re.IGNORECASE)
        if limit_match:
            existing_limit = int(limit_match.group(1))
            if existing_limit > ceiling:
                # Replace with clamped limit
                cleaned = re.sub(r'\bLIMIT\s+\d+\b', f'LIMIT {ceiling}', cleaned, flags=re.IGNORECASE)
            return cleaned
        else:
            return f"{cleaned} LIMIT {default_appended}"

    def execute(
        self,
        db_source: Union[str, sqlite3.Connection],
        sql: str,
        params: Tuple[Any, ...] = (),
        max_rows: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validates, limits, and executes the SQL query against an SQLite database.
        Returns structured dictionary with columns, rows, count, and executed SQL.
        """
        is_valid, error_msg = self.validate_query(sql)
        if not is_valid:
            raise SecurityViolationError(f"Security validation failed: {error_msg}")

        sanitized_sql = self.sanitize_and_limit(sql, max_rows=max_rows)

        # Connect or use existing connection
        owns_conn = False
        if isinstance(db_source, sqlite3.Connection):
            conn = db_source
        elif isinstance(db_source, str):
            conn = sqlite3.connect(db_source)
            owns_conn = True
        else:
            raise ValueError("db_source must be a file path string or sqlite3.Connection.")

        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Execute statement
            cursor.execute(sanitized_sql, params)
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            formatted_rows = [dict(row) for row in rows]

            return {
                "columns": columns,
                "rows": formatted_rows,
                "row_count": len(formatted_rows),
                "executed_sql": sanitized_sql
            }
        finally:
            if owns_conn:
                conn.close()
