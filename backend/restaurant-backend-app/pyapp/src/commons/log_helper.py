"""Logging utilities for the restaurant backend Lambda functions."""

import logging
import os
from sys import stdout

_name_to_level = {
    "CRITICAL": logging.CRITICAL,
    "FATAL": logging.FATAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

logger = logging.getLogger(__name__)
logger.propagate = False
console_handler = logging.StreamHandler(stream=stdout)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
)
logger.addHandler(console_handler)


log_level = _name_to_level.get(os.environ.get("log_level"))
if not log_level:
    log_level = logging.INFO
logging.captureWarnings(True)


def get_logger(log_name: str, level: int | None = log_level) -> logging.Logger:
    """Return a child logger configured at the given level.

    Args:
        log_name: Dotted name used to identify the child logger.
        level: Logging level; if None the logger inherits its parent's level.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    module_logger = logger.getChild(log_name)
    if level:
        module_logger.setLevel(level)
    return module_logger
