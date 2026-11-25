import logging
import re
import sys

_TOKEN_RE = re.compile(r"\d{6,}:[A-Za-z0-9_-]{30,}")


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001
            return True
        record.msg = _TOKEN_RE.sub("[REDACTED]", msg)
        record.args = ()
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactFilter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    logging.getLogger("aiogram").setLevel(logging.INFO)
