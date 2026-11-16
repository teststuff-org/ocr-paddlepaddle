# OCR API

API FastAPI : upload d'un PDF, extraction du texte (couche texte native, sinon OCR PaddleOCR), export en JSON ou Word.

## Lancer
- Linux / macOS : `./run.sh`
- Windows : `.\run.ps1`

## Arrêter
```powershell
.\run.ps1 stop      # Windows
./run.sh stop       # Linux / macOS
```
`stop` remonte d'abord jusqu'au lanceur (`uv run uvicorn`, reloader) puis arrête son arbre
complet, du plus profond au plus haut, et vérifie que le port est libre. Tuer un seul maillon
laisse un worker orphelin qui garde le port et continue de servir l'ancien code. Sous Linux/macOS
l'arrêt passe par `SIGTERM` (arrêt propre, requête en cours terminée), puis `SIGKILL` après 10 s ;
sous Windows il n'existe pas d'équivalent pour une application console, l'arrêt est immédiat.

Prérequis : Python 3.11+. Les scripts affichent l'URL de l'API (`http://localhost:8000`) et de Swagger (`/docs`).

Les scripts utilisent [uv](https://docs.astral.sh/uv/) (standard moderne) et se rabattent sur `venv` + `pip` si uv est absent.

Documentation interactive : http://localhost:8000/docs

## Accès dans le navigateur (Windows)

Les scripts écoutent sur `127.0.0.1` : l'API n'est joignable que depuis cette machine, et
`http://localhost:8000/docs` répond sans dépendre de la résolution de `localhost`.

| Besoin | Commande |
|---|---|
| Local (défaut) | `.\run.ps1` / `./run.sh` |
| Exposer sur le réseau local | `$env:HOST = "0.0.0.0"` puis `.\run.ps1` |
| Port déjà pris | `$env:PORT = 8001` puis `.\run.ps1` |

Le script refuse de démarrer si le port est déjà occupé, en indiquant le PID à arrêter : deux
serveurs sur le même port, c'est un ancien processus qui répond à la place du nouveau, avec
l'ancien code — cause classique d'une page `/docs` qui semble cassée. `.\run.ps1 stop` règle le cas.

## Rechargement à chaud

Désactivé par défaut : sous Windows, le reloader d'uvicorn ne reçoit pas proprement l'ordre
d'arrêt quand la console n'est pas interactive. Il se fige après `Reloading...` et laisse un
worker orphelin qui garde le port et sert l'ancien code.

```powershell
.\run.ps1 start -Reload     # ou : $env:RELOAD = "true"
./run.sh start --reload     # ou : RELOAD=true ./run.sh
```

Sans rechargement, relancer `start` après une modification du code.

Si `http://localhost:8000/docs` ne répond pas alors que `http://127.0.0.1:8000/docs` répond,
le problème est la résolution de `localhost` (IPv6 `::1` non écouté), pas l'API : utiliser
`127.0.0.1`.

## Utiliser
```bash
curl -F "file=@mon.pdf" "http://localhost:8000/documents/ocr?format=json"
curl -F "file=@mon.pdf" "http://localhost:8000/documents/ocr?format=docx" -o resultat.docx
```
Paramètres : `format` (`json` | `docx`), `force_ocr` (`true` pour forcer l'OCR même si le PDF contient du texte).
Langue OCR : variable d'environnement `OCR_LANG` (défaut `fr`).
oneDNN : `OCR_USE_MKLDNN=true` pour l'activer ; laissé désactivé car il fait planter PaddlePaddle
sur CPU Windows (`ConvertPirAttribute2RuntimeAttribute not support`).
Jeu de modèles : `OCR_MODEL_PROFILE=mobile` pour les modèles mobiles, ~7x plus rapides sur CPU
(page A4 à 200 dpi : 50 s en `medium`, 7 s en `mobile`), moins sûrs sur les petits caractères.
Journalisation : `LOG_LEVEL` (`INFO` par défaut, `DEBUG` pour le détail). Une requête se suit
page par page, avec le début et la fin de chaque page :

```
INFO app.routes.documents: Requete OCR : fichier=scan.pdf taille=11602687 octets format=json force_ocr=True
INFO app.readers.pdf_reader: PDF ouvert : pages=3 taille=11602687 octets force_ocr=False
INFO app.readers.pdf_reader: Page 1/3 : debut (force_ocr=False)
INFO app.readers.pdf_reader: Page 1/3 : fin source=text_layer lignes=1 duree=0.0s
INFO app.readers.pdf_reader: Page 2/3 : debut (force_ocr=False)
INFO app.readers.pdf_reader: Page 2/3 : aucune couche texte, recours a l'OCR
INFO app.readers.pdf_reader: Page 2/3 : OCR en cours (image 1653x2339 px, 200 dpi)
INFO app.readers.ocr_engine: Inference OCR : image=1653x2339 lignes=16 duree=35.6s
INFO app.readers.pdf_reader: Page 2/3 : fin source=ocr lignes=16 duree=35.6s
INFO app.readers.pdf_reader: Page 3/3 : debut (force_ocr=False)
INFO app.readers.pdf_reader: Page 3/3 : fin source=text_layer lignes=1 duree=0.0s
INFO app.readers.pdf_reader: Lecture terminee : pages=3 ocr=1 vides=0 lignes=18 duree=35.57s
INFO app.routes.documents: Requete OCR terminee : fichier=mixed.pdf pages=3 format=json taille_sortie=917 octets duree=35.57s
```

Une page scannée prend des dizaines de secondes : les lignes `Page i/n : debut` et
`Page i/n : OCR en cours` sont là pour distinguer un serveur qui travaille d'un serveur bloqué.

### Lire les journaux

Les journaux vont sur la console **et** dans `logs/ocr-api.log` (rotation à 10 Mo, 5 fichiers).
Le fichier est le seul endroit fiable : la console n'existe que pour celui qui a lancé le serveur.

```powershell
Get-Content .\logs\ocr-api.log -Wait -Tail 30    # Windows : suivi en direct
```
```bash
tail -f logs/ocr-api.log                          # Linux / macOS
```

Au démarrage, la ligne `Journal fichier : <chemin absolu>` donne l'emplacement exact, même si le
serveur a été lancé depuis un autre dossier. `LOG_FILE` change ce chemin, `LOG_LEVEL=DEBUG` passe
au détail.

`GET /health` répond `{"status": "ok"}` sans lancer l'OCR ; `GET /` redirige vers `/docs`.
