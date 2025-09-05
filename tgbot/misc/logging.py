import logging
import sys
from loguru import logger


class InterceptHandler(logging.Handler):
    LEVELS_MAP = {
        logging.CRITICAL: "CRITICAL",
        logging.ERROR: "ERROR",
        logging.WARNING: "WARNING",
        logging.INFO: "INFO",
        logging.DEBUG: "DEBUG",
    }

    def _get_level(self, record):
        return self.LEVELS_MAP.get(record.levelno, record.levelno)

    def emit(self, record):
        logger.opt(depth=6, exception=record.exc_info).log(self._get_level(record), record.getMessage())


def configure_logger(capture_exceptions: bool = False) -> None:
    logger.remove()
    logger.add(
        "logs/log_{time:YYYY-MM-DD}.log",
        rotation="12:00",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}",
        level="INFO",
        encoding="utf-8",
        compression="zip",
    )
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD at HH:mm:ss}</green> | <level>{level}</level> | {file}:{line} | {message}",
        level="INFO",
    )
    if capture_exceptions:
        logger.add(
            "logs/error_log_{time:YYYY-MM-DD}.log",
            rotation="12:00",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}",
            level="ERROR",
            encoding="utf-8",
            compression="zip",
        )

    # Принудительно перехватываем стандартный logging после Django
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(InterceptHandler())
    root.setLevel(logging.INFO)

    # Отключаем шумные логгеры при необходимости
    logger.disable("sqlalchemy")
    logger.disable("aioschedule")
