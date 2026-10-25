"""
Anti-Detection & Resilient HTTP Transport Layer
================================================
Rotating modern User-Agents, synchronized Client Hints, human delay jitter,
and exponential backoff with full jitter to defeat rate limiting and anti-bot systems.
Author: Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

import random
import time
from typing import Dict, List, Any, Optional, Tuple

class AntiDetectionEngine:
    """Generates browser-consistent HTTP headers and calculates anti-detection timings."""

    # Curated modern desktop User-Agents with corresponding Client Hints
    BROWSER_PROFILES = [
        {
            "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "ch_ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "platform": '"Windows"',
            "mobile": "?0"
        },
        {
            "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "ch_ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "platform": '"macOS"',
            "mobile": "?0"
        },
        {
            "ua": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "ch_ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "platform": '"Linux"',
            "mobile": "?0"
        },
        {
            "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "ch_ua": None,  # Safari does not emit Chromium Sec-CH-UA
            "platform": '"macOS"',
            "mobile": "?0"
        },
        {
            "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "ch_ua": None,  # Firefox uses standard headers
            "platform": '"Windows"',
            "mobile": "?0"
        }
    ]

    def __init__(self, base_delay: float = 1.0, max_delay: float = 30.0):
        self.base_delay = base_delay
        self.max_delay = max_delay

    def get_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        """Returns browser headers with synchronized Client Hints and Fetch Metadata."""
        profile = random.choice(self.BROWSER_PROFILES)
        headers = {
            "User-Agent": profile["ua"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin" if referer else "none",
            "Sec-Fetch-User": "?1",
            "DNT": "1"
        }

        if profile["ch_ua"]:
            headers["Sec-CH-UA"] = profile["ch_ua"]
            headers["Sec-CH-UA-Mobile"] = profile["mobile"]
            headers["Sec-CH-UA-Platform"] = profile["platform"]

        if referer:
            headers["Referer"] = referer

        return headers

    def calculate_human_jitter(self, min_s: float = 0.5, max_s: float = 2.0) -> float:
        """Computes a realistic Gaussian-distributed human interaction delay."""
        mean = (min_s + max_s) / 2.0
        stddev = (max_s - min_s) / 4.0
        delay = random.gauss(mean, stddev)
        return max(min_s, min(max_s, round(delay, 3)))

    def calculate_exponential_backoff(self, attempt: int, base: Optional[float] = None, max_b: Optional[float] = None) -> float:
        """
        Computes Exponential Backoff with Full Jitter:
        T = random.uniform(0, min(T_max, T_base * 2^attempt))
        Prevents thundering herd problems during 429/503 rate-limit recovery.
        """
        b = base or self.base_delay
        cap = max_b or self.max_delay
        upper_bound = min(cap, b * (2 ** attempt))
        return round(random.uniform(0.1, upper_bound), 3)

    def sleep_jitter(self, min_s: float = 0.5, max_s: float = 2.0):
        """Simulates human interaction delay via time.sleep."""
        delay = self.calculate_human_jitter(min_s, max_s)
        time.sleep(delay)
