"""Logging utilities for the restaurant backend Lambda functions."""

import logging
import os
from collections import OrderedDict

import structlog

_log_level_name = os.environ.get("log_level", "INFO").upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)

structlog.configure(
    processors=[
        structlog.processors.EventRenamer("message"),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
        structlog.contextvars.merge_contextvars,
        structlog.processors.JSONRenderer(),
    ],
    context_class=OrderedDict,
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger("debug"),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a structlog bound logger for the given name.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A structlog :class:`BoundLogger` instance.

    """
    return structlog.get_logger(name)
