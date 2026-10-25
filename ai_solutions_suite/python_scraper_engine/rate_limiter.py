"""
Thread-Safe Monotonic Token Bucket Rate Limiter
================================================
Controls scraping request throughput and enforces domain-specific request budgets.
Author: Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

import time
import threading
from typing import Optional

class TokenBucketRateLimiter:
    """
    Implements a thread-safe token bucket algorithm with monotonic timing.
    - rate: Tokens replenished per second.
    - capacity: Maximum burst size allowed.
    """

    def __init__(self, rate: float = 5.0, capacity: float = 10.0):
        if rate <= 0:
            raise ValueError("Rate must be positive.")
        if capacity < 1:
            raise ValueError("Capacity must be at least 1.0.")

        self.rate = float(rate)
        self.capacity = float(capacity)
        self._tokens = float(capacity)
        self._last_update = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        delta = now - self._last_update
        self._last_update = now
        added = delta * self.rate
        self._tokens = min(self.capacity, self._tokens + added)

    def tokens_available(self) -> float:
        """Returns the current number of available tokens."""
        with self._lock:
            self._refill()
            return self._tokens

    def acquire(self, tokens: float = 1.0, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Attempts to acquire the specified number of tokens.
        If block is True, sleeps until tokens are available or timeout expires.
        """
        if tokens <= 0:
            return True
        if tokens > self.capacity:
            raise ValueError(f"Requested tokens ({tokens}) exceeds total capacity ({self.capacity}).")

        start_time = time.monotonic()

        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

                if not block:
                    return False

                # Calculate required sleep duration
                deficit = tokens - self._tokens
                sleep_duration = deficit / self.rate

            # Check timeout
            if timeout is not None:
                elapsed = time.monotonic() - start_time
                if elapsed + sleep_duration > timeout:
                    return False

            # Sleep outside the lock
            time.sleep(min(sleep_duration, 0.1))

    def reset(self):
        """Restores bucket to maximum capacity."""
        with self._lock:
            self._tokens = self.capacity
            self._last_update = time.monotonic()
