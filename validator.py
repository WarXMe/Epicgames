"""
validator.py — Test proxies concurrently and return only live ones
"""
import threading
import requests

# test against a fast, reliable endpoint
_TEST_URL     = "https://httpbin.org/ip"
_TEST_TIMEOUT = 6
_TEST_THREADS = 200    # high thread count — most will be waiting on dead proxies


def validate(proxies: list[str], progress_cb=None) -> list[str]:
    """
    Test each proxy. Returns list of proxies that successfully connect.

    progress_cb(tested, total, live) — called periodically during validation
    """
    live:    list[str]  = []
    lock     = threading.Lock()
    tested   = [0]
    last_cb  = [0.0]

    import time
    start = time.time()

    def _test(proxy: str):
        ok = False
        try:
            r = requests.get(
                _TEST_URL,
                proxies={"http": proxy, "https": proxy},
                timeout=_TEST_TIMEOUT,
            )
            ok = r.status_code == 200
        except Exception:
            pass

        with lock:
            if ok:
                live.append(proxy)
            tested[0] += 1
            now = time.time()
            if progress_cb and (now - last_cb[0] > 2.0 or tested[0] == len(proxies)):
                last_cb[0] = now
                progress_cb(tested[0], len(proxies), len(live))

    sem     = threading.BoundedSemaphore(_TEST_THREADS)
    threads = []
    for proxy in proxies:
        sem.acquire()
        def task(p=proxy):
            try:
                _test(p)
            finally:
                sem.release()
        t = threading.Thread(target=task, daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return live
