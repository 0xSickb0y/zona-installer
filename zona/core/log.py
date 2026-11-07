import sys
import logging

COLORS = {
    logging.INFO: "\033[32m",      # green
    logging.ERROR: "\033[31m",     # red
    logging.DEBUG: "\033[36m",     # cyan
    logging.WARNING: "\033[33m",   # yellow
}
RESET = "\033[0m"

logger = logging.getLogger("zona")

class ColorFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        if sys.stderr.isatty(): # no colors when output is piped to a file
            return f"{COLORS.get(record.levelno, '')}{message}{RESET}"
        return message


class ProgressAwareHandler(logging.StreamHandler):
    """Clears an active download progress line before writing, so the two never share a line."""
    def emit(self, record):
        from zona.core import progress
        current = progress.active()
        if current is None:
            return super().emit(record)
        with progress.OUTPUT_LOCK:
            current.clear()
            super().emit(record)


def setup_logging(verbose=False):
    handler = ProgressAwareHandler()
    handler.setFormatter(ColorFormatter("%(levelname)-7s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)