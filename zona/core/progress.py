# Download progress: one status line on stderr, shared by every concurrent download.
#
#   with progress.tracker() as p:        # reuses the active tracker if one is already running
#       p.start(name, total_bytes)       # total may be None (unknown yet)
#       p.advance(name, nbytes)          # or p.set(name, done, total) for absolute values
#       p.finish(name)
#
# The line is redrawn by a background thread; log records emitted meanwhile clear it first
# (see zona.core.log), so messages never end up glued to the progress line.

import collections
import contextlib
import shutil
import sys
import threading
import time

_active = None
_active_lock = threading.Lock()
OUTPUT_LOCK = threading.RLock()  # serialises progress redraws with log output


def active():
    """The Progress currently drawing, or None."""
    return _active


def human_bytes(n):
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unit == "GiB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GiB"


def human_time(seconds):
    seconds = int(seconds)
    if seconds >= 3600:
        return f"{seconds // 3600}h{seconds % 3600 // 60:02d}m"
    if seconds >= 60:
        return f"{seconds // 60}m{seconds % 60:02d}s"
    return f"{seconds}s"


class Progress:
    def __init__(self, interval=0.5):
        self._lock = threading.Lock()
        self._tasks = {}  # name -> {"done": int, "total": int|None, "finished": bool}
        self._samples = collections.deque(maxlen=20)  # (time, bytes_done) for the speed estimate
        self._interval = interval
        self._stop = threading.Event()
        self._thread = None
        self._tty = sys.stderr.isatty()
        self._drawn = False

    # -- task updates (thread-safe) --
    def start(self, name, total=None):
        with self._lock:
            self._tasks[name] = {"done": 0, "total": total, "finished": False}

    def advance(self, name, nbytes):
        with self._lock:
            self._tasks[name]["done"] += nbytes

    def set(self, name, done, total=None):
        with self._lock:
            task = self._tasks[name]
            task["done"] = done
            if total:
                task["total"] = total

    def finish(self, name):
        with self._lock:
            task = self._tasks.get(name)
            if task:
                task["finished"] = True
                if task["total"]:
                    task["done"] = task["total"]

    # -- drawing --
    def _line(self):
        with self._lock:
            tasks = dict(self._tasks)
        done = sum(t["done"] for t in tasks.values())
        known_total = all(t["total"] for t in tasks.values())
        total = sum(t["total"] or 0 for t in tasks.values())
        finished = sum(t["finished"] for t in tasks.values())

        now = time.monotonic()
        self._samples.append((now, done))
        t0, b0 = self._samples[0]
        speed = (done - b0) / (now - t0) if now > t0 else 0

        parts = [f"[{finished}/{len(tasks)}]"]
        if known_total and total:
            parts.append(f"{human_bytes(done)} / {human_bytes(total)} ({done * 100 // total}%)")
        else:
            parts.append(f"{human_bytes(done)} / ?")
        parts.append(f"{human_bytes(speed)}/s")
        if known_total and total and speed > 0:
            parts.append(f"ETA {human_time((total - done) / speed)}")
        running = [name for name, t in tasks.items() if not t["finished"]]
        if running:
            parts.append("· " + ", ".join(running))

        width = shutil.get_terminal_size((100, 20)).columns - 1
        line = "  ".join(parts)
        return line if len(line) <= width else line[: width - 1] + "…"

    def clear(self):
        """Erase the progress line so something else can be printed."""
        with OUTPUT_LOCK:
            if self._tty and self._drawn:
                sys.stderr.write("\r\033[K")
                sys.stderr.flush()
                self._drawn = False

    def redraw(self):
        if self._tty:
            line = self._line()
            with OUTPUT_LOCK:
                sys.stderr.write("\r\033[K" + line)
                sys.stderr.flush()
                self._drawn = True

    def _run(self):
        while not self._stop.wait(self._interval):
            self.redraw()

    # -- lifecycle --
    def __enter__(self):
        global _active
        with _active_lock:
            _active = self
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        global _active
        self._stop.set()
        self._thread.join()
        with _active_lock:
            _active = None
        if self._tty:
            self.redraw()  # final state
            sys.stderr.write("\n")
            sys.stderr.flush()
        return False


@contextlib.contextmanager
def tracker():
    """Yield the running Progress, or start a new one for the duration of the block."""
    current = active()
    if current is not None:
        yield current
        return
    with Progress() as p:
        yield p
