"""Journalisation de l'API : un format unique, sur la console ET dans un fichier.

Le fichier n'est pas un confort : sans lui, les journaux n'existent que dans la console du
processus qui a lance uvicorn. Impossible de relire ce qui s'est passe, ni de suivre une requete
depuis un autre terminal, ni de savoir ce qui a echoue quand le serveur a ete lance par un tiers.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "logs/ocr-api.log")
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5

# "uvicorn.error" n'a pas de handler et propage vers "uvicorn" : lui en donner un ecrirait
# chaque ligne deux fois. On n'equipe donc que les loggers qui arrete la propagation.
_FILE_HANDLER_LOGGERS = (None, "uvicorn", "uvicorn.access")


def configure_logging() -> Path:
    """Aligne le niveau et le format de tous les journaux, et renvoie le chemin du fichier."""
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    log_path = Path(LOG_FILE).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    for name in _FILE_HANDLER_LOGGERS:
        _install_handlers(logging.getLogger(name), formatter, log_path)

    logging.getLogger().setLevel(LOG_LEVEL)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(LOG_LEVEL)

    return log_path


def _install_handlers(
    logger: logging.Logger, formatter: logging.Formatter, log_path: Path
) -> None:
    """Ajoute console (si absente) et fichier au logger, sans doubler une installation."""
    if any(getattr(handler, "installed_by_ocr_api", False) for handler in logger.handlers):
        return

    for handler in logger.handlers:
        handler.setFormatter(formatter)

    if not logger.handlers:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.installed_by_ocr_api = True
        logger.addHandler(console)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.installed_by_ocr_api = True
    logger.addHandler(file_handler)
