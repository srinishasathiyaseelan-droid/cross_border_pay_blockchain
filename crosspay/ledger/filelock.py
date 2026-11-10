"""Minimal cross-process file lock (fcntl on POSIX, msvcrt on Windows) for the derived ledger view (M3)."""
import os
import time


class FileLock:
    def __init__(self, path: str, timeout: float = 10.0):
        self.path = path
        self.timeout = timeout
        self._fh = None

    def __enter__(self):
        self._fh = open(self.path, "a+b")
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt

                    self._fh.seek(0)
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() > deadline:
                    self._fh.close()
                    raise TimeoutError(f"Timed out waiting for lock {self.path}")
                time.sleep(0.02)

    def __exit__(self, *exc):
        try:
            if os.name == "nt":
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
        return False
