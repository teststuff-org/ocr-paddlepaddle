import os

OCR_LANG = os.getenv("OCR_LANG", "fr")   # fr, en, ch, japan, korean...
RENDER_DPI = int(os.getenv("RENDER_DPI", "200"))  # résolution de rendu des pages avant OCR

# oneDNN (mkldnn) fait planter PaddlePaddle sur CPU Windows : "ConvertPirAttribute2RuntimeAttribute
# not support [pir::ArrayAttribute<pir::DoubleAttribute>]". Désactivé par défaut ; réactivable
# (OCR_USE_MKLDNN=true) sur une plateforme où l'accélération oneDNN fonctionne.
OCR_USE_MKLDNN = os.getenv("OCR_USE_MKLDNN", "false").lower() == "true"

# Jeu de modèles : "medium" (défaut PaddleOCR, précis) ou "mobile" (environ 7x plus rapide sur
# CPU sans oneDNN, moins sûr sur les petits caractères et l'écriture manuscrite).
OCR_MODEL_PROFILE = os.getenv("OCR_MODEL_PROFILE", "medium").lower()
