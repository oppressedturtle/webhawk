"""Minimal structured logging setup.

Kept dependency-free for the foundation phase; emits single-line key=value
records that are easy to grep in development and trivially parseable in prod.
"""

from __future__ import annotations

import logging
import sys


def configure_logging(*, debug: bool = False) -> None:
    """Configure the root logger. Idempotent across repeated calls."""
    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)

    # Replace handlers so re-running (e.g. in tests/reload) doesn't duplicate.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
