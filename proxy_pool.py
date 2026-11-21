"""
proxy_pool.py — Thread-safe round-robin proxy pool
"""
import threading


class ProxyPool:
    def __init__(self):
        self._proxies: list[str] = []
        self._idx  = 0
        self._lock = threading.Lock()

    def load(self, lines: list[str]) -> int:
        """
        Load proxies from a list of raw strings.
        Accepts:
            ip:port
            ip:port:user:pass
            http://ip:port
            http://user:pass@ip:port
        Returns count loaded.
        """
        parsed = []
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # auto-add scheme if missing
            if not line.startswith("http"):
                # ip:port:user:pass → http://user:pass@ip:port
                parts = line.split(":")
                if len(parts) == 4:
                    ip, port, user, pw = parts
                    line = f"http://{user}:{pw}@{ip}:{port}"
                else:
                    line = f"http://{line}"
            parsed.append(line)

        with self._lock:
            self._proxies = parsed
            self._idx     = 0
        return len(parsed)

    def next(self) -> str | None:
        """Get next proxy in round-robin order. Returns None if pool is empty."""
        with self._lock:
            if not self._proxies:
                return None
            proxy      = self._proxies[self._idx % len(self._proxies)]
            self._idx += 1
            return proxy

    def clear(self):
        with self._lock:
            self._proxies = []
            self._idx     = 0

    @property
    def count(self) -> int:
        return len(self._proxies)


# global singleton — imported by checker + bot
pool = ProxyPool()
