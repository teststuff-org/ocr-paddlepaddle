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
`stop` arrête l'arbre de processus complet qui écoute sur le port (worker, reloader, uvicorn), du
plus profond au plus haut, puis vérifie que le port est libre. Tuer un seul maillon laisse un
worker orphelin qui garde le port et continue de servir l'ancien code. Sous Linux/macOS l'arrêt
passe par `SIGTERM` (arrêt propre), puis `SIGKILL` après 10 s ; sous Windows il n'existe pas
d'équivalent pour une application console, l'arrêt est donc immédiat.

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

`GET /health` répond `{"status": "ok"}` sans lancer l'OCR ; `GET /` redirige vers `/docs`.
