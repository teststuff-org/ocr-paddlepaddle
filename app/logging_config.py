"""Journalisation de l'API : un format unique pour l'application et pour uvicorn.

Messages en ASCII volontairement : la console Windows peut etre en cp437, ou un accent
ferait echouer l'ecriture du journal au pire moment (pendant une erreur).
"""
import logging
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


def configure_logging() -> None:
    """Aligne le niveau et le format de tous les journaux, uvicorn compris."""
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, force=True)

    for name in _UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        for handler in uvicorn_logger.handlers:
            handler.setFormatter(formatter)
        uvicorn_logger.setLevel(LOG_LEVEL)
