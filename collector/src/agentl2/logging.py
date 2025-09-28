from __future__ import annotations

import sys
from typing import Any, Optional

from loguru import logger


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    logger.remove()
    logger.configure(
        handlers=[
            {
                "sink": sys.stdout,
                "level": level.upper(),
                "serialize": fmt.lower() == "json",
                "backtrace": True,
                "diagnose": False,
            }
        ]
    )


def get_logger(name: Optional[str] = None) -> Any:
    if name:
        return logger.bind(module=name)
    return logger


def bind_context(**context: Any) -> None:
    logger.bind(**context)
