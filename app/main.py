import logging

from fastapi import FastAPI

from app.config import OCR_LANG, OCR_MODEL_PROFILE, OCR_USE_MKLDNN, RENDER_DPI
from app.logging_config import configure_logging
from app.routes import documents, health

LOG_FILE_PATH = configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="OCR API")
app.include_router(health.router)
app.include_router(documents.router)

# Trace la configuration réellement appliquée : c'est la première chose à vérifier quand un
# résultat surprend (langue, résolution de rendu, oneDNN désactivé sur CPU Windows).
# Le chemin du fichier est affiché pour qu'on sache où lire la trace sans dépendre de la console
# de celui qui a démarré le serveur.
logger.info(
    "OCR API demarree : lang=%s profil=%s dpi=%d mkldnn=%s level=%s",
    OCR_LANG,
    OCR_MODEL_PROFILE,
    RENDER_DPI,
    OCR_USE_MKLDNN,
    logging.getLevelName(logger.getEffectiveLevel()),
)
logger.info("Journal fichier : %s", LOG_FILE_PATH)
