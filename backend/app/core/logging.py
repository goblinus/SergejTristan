"""Настройка логирования stdlib logging."""

import logging
import sys

_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def setup_logging(level: int | str = logging.INFO) -> None:
    """Настраивает корневой логгер: вывод в stdout, единый формат."""
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())
        if not isinstance(level, int):
            level = logging.INFO

    # Windows-консоль по умолчанию может быть не в UTF-8; русские сообщения не должны падать.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError, OSError):
        pass

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # httpx/httpcore логируют каждый запрос на INFO; для скриптов это шум.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
