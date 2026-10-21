"""
IBKR historical-data pacing (BI-029). TWS rejects historical requests that break its pacing rules (error 162
"pacing violation"); waiting BEFORE sending avoids them instead of retrying after:

  - at most 60 requests in any 10 minutes,
  - no identical request (same contract, end, duration, bar size, data type) within 15 seconds,
  - at most 6 requests for the same contract and data type within 2 seconds.

One pacer per process (``shared_pacer``): the limits apply to the whole TWS session, not to one broker object.
The clock and sleep are injectable for tests.
"""

import threading
import time
from collections import deque
from typing import Callable, Deque, Dict, Hashable, Tuple

WINDOW_SECONDS, WINDOW_LIMIT = 600.0, 60
IDENTICAL_SECONDS = 15.0
BURST_SECONDS, BURST_LIMIT = 2.0, 6


class HistoryPacer:

    def __init__(self, clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep):
        self.clock, self.sleep = clock, sleep
        self._lock = threading.Lock()
        self._all: Deque[float] = deque()
        self._identical: Dict[Hashable, float] = {}
        self._burst: Dict[Hashable, Deque[float]] = {}

    def wait_time(self, request_key: Hashable, contract_key: Hashable, now: float) -> float:
        """Seconds to wait before a request may be sent at `now` (0 = send now)."""
        waits = [0.0]
        while self._all and now - self._all[0] >= WINDOW_SECONDS:
            self._all.popleft()
        if len(self._all) >= WINDOW_LIMIT:
            waits.append(self._all[len(self._all) - WINDOW_LIMIT] + WINDOW_SECONDS - now)
        last = self._identical.get(request_key)
        if last is not None:
            waits.append(last + IDENTICAL_SECONDS - now)
        burst = self._burst.get(contract_key, deque())
        while burst and now - burst[0] >= BURST_SECONDS:
            burst.popleft()
        if len(burst) >= BURST_LIMIT:
            waits.append(burst[len(burst) - BURST_LIMIT] + BURST_SECONDS - now)
        return max(waits)

    def acquire(self, request_key: Hashable, contract_key: Hashable) -> float:
        """Wait as long as the rules require, then record the request. Returns the seconds waited."""
        waited = 0.0
        with self._lock:
            now = self.clock()
            while True:
                wait = self.wait_time(request_key, contract_key, now)
                if wait <= 0:
                    break
                self.sleep(wait)
                waited += wait
                now = max(self.clock(), now + wait)       # never re-check at a time earlier than slept to
            self._all.append(now)
            self._identical[request_key] = now
            self._burst.setdefault(contract_key, deque()).append(now)
        return waited


shared_pacer = HistoryPacer()
