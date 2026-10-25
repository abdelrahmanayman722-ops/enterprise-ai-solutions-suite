"""
Property-Based Fuzz Generator & Verification Oracle for Gate 2
Target: contract_hunter/normalizer.py
Author: teamwork_preview_challenger_gate2_1
"""

import sys
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contract_hunter.normalizer import parse_salary, is_high_ticket_opportunity, CURRENCY_RATES


def run_fuzz_oracle():
    print("=" * 70)
    print("PROPERTY-BASED FUZZ GENERATOR & ORACLE")
    print("=" * 70)

    random.seed(42)
    currencies = [
        ("$", 1.0, True),      # (symbol, rate, is_symbol)
        ("€", 1.08, True),
        ("£", 1.28, True),
        ("CAD ", 0.74, False),
        ("AUD ", 0.65, False),
        ("", 1.0, False),      # naked k with /year or annual context
    ]
    k_suffixes = ["k", "K", " k", " K"]
    year_suffixes = ["", "/yr", " / yr", "/year", " / year", " annually", " per year"]
    separators = [" - ", "-", " to "]

    # Test 1: Single Figure k Salary Generator (1000 iterations)
    print("\n[+] Generating 1,000 single-figure k salaries across currencies & formats...")
    single_failures = 0
    for i in range(1000):
        val = random.randint(30, 450)
        curr_sym, rate, is_sym = random.choice(currencies)
        k_suf = random.choice(k_suffixes)
        yr_suf = random.choice(year_suffixes)
        # If curr_sym is empty, make sure yr_suf is non-empty so it has context
        if not curr_sym and not yr_suf:
            yr_suf = "/yr"

        # Construct input
        raw = f"{curr_sym}{val}{k_suf}{yr_suf}".strip()
        expected_monthly = round((val * 1000.0 * rate) / 12.0, 2)

        min_usd, max_usd, period, matched = parse_salary(raw)
        if period != "annual" or abs(min_usd - expected_monthly) > 0.05 or abs(max_usd - expected_monthly) > 0.05:
            single_failures += 1
            if single_failures <= 5:
                print(f"  [-] Single-figure mismatch: raw='{raw}', expected={expected_monthly}, got=({min_usd}, {max_usd}, '{period}')")

        # Invariant: if expected_monthly >= 3500.0, is_high_ticket must be True
        is_ht = is_high_ticket_opportunity(min_usd, max_usd, title="Developer")
        if (expected_monthly >= 3500.0) != is_ht:
            single_failures += 1
            if single_failures <= 5:
                print(f"  [-] High ticket mismatch for {raw}: monthly={expected_monthly}, is_ht={is_ht}")

    print(f"    Single-figure generator result: {1000 - single_failures}/1000 passed.")

    # Test 2: Dual Figure k Salary Range Generator (1000 iterations)
    print("\n[+] Generating 1,000 dual-figure k salary ranges across currencies & formats...")
    range_failures = 0
    for i in range(1000):
        low_val = random.randint(30, 200)
        high_val = low_val + random.randint(10, 100)
        curr_sym, rate, is_sym = random.choice(currencies)
        k_suf1 = random.choice(["k", "K", ""])  # shorthand allowed e.g. 140 - 180k
        k_suf2 = random.choice(["k", "K"])     # upper bound must have k
        sep = random.choice(separators)
        yr_suf = random.choice(year_suffixes)

        if is_sym:
            # Symbol can appear on both bounds or just the first
            sym2 = curr_sym if random.choice([True, False]) else ""
            raw = f"{curr_sym}{low_val}{k_suf1}{sep}{sym2}{high_val}{k_suf2}{yr_suf}".strip()
        else:
            # Currency code prefixes the whole range, e.g. CAD 100k - 150k
            raw = f"{curr_sym}{low_val}{k_suf1}{sep}{high_val}{k_suf2}{yr_suf}".strip()

        exp_low = round((low_val * 1000.0 * rate) / 12.0, 2)
        exp_high = round((high_val * 1000.0 * rate) / 12.0, 2)

        min_usd, max_usd, period, matched = parse_salary(raw)
        if period != "annual" or abs(min_usd - exp_low) > 0.05 or abs(max_usd - exp_high) > 0.05:
            range_failures += 1
            if range_failures <= 5:
                print(f"  [-] Range mismatch: raw='{raw}', exp=({exp_low}, {exp_high}), got=({min_usd}, {max_usd}, '{period}')")

    print(f"    Range generator result: {1000 - range_failures}/1000 passed.")

    # Test 3: Non-Salary / Naked Strings Generator (500 iterations)
    print("\n[+] Generating 500 non-salary / naked numeric strings...")
    naked_failures = 0
    templates = [
        "{0} years of experience with {1}",
        "{0} - {1} years required",
        "{0} to {1} team members",
        "Handling {0} - {1} requests per second",
        "Scale to {0} servers across AWS",
        "Sprint length: {0} to {1} weeks",
        "Over {0} happy enterprise clients",
    ]
    techs = ["React", "TypeScript", "Python", "Docker", "Kubernetes", "PostgreSQL"]

    for i in range(500):
        n1 = random.randint(1, 20)
        n2 = n1 + random.randint(1, 10)
        t = random.choice(templates).format(n1, n2 if "{1}" in templates else random.choice(techs))
        if "{1}" in t:
            t = t.format(n1, random.choice(techs))

        min_usd, max_usd, period, matched = parse_salary(t)
        if period != "unspecified" or min_usd is not None or max_usd is not None:
            naked_failures += 1
            if naked_failures <= 5:
                print(f"  [-] False positive on naked text: raw='{t}', got=({min_usd}, {max_usd}, '{period}')")

    print(f"    Naked generator result: {500 - naked_failures}/500 passed.")

    # Summary
    total_fuzz = 2500
    total_failed = single_failures + range_failures + naked_failures
    print("\n" + "=" * 70)
    print(f"FUZZ ORACLE SUMMARY: {total_fuzz - total_failed}/{total_fuzz} tests PASSED")
    if total_failed == 0:
        print("[+] 100% EMPIRICAL FUZZ & PROPERTY-BASED TESTS PASSED!")
    else:
        print(f"[-] {total_failed} FUZZ PROPERTY TESTS FAILED!")
    print("=" * 70)

    return total_failed == 0


if __name__ == "__main__":
    success = run_fuzz_oracle()
    sys.exit(0 if success else 1)
