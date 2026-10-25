"""
Adversarial & Empirical Verification Script for Gate 2
Target: contract_hunter/normalizer.py
Author: teamwork_preview_challenger_gate2_1
"""

import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contract_hunter.normalizer import parse_salary, is_high_ticket_opportunity, CURRENCY_RATES


def run_gate2_tests():
    print("=" * 70)
    print("GATE 2 EMPIRICAL ADVERSARIAL VERIFICATION")
    print("=" * 70)

    all_passed = True
    test_count = 0
    fail_count = 0

    def assert_test(cond, name, details=""):
        nonlocal all_passed, test_count, fail_count
        test_count += 1
        if cond:
            print(f"  [PASS] #{test_count:02d}: {name}")
        else:
            all_passed = False
            fail_count += 1
            print(f"  [FAIL] #{test_count:02d}: {name} -> {details}")

    # ==========================================
    # Group 1: Core Mission Requirements
    # ==========================================
    print("\n--- Group 1: Core Mission Requirements ---")

    # 1.1 $140k exactly (11666.67, 11666.67, 'annual', '$140k') and is_high_ticket True
    res = parse_salary("$140k")
    assert_test(
        res == (11666.67, 11666.67, 'annual', '$140k'),
        "parse_salary('$140k') exact match == (11666.67, 11666.67, 'annual', '$140k')",
        f"Expected (11666.67, 11666.67, 'annual', '$140k'), got {res}"
    )
    ht = is_high_ticket_opportunity(res[0], res[1], title="Fullstack Developer")
    assert_test(
        ht is True,
        "is_high_ticket_opportunity for $140k is True (11666.67 >= 3500)",
        f"Expected True, got {ht}"
    )

    # 1.2 Multi-currency & variants matrix
    test_matrix = [
        ("$100k", (8333.33, 8333.33, "annual", "$100k")),
        ("$120k/yr", (10000.0, 10000.0, "annual", "$120k/yr")),
        ("$150k/yr", (12500.0, 12500.0, "annual", "$150k/yr")),
        ("€90k", (8100.0, 8100.0, "annual", "€90k")),
        ("£80k", (8533.33, 8533.33, "annual", "£80k")),
        ("CAD 120k", (7400.0, 7400.0, "annual", "120k")),
    ]
    for raw, expected in test_matrix:
        res = parse_salary(raw)
        passed = (
            abs(res[0] - expected[0]) < 0.02 and
            abs(res[1] - expected[1]) < 0.02 and
            res[2] == expected[2] and
            res[3] == expected[3]
        )
        assert_test(
            passed,
            f"parse_salary('{raw}') normalized accurately to {expected[0]:.2f}/mo",
            f"Expected {expected}, got {res}"
        )
        ht_val = is_high_ticket_opportunity(res[0], res[1])
        assert_test(
            ht_val is True,
            f"is_high_ticket_opportunity for '{raw}' is True ({res[0]} >= 3500)",
            f"Expected True, got {ht_val}"
        )

    # ==========================================
    # Group 2: Naked ranges and numbers
    # ==========================================
    print("\n--- Group 2: Naked Ranges & Non-Salary Strings Rejection ---")
    naked_cases = [
        "5 years experience",
        "100 - 200 items",
        "5-7 years of experience in React and Node.js",
        "Looking for 3 - 5 developers",
        "Team of 10 to 20 engineers",
        "100 - 200",
        "$500 - $600",
        "equity: 0.1% - 0.5%",
        "We raised $5M in Series A",
        "Zero compensation mentioned",
        "",
        "   ",
    ]
    for raw in naked_cases:
        res = parse_salary(raw)
        # Should NOT be classified as annual, should be unspecified
        assert_test(
            res[2] == "unspecified" and res[0] is None and res[1] is None,
            f"Naked string '{raw}' parsed as unspecified",
            f"Got {res}"
        )

    # ==========================================
    # Group 3: Adversarial Case Variations & Ranges
    # ==========================================
    print("\n--- Group 3: Adversarial Variations & Dual-Pattern Range Preservation ---")
    variations = [
        # Upper case K
        ("$140K", (11666.67, 11666.67, "annual", "$140K")),
        # Without currency sign but with k
        ("140k / year", (11666.67, 11666.67, "annual", "140k / year")),
        # Space between symbol and digits
        ("$ 140k", (11666.67, 11666.67, "annual", "$ 140k")),
        # Space between digits and k
        ("$140 k", (11666.67, 11666.67, "annual", "$140 k")),
        # Decimal k
        ("$125.5k", (10458.33, 10458.33, "annual", "$125.5k")),
        # Annual ranges with k
        ("$140k - $180k", (11666.67, 15000.0, "annual", "$140k - $180k")),
        ("$140 - $180k", (11666.67, 15000.0, "annual", "$140 - $180k")),
        ("$140k to $180k", (11666.67, 15000.0, "annual", "$140k to $180k")),
        ("140k-180k", (11666.67, 15000.0, "annual", "140k-180k")),
        ("€70k-€90k", (6300.0, 8100.0, "annual", "€70k-€90k")),
        # Full annual numbers with commas
        ("$120,000 - $160,000 / year", (10000.0, 13333.33, "annual", "$120,000 - $160,000 / year")),
        ("$150,000 / year", (12500.0, 12500.0, "annual", "$150,000 / year")),
        # Hourly precedence over annual mentions
        ("$50/hr ($100k eq)", (8000.0, 8000.0, "hourly", "$50/hr")),
        # Monthly precedence over annual mentions
        ("$4000/mo ($100k eq)", (4000.0, 4000.0, "monthly", "$4000/mo")),
    ]
    for raw, expected in variations:
        res = parse_salary(raw)
        passed = (
            abs(res[0] - expected[0]) < 0.05 and
            abs(res[1] - expected[1]) < 0.05 and
            res[2] == expected[2]
        )
        assert_test(
            passed,
            f"Variation '{raw}' -> {res[0]}-{res[1]}/mo ({res[2]})",
            f"Expected {expected}, got {res}"
        )

    # ==========================================
    # Group 4: Edge Cases: 401(k), ReDoS, Contextual Noise
    # ==========================================
    print("\n--- Group 4: Edge Cases (401k, ReDoS, Contextual Noise) ---")

    # 4.1 "401(k)" retirement benefit should NOT be parsed as a $401k salary!
    res_401 = parse_salary("We offer health insurance, 401(k) matching, and remote flexibility.")
    assert_test(
        res_401[2] == "unspecified",
        "'401(k) matching' is NOT parsed as $401k salary",
        f"Got {res_401}"
    )

    # 4.2 Noise surrounded salary
    noise_text = "🚀 Senior Fullstack Engineer! 💰 Offering $140k - $160k with equity 🎉"
    res_noise = parse_salary(noise_text)
    assert_test(
        res_noise[2] == "annual" and abs(res_noise[0] - 11666.67) < 0.05,
        "Emoji and text surrounded range parsed correctly",
        f"Got {res_noise}"
    )

    # 4.3 Long text ReDoS safety
    long_string = "looking for a developer " * 1000 + "$140k" + " apply now " * 1000
    import time
    t0 = time.perf_counter()
    res_long = parse_salary(long_string)
    dur = time.perf_counter() - t0
    assert_test(
        dur < 0.1 and res_long[2] == "annual",
        f"ReDoS resistance: 44,000 char string parsed in {dur:.4f}s (<0.1s)",
        f"Duration {dur:.4f}s, got {res_long}"
    )

    # Summary
    print("\n" + "=" * 70)
    print(f"VERIFICATION SUMMARY: {test_count - fail_count}/{test_count} tests PASSED")
    if all_passed:
        print("[+] ALL ADVERSARIAL ASSERTIONS PASSED WITH ZERO FAILURES!")
    else:
        print(f"[-] {fail_count} ADVERSARIAL ASSERTIONS FAILED!")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    success = run_gate2_tests()
    sys.exit(0 if success else 1)
