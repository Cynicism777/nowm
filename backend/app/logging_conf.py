import json
import logging
import pathlib
import time
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = pathlib.Path(__file__).resolve().parents[1] / "logs"


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("nowm")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    h = TimedRotatingFileHandler(LOG_DIR / "access.log", when="midnight",
                                 backupCount=30, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(h)
    return logger


def log_event(logger: logging.Logger, **fields) -> None:
    fields.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S"))
    logger.info(json.dumps(fields, ensure_ascii=False))
