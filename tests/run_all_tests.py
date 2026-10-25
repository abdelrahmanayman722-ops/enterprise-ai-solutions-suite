"""
Master 4-Tier E2E Test Suite Runner
===================================
The Ultimate High-Ticket Software Revenue Engine
Author: Eng. Abdelrahman Rashad & QA Automation Track

Executes all 4 Testing Tiers + Subsystem Test Suites:
- Tier 1: Unit & Component Feature Coverage (27 tests)
- Tier 2: Boundary, Corner Cases & Security Guardrails (20 tests)
- Tier 3: Cross-Feature Integration & Persistence (5 tests)
- Tier 4: Real-World Business Scenarios & DOM Smoke (4 tests)
- Subsystem Unit Test Suites (Hunter, RAG, Scraper, Dashboard, Cockpit)

Produces formatted executive summary table and guarantees exit code 0 on 100% pass.
"""

import sys
import os
import time
import unittest
import importlib
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Ensure repo root and tests directory are on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


class TimedTextTestResult(unittest.TextTestResult):
    """Custom TestResult collecting granular per-test execution duration."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_timings = {}
        self._start_time = 0.0

    def startTest(self, test):
        self._start_time = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        elapsed = time.perf_counter() - self._start_time
        test_id = test.id()
        self.test_timings[test_id] = elapsed
        super().stopTest(test)


class MasterTestRunner:
    """Orchestrates comprehensive multi-tier test execution."""

    TIERS = [
        ("Tier 1: Feature Coverage", "tier1_feature_tests", TESTS_DIR, "Feature Coverage across Hunter, RAG, Scraper, Dashboard & Cockpit API"),
        ("Tier 2: Boundary & Corner Cases", "tier2_boundary_tests", TESTS_DIR, "Fault tolerance, SQL injection barriers, empty queries & limit clamping"),
        ("Tier 3: Cross-Feature Integration", "tier3_integration_tests", TESTS_DIR, "Hunter -> Cockpit sync, Pipeline -> Metrics recalculation, persistence reload"),
        ("Tier 4: Real-World Scenarios", "tier4_e2e_scenarios", TESTS_DIR, "Contract acquisition lifecycle, B2B sale, and headless DOM smoke tests"),
    ]

    MODULE_SUITES = [
        ("Module: Contract Hunter (M1)", "test_hunter", REPO_ROOT / "contract_hunter", "M1 Contract Hunter unit & adapter suite"),
        ("Module: Enterprise RAG (M2)", "test_rag", REPO_ROOT / "ai_solutions_suite" / "ai_agent_rag", "M2 Enterprise RAG & SafeSQL suite"),
        ("Module: Python Scraper (M2)", "test_scraper", REPO_ROOT / "ai_solutions_suite" / "python_scraper_engine", "M2 Resilient Scraper suite"),
        ("Module: SaaS Dashboard (M2)", "test_dashboard", REPO_ROOT / "ai_solutions_suite" / "saas_dashboard", "M2 Executive SaaS Dashboard suite"),
        ("Module: Cockpit API (M3)", "test_cockpit", REPO_ROOT / "cockpit", "M3 Executive Pipeline Cockpit suite"),
    ]

    def __init__(self, verbosity: int = 1):
        self.verbosity = verbosity

    def run_suite(self, mod_name: str, target_dir: Path) -> Tuple[unittest.TestResult, float]:
        start = time.perf_counter()
        old_path = list(sys.path)
        old_cwd = os.getcwd()

        try:
            os.chdir(str(target_dir))
            # Insert target directory at front of sys.path for local module resolution
            sys.path.insert(0, str(target_dir))

            # Evict colliding module names if already cached
            for m in ["normalizer", "pitch_generator", "cache_manager", "scraper_engine", "rag_agent"]:
                if m in sys.modules:
                    del sys.modules[m]

            loader = unittest.defaultTestLoader
            suite = loader.loadTestsFromName(mod_name)

            runner = unittest.TextTestRunner(
                verbosity=0,
                resultclass=TimedTextTestResult
            )
            result = runner.run(suite)
        finally:
            os.chdir(old_cwd)
            sys.path = old_path

        duration = time.perf_counter() - start
        return result, duration

    def run_all(self) -> int:
        print("\n" + "=" * 80)
        print(" GLOBAL REVENUE ENGINE - MASTER 4-TIER E2E TEST RUNNER")
        print(" Author: Eng. Abdelrahman Rashad | Integrity Mode: Strict Production Verification")
        print("=" * 80 + "\n")

        all_results: List[Dict[str, Any]] = []
        overall_start = time.perf_counter()

        # 1. Execute Core 4-Tier Hierarchy
        print("[*] Executing Core 4-Tier E2E Hierarchy...")
        print("-" * 80)

        total_tests = 0
        total_failures = 0
        total_errors = 0

        for title, mod_name, target_dir, desc in self.TIERS:
            print(f"  > Running {title:<36} ... ", end="", flush=True)
            res, duration = self.run_suite(mod_name, target_dir)
            passed = res.wasSuccessful()
            status = "PASS [OK]" if passed else "FAIL [X]"

            total_tests += res.testsRun
            total_failures += len(res.failures)
            total_errors += len(res.errors)

            print(f"{status}  ({res.testsRun} tests in {duration:.3f}s)")

            all_results.append({
                "tier": title,
                "description": desc,
                "tests": res.testsRun,
                "failures": len(res.failures),
                "errors": len(res.errors),
                "duration": duration,
                "passed": passed,
                "failure_details": res.failures + res.errors
            })

        # 2. Execute Subsystem Module Suites
        print("\n[*] Executing Component & Subsystem Test Suites...")
        print("-" * 80)

        for title, mod_name, target_dir, desc in self.MODULE_SUITES:
            print(f"  > Running {title:<36} ... ", end="", flush=True)
            res, duration = self.run_suite(mod_name, target_dir)
            passed = res.wasSuccessful()
            status = "PASS [OK]" if passed else "FAIL [X]"

            total_tests += res.testsRun
            total_failures += len(res.failures)
            total_errors += len(res.errors)

            print(f"{status}  ({res.testsRun} tests in {duration:.3f}s)")

            all_results.append({
                "tier": title,
                "description": desc,
                "tests": res.testsRun,
                "failures": len(res.failures),
                "errors": len(res.errors),
                "duration": duration,
                "passed": passed,
                "failure_details": res.failures + res.errors
            })

        overall_duration = time.perf_counter() - overall_start

        # 3. Formatted Executive Summary Report
        print("\n" + "=" * 80)
        print(" MASTER TEST EXECUTION SUMMARY")
        print("=" * 80)
        print(f"{'Test Suite / Tier':<38} | {'Count':<6} | {'Failures':<8} | {'Time (s)':<9} | {'Status':<8}")
        print("-" * 80)

        for r in all_results:
            status_str = "PASS" if r["passed"] else "FAIL"
            print(f"{r['tier']:<38} | {r['tests']:<6} | {r['failures'] + r['errors']:<8} | {r['duration']:<9.3f} | {status_str:<8}")

        print("-" * 80)
        print(f"{'OVERALL TOTALS':<38} | {total_tests:<6} | {total_failures + total_errors:<8} | {overall_duration:<9.3f} | {'PASS' if total_failures + total_errors == 0 else 'FAIL'}")
        print("=" * 80)

        # 4. Print any failure tracebacks
        if total_failures + total_errors > 0:
            print("\n[!] DETAILED FAILURE DIAGNOSTICS:")
            for r in all_results:
                if not r["passed"]:
                    print(f"\n--- Failures in {r['tier']} ---")
                    for test_case, tb in r["failure_details"]:
                        print(f"FAILED: {test_case}")
                        print(tb)
            print("\n[!] Exit Code: 1 (Test failures detected)")
            return 1
        else:
            print(f"\n[+] VICTORY: 100% of {total_tests} test cases passed across all 4 tiers and subsystems!")
            print(f"[+] Total execution time: {overall_duration:.3f}s")
            print("[+] Exit Code: 0 (All quality gates satisfied)\n")
            return 0


if __name__ == "__main__":
    runner = MasterTestRunner()
    sys.exit(runner.run_all())
