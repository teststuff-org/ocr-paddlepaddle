# 1. Prompt d'implémentation : extraction PDF robuste

## Sommaire

- [1. Prompt d'implémentation : extraction PDF robuste](#1-prompt-dimplémentation--extraction-pdf-robuste)
  - [1.1 Comment utiliser ce document](#11-comment-utiliser-ce-document)
  - [1.2 Constat mesuré sur le code actuel](#12-constat-mesuré-sur-le-code-actuel)
- [2. Le prompt](#2-le-prompt)
  - [2.1 Rôle et mission](#21-rôle-et-mission)
  - [2.2 Contexte du dépôt et contraintes non négociables](#22-contexte-du-dépôt-et-contraintes-non-négociables)
  - [2.3 Définition de « robuste » (mesurable)](#23-définition-de-robuste-mesurable)
  - [2.4 Modèle de données cible](#24-modèle-de-données-cible)
  - [2.5 Pipeline cible, étape par étape](#25-pipeline-cible-étape-par-étape)
  - [2.6 Règles de décision](#26-règles-de-décision)
  - [2.7 Cas pièges à couvrir](#27-cas-pièges-à-couvrir)
  - [2.8 Contrat d'API](#28-contrat-dapi)
  - [2.9 Performances attendues](#29-performances-attendues)
  - [2.10 Observabilité exigée](#210-observabilité-exigée)
  - [2.11 Tests exigés](#211-tests-exigés)
  - [2.12 Découpage en tâches](#212-découpage-en-tâches)
  - [2.13 Critères d'acceptation](#213-critères-dacceptation)
  - [2.14 Interdits](#214-interdits)
- [3. Annexe : bibliothèques disponibles et arbitrage](#3-annexe--bibliothèques-disponibles-et-arbitrage)

## 1.1 Comment utiliser ce document

La section 2 est un prompt prêt à coller dans un agent d'implémentation (Claude Code, Copilot,
opencode). Elle est autonome : elle rappelle le contexte, fixe le contrat de sortie, énumère les
cas pièges et termine par des critères d'acceptation vérifiables un par un.

La section 1.2 justifie le prompt : elle consigne ce que le code actuel fait réellement,
mesuré sur trois PDF de test, et non supposé.

## 1.2 Constat mesuré sur le code actuel

Sonde exécutée le 16/11/2026 sur `app/readers/pdf_reader.py` (`read_pdf`), avec un PDF à tableau
4×4 et un PDF AcroForm (champ texte, liste déroulante, case à cocher).

| Attendu | Réalité du code actuel | Verdict |
|---|---|---|
| Tableau restitué en lignes/colonnes | 16 lignes plates, ordre de peinture, plus aucune notion de cellule | Non |
| Nombres négatifs | `-3.45`, `-48.30`, `-125,50` conservés dans la couche texte | Oui, tant qu'il y a une couche texte |
| Nombre négatif en OCR | Conservé sur un scan propre à 200 dpi ; non garanti sur un scan dégradé | Fragile |
| Liste déroulante | La valeur (`Canada`) apparaît comme une ligne de texte orpheline, sans lien avec le libellé `Pays :` | Non |
| Case à cocher | Restituée comme la chaîne `'3'` (glyphe de l'apparence), indiscernable du texte | Non |
| Champ de formulaire nommé | `page.widgets()` expose `nom` / `pays` / `tva` avec type et valeur ; le code ne l'appelle jamais | Information perdue |

Détail du rendu actuel sur le formulaire :

```
'Formulaire fournisseur'
'Nom :'          <- libellé
'Pays :'         <- libellé
'Assujetti TVA :'<- libellé
'Solde :'
'Hydro-Pro Inc.' <- valeur du champ texte, détachée de son libellé
'Canada'         <- valeur de la liste déroulante, détachée de son libellé
'3'              <- apparence de la case cochée
```

Alors que PyMuPDF, déjà présent dans les dépendances, donne directement :

```
'nom'  type='Text'     valeur='Hydro-Pro Inc.'
'pays' type='ComboBox' valeur='Canada'
'tva'  type='CheckBox' valeur='Yes'
```

Conclusion : le code actuel est un **extracteur de flux de texte**, pas un extracteur de
document. Il est fiable pour du texte courant, insuffisant dès qu'il y a une structure
(tableaux, formulaires) ou une ambiguïté de sens (libellé ↔ valeur, signe négatif).

# 2. Le prompt

## 2.1 Rôle et mission

Tu es ingénieur Python senior spécialisé en extraction documentaire. Ta mission : rendre
l'extraction de `ocr-api` **fidèle à la structure du PDF**, pas seulement à son flux de texte.

Le livrable doit extraire, sur un même document : le texte dans l'ordre de lecture, les tableaux
en cellules adressables, les champs de formulaire avec leur libellé, et les nombres sous forme
**numérique signée** — aussi bien sur un PDF natif que sur un scan.

Tu travailles par étapes vérifiables, tu mesures avant d'optimiser, et tu ne remplaces aucune
bibliothèque sans avoir écrit le test qui prouve que le remplacement est meilleur.

## 2.2 Contexte du dépôt et contraintes non négociables

- Dépôt `D:\workspace\ocr-api`, API FastAPI (`app/main.py`), endpoint `POST /documents/ocr`,
  export `json` ou `docx`. Python 3.11+.
- Dépendances déjà présentes : `pymupdf` (2.1), `paddleocr` (3.7), `python-docx`, `numpy`,
  `fastapi`, `uvicorn`. Toute dépendance nouvelle doit être justifiée dans la PR, épinglée
  dans `requirements.txt`, et installable hors ligne ou sur ARM64.
- **Windows x86_64 et Linux x86_64 sont tous deux cibles.** Aucune solution qui ne fonctionne que
  sur l'un des deux. Pas de GPU supposé disponible.
- Respecte `D:/workspace/aitools-org/sms-agents-and-skills/standards/engineering-standards.md` :
  `src/`-layout déjà en place, paquets par rôle (`routes/`, `services/`, `parsers/`, `models/`,
  `schemas/`), une classe par fichier avec le suffixe de son paquet, ≤ 300 lignes par module,
  ≤ 50 par fonction, ≤ 5 paramètres, ≤ 7 méthodes publiques, docstring de classe, injection par
  constructeur, pas de conteneur d'objets, pas de nom `utils`/`helpers`.
- Deux écarts existants à traiter explicitement dans la PR : `app/readers/` et `app/exporters/`
  ne font pas partie du vocabulaire des paquets standard. Propose dans la PR le renommage
  `readers/` → `parsers/` (rôle : contenu brut → `models`). Pour l'export, garde `exporters/`
  mais documente le rôle en tête de paquet, ou renomme en `writers/` : tranche, ne laisse pas
  deux conventions cohabiter.
- Le service `documents` reste **synchrone** (`def`, exécuté dans le threadpool FastAPI), et
  l'inférence PaddleOCR reste sérialisée par un verrou : elle n'est pas thread-safe.

## 2.3 Définition de « robuste » (mesurable)

Une extraction est robuste si, sur le jeu de test décrit en 2.11 :

1. **Structure** : chaque tableau du document est restitué avec ses dimensions exactes
   (lignes × colonnes), ses fusions de cellules, et un en-tête identifié.
2. **Sémantique** : chaque valeur de formulaire est rattachée à son libellé et à son type
   (`choice`, `checkbox`, `radio`, `text`, `signature`), avec l'état coché explicite.
3. **Nombres** : chaque montant est disponible en texte **et** en valeur numérique signée,
   y compris séparateurs français (`1 250,50`), parenthèses comptables (`(1 250,50)` → `-1250.5`),
   signe en fin (`1250,50-`), signe moins Unicode `−` (U+2212), et symboles monétaires.
4. **Ordre** : le texte est restitué dans un ordre de lecture humain sur un document à deux
   colonnes, sans fusionner en-tête ni pied de page dans le corps.
5. **Traçabilité** : chaque élément porte sa page, sa position (`bbox`) et sa provenance
   (`text_layer` / `ocr`), plus un indice de confiance quand il vient de l'OCR.
6. **Dégradation** : un PDF corrompu, chiffré, vide ou illisible renvoie une erreur explicite
   en 4xx avec un message actionnable, jamais un 500 opaque ; une page sans texte déclenche un
   avertissement dans la réponse, pas une extraction silencieusement vide.

## 2.4 Modèle de données cible

Ajoute dans `app/models/` les objets métier (aucune dépendance framework ni ORM) qui portent ce
schéma, puis les schémas Pydantic correspondants dans `app/schemas/` pour la sérialisation.

```json
{
  "page_count": 2,
  "warnings": ["page 2 : tableaux detectes sans trait, reconstruction heuristique"],
  "pages": [
    {
      "number": 1,
      "source": "text_layer",
      "rotation": 0,
      "width": 595.0,
      "height": 842.0,
      "blocks": [
        {"kind": "heading", "text": "Facture 2026-0042", "bbox": [60, 88, 300, 108], "confidence": 1.0},
        {"kind": "paragraph", "text": "Hydro-Pro Inc.", "bbox": [60, 120, 300, 136], "confidence": 1.0}
      ],
      "tables": [
        {
          "bbox": [60, 200, 480, 320],
          "header_rows": 1,
          "rows": [
            [
              {"text": "Article", "row_span": 1, "col_span": 1, "kind": "text"},
              {"text": "Montant", "row_span": 1, "col_span": 1, "kind": "text"}
            ],
            [
              {"text": "Joint torique", "row_span": 1, "col_span": 1, "kind": "text"},
              {"text": "-48,30", "row_span": 1, "col_span": 1, "kind": "number", "value": -48.3}
            ]
          ]
        }
      ],
      "form_fields": [
        {
          "name": "pays",
          "label": "Pays",
          "type": "choice",
          "value": "Canada",
          "options": ["Canada", "Belgique", "France"],
          "checked": null,
          "bbox": [120, 148, 320, 166]
        },
        {
          "name": "tva",
          "label": "Assujetti TVA",
          "type": "checkbox",
          "value": "Yes",
          "options": [],
          "checked": true,
          "bbox": [170, 188, 186, 204]
        }
      ],
      "numbers": [
        {"text": "-48,30", "value": -48.3, "source": "table", "table": 0, "row": 1, "col": 1}
      ]
    }
  ]
}
```

Contraintes sur ce schéma :

- `bbox` est en points PDF, origine en haut à gauche, `[x0, y0, x1, y1]`.
- `kind` d'un bloc vaut `heading`, `paragraph`, `list_item`, `table`, `form`, `footer`,
  `header` ou `unknown`. Aucune autre valeur.
- `value` n'est renseigné que si `kind == "number"` et que la conversion est certaine ;
  sinon `value: null` et le texte brut reste la référence.
- `confidence` est `1.0` pour la couche texte, la confiance du modèle pour l'OCR.
- Aucun champ `text` global ne disparaît : conserve `page.text` pour ne pas casser les
  appelants existants (compatibilité ascendante de l'endpoint).

## 2.5 Pipeline cible, étape par étape

Implémente dans cet ordre, en commit par étape, chaque étape testée avant la suivante.

**Étape 1 — Diagnostic du document.** À l'ouverture : pages, taille, chiffrement
(`doc.needs_pass`), PDF/XFA (`doc.is_form_pdf`), présence de couche texte par page. Journalise
ces faits. Un PDF chiffré renvoie 422 avec `detail` explicite (« PDF protégé par mot de passe »).

**Étape 2 — Contrôle de qualité de la couche texte.** Ne plus faire confiance aveuglément à
`page.get_text()` : mesure la part de caractères exploitables (alphanumériques + ponctuation),
compte les caractères de remplacement (`U+FFFD`), détecte l'absence de tout espace dans un texte
de plus de 40 caractères, et vérifie la présence d'un mapping `ToUnicode` sur les polices. Une
couche texte jugée inexploitable déclenche l'OCR **même sans `force_ocr`**, avec un
avertissement dans `warnings`.

**Étape 3 — Blocs, spans et positions.** Continue à lire la couche texte, mais via
`page.get_text("dict")` : récupère les blocs, leurs `bbox`, les tailles de police et les
positions de chaque span. C'est la matière première du classement titre/paragraphe, de l'ordre
de lecture et de la reconstruction de colonnes.

**Étape 4 — Tableaux vectoriels.** Utilise `page.find_tables()` (lattice pour les traits,
stream pour les tableaux sans traits). Pour chaque tableau : `extract()`, `header.names`,
`row_count`, `col_count`, et fusions. **Ne fais jamais confiance au texte de cellule brut** :
ré-extrais le texte de chaque cellule par `page.get_text("text", clip=cell_rect)` et corrige
les artefacts de recollage (mots collés, signe séparé de son nombre) — la sonde a montré
`'115000\n.'` et `'Prixunitaire'` sur un tableau pourtant simple. Si `find_tables` ne trouve rien
sur une page manifestement tabulaire (nombreuses lignes verticales ou colonnes alignées),
tente `pdfplumber` en second recours, ou une heuristique de colonnes par projection des `bbox`.

**Étape 5 — Tableaux scannés.** Sur une page en OCR : détecte les tableaux avec le modèle de
structure de PaddleOCR (PP-Structure, reconnaissance de table SLANet) ou `img2table`, puis
OCRise **cellule par cellule** en réutilisant les coordonnées détectées. Une cellule vide reste
une cellule vide : ne laisse pas l'OCR inventer du texte, et conserve `confidence` par cellule.

**Étape 6 — Champs de formulaire.** Parcours `page.widgets()` : `field_name`,
`field_type_string`, `field_value`, `choice_values`, `button_states`, `rect`, `field_flags`.
Traite `Text`, `ComboBox`/`ListBox` (liste déroulante), `CheckBox` (état coché par comparaison de
`field_value` aux `button_states` allumés), `RadioButton`, `Signature`, et les champs en lecture
seule. Pour chaque champ, associe le **libellé** : chercher le bloc de texte le plus proche à
gauche sur la même ligne de base, sinon au-dessus, avec une distance maximale proportionnelle à
la hauteur du champ ; à défaut, humanise `field_name`. Ne déduis jamais un libellé par la seule
proximité sans vérifier le recouvrement vertical.

**Étape 7 — OCR avec géométrie.** Le moteur actuel jette les boîtes et ne garde que `rec_texts`.
Conserve `rec_boxes`, `rec_polys` et `rec_scores` : sans eux, aucune reconstruction de lignes,
de colonnes ou d'ordre n'est possible. Regroupe les textes en lignes par recouvrement vertical,
puis en blocs par proximité.

**Étape 8 — Ordre de lecture.** Détecte les colonnes par histogramme des `x0` des blocs (deux
colonnes = deux pics séparés par un couloir vide sur toute la hauteur). Restitue : en-tête de
page, puis colonne gauche de haut en bas, puis colonne droite, puis pied de page. Marque
`header`/`footer` les blocs répétés à l'identique sur au moins 60 % des pages, ou situés dans les
8 % supérieurs/inférieurs de la page.

**Étape 9 — Nombres et normalisation.** Une seule fonction, une seule vérité, dans
`app/services/` (ou un module dédié nommé d'après son rôle, pas `utils`). Règles :

| Entrée | Sortie `value` |
|---|---|
| `1 250,50` (espace insécable inclus) | `1250.5` |
| `1,250.50` | `1250.5` |
| `(1 250,50)` | `-1250.5` (négatif comptable) |
| `1250,50-` | `-1250.5` |
| `−48,30` (U+2212) | `-48.3` |
| `-48.30 CAD` | `-48.3` |
| `1 250` | `1250.0` |
| `12 %` | `null` (ce n'est pas un montant), texte conservé |

La règle de séparateur décimal doit être décidée **par cellule ou par colonne**, jamais par
valeur isolée : dans un tableau, la convention est constante. Conserve toujours `text` à côté de
`value` : une conversion fausse doit rester détectable.

**Étape 10 — Export.** `json` sérialise le schéma complet. `docx` restitue les tableaux comme
**vrais tableaux Word** (`document.add_table`), les paires libellé/valeur comme deux colonnes, et
les montants au format numérique aligné à droite. Aucune régression pour les documents sans
structure : même texte, même ordre.

**Étape 11 — Orchestration.** Un service `DocumentExtractionService` (paquet `services/`)
orchestre les étapes ; les `parsers/` ne font que du parsing, les `models/` ne connaissent rien
du framework. La route ne fait que valider, appeler le service, mapper la réponse.

## 2.6 Règles de décision

- `force_ocr=true` : OCR systématique, sans contrôle de qualité de couche texte.
- `force_ocr=false` : couche texte si elle passe le contrôle de l'étape 2, sinon OCR.
- Page mixte (couche texte partielle, par exemple un en-tête numérique sur un corps scanné) :
  OCRise la page entière puis fusionne, en préférant la couche texte pour les zones où elle est
  exploitable ; journalise le cas, il est rare et coûteux à déboguer.
- PDF chiffré : 422. PDF invalide : 400. Page sans texte après OCR : 200 avec `warnings`, jamais
  500.
- Une exception inattendue : 500 avec un `detail` court, et la trace complète côté serveur
  uniquement.
- Taille d'upload : refuse au-delà de `MAX_UPLOAD_MB` (défaut 50) en 413.
- Nombre de pages : refuse au-delà de `MAX_PAGES` (défaut 200) en 422, avec le compte réel.

## 2.7 Cas pièges à couvrir

Chaque ligne ci-dessous doit exister comme test (voir 2.11). C'est la liste que le code doit
survivre, pas un catalogue théorique.

**Tableaux** : avec traits ; sans traits (colonnes alignées seulement) ; cellules fusionnées
horizontales et verticales ; en-tête sur deux lignes ; cellules multi-lignes ; colonne de
montants vides ; tableau à cheval sur deux pages ; tableau imbriqué ; texte qui déborde de la
cellule ; tableau sans en-tête.

**Formulaires** : liste déroulante avec valeur par défaut ; case à cocher non cochée ; groupe de
boutons radio avec une seule sélection ; champ texte multi-lignes ; champ hérité (même nom sur
plusieurs pages) ; formulaire XFA (non supporté nativement par PyMuPDF : détecte et renvoie un
avertissement explicite plutôt qu'une extraction vide) ; libellé à droite du champ ; libellé
au-dessus ; champ sans libellé.

**Nombres** : négatif en couche texte ; négatif reconnu par OCR ; parenthèses comptables ; signe
final ; pourcentage ; montant avec devise ; zéro ; nombre avec exposant ; séparateurs FR et EN
dans le même document.

**Mise en page** : deux colonnes ; trois colonnes ; page pivotée (90/180/270) ; en-tête et pied
de page répétés ; filigrane diagonal ; texte vertical dans une marge ; note de bas de page ;
sommaire avec points de suite.

**PDF dégradés** : scan incliné de 3° ; scan à 100 dpi ; page photographiée avec ombre ; police
sans `ToUnicode` (texte extrait en charabia) ; PDF producé par LaTeX avec ligatures (`ﬁ`) ;
PDF avec zone de texte rasterisée dans un document par ailleurs natif ; PDF de 0 octet ; PDF
tronqué ; PDF chiffré.

**Caractères** : tiret `-` vs moins `−` vs tiret cadratin `—` ; espace insécable dans les
nombres ; `€` et `$` ; accents français sur majuscules ; apostrophe typographique.

## 2.8 Contrat d'API

- `POST /documents/ocr` garde ses paramètres actuels (`file`, `format`, `force_ocr`).
- Ajoute un paramètre `structure` (booléen, défaut `true`) : à `false`, la réponse reste le texte
  plat actuel — garantit la compatibilité avec les appelants existants et permet d'isoler une
  régression de structure.
- Ajoute `GET /documents/{id}` seulement si tu introduis un stockage ; par défaut, pas d'état,
  pas de base : l'API reste sans stockage.
- Le JSON doit rester **stable** : ajouter des champs est permis, en retirer ou en renommer ne
  l'est pas. Documente le schéma dans le README et dans l'OpenAPI (modèles Pydantic, pas de
  `dict` nu).
- Erreurs : `{"detail": "message actionnable"}`. Codes : 400 PDF invalide, 413 trop volumineux,
  422 chiffré / trop de pages / format non supporté, 500 échec interne.

## 2.9 Performances attendues

Mesuré sur cette machine (CPU, oneDNN indisponible) : page A4 avec couche texte < 50 ms ;
page A4 scannée à 200 dpi, profil `mobile` ≈ 10 s, profil `medium` ≈ 50 s.

- Ne rends jamais une page en image si la couche texte suffit : le rendu est le premier coût.
- Rends à `RENDER_DPI` (défaut 200) et plafonne la plus grande dimension à 4000 px avant inférence.
- Charge le moteur une seule fois (`lru_cache`), sérialise l'inférence par verrou, et journalise
  le temps de chargement du modèle séparément du temps d'inférence.
- Objectif : PDF texte de 10 pages < 1 s ; scan de 10 pages < 2 min en profil `mobile`.
- Toute optimisation doit être précédée d'une mesure journalisée, pas d'une intuition.

## 2.10 Observabilité exigée

Déjà en place, à conserver et compléter :

- Démarrage : configuration effective (langue, dpi, profil de modèle, oneDNN, niveau de journal).
- Requête : fichier, taille, format, `force_ocr`, durée, taille de sortie.
- Document : pages, dont pages OCR, pages vides, lignes, durée totale.
- Page : provenance et durée (INFO si OCR, DEBUG sinon).
- Erreur : trace complète côté serveur, message court côté client.
- À ajouter : nombre de tableaux, de cellules et de champs extraits par page ; avertissements
  émis ; nombre de caractères illisibles détectés dans la couche texte.

## 2.11 Tests exigés

Arborescence séparée, miroir de `app/` : `tests/unit/`, `tests/integration/`,
`tests/architecture/`. Framework : `pytest` (+ `pytest-asyncio` si besoin).

- **Fixtures générées** : un module de fixtures qui **fabrique** les PDF de test avec PyMuPDF
  (tableau avec traits, tableau sans traits, fusions, formulaire complet, scan synthétique à
  différentes résolutions, page pivotée, deux colonnes). Pas de binaires opaques dans le dépôt :
  les PDF sont produits par le code, donc lisibles et modifiables.
- **Un test par comportement**, nommé par le comportement :
  `test_extrait_un_montant_negatif_entre_parentheses`, `test_rattache_la_valeur_a_son_libelle`,
  `test_restaure_un_tableau_4x4_avec_entete`, `test_ne_considere_pas_le_texte_illisible_comme_une_couche_texte`.
- **Tests de non-régression** sur le texte plat (`structure=false`) : le comportement actuel ne
  doit pas changer.
- **Tests d'architecture** (déjà exigés par les standards) : `models/` n'importe pas `fastapi`,
  aucun endpoint hors `routes/`, plafonds de taille respectés, pas de `utils.py`.
- **Test de performance** marqué `slow`, hors CI par défaut : une page A4 texte sous 1 s.
- Aucun test ne doit télécharger de modèle : injecte un faux moteur OCR pour les tests unitaires,
  et ne touche au vrai PaddleOCR que dans un test d'intégration marqué `slow`.

## 2.12 Découpage en tâches

Livre dans cet ordre, un commit par tâche, la PR restant verte à chaque étape :

1. Modèle de données + schémas Pydantic + sérialisation JSON (`structure=false` inchangé).
2. Diagnostic PDF et contrôle de qualité de la couche texte, avec tests.
3. Blocs et positions (`get_text("dict")`), ordre de lecture simple (une colonne), en-têtes et
   pieds de page détectés.
4. Tableaux vectoriels via `find_tables`, re-extraction du texte par cellule, tests des artefacts.
5. Champs de formulaire et rattachement des libellés, tests des 4 types de champs.
6. Normalisation des nombres, table de cas exhaustive, tests paramétrés.
7. OCR avec géométrie (boîtes) et reconstruction de lignes, test sur scan synthétique.
8. Export `docx` structuré (vrais tableaux, paires libellé/valeur).
9. Colonnes multiples et pages mixtes.
10. Garde-fous : taille, pages, chiffrement, erreurs, `warnings`.

## 2.13 Critères d'acceptation

À cocher un par un dans la description de la PR, avec la preuve (sortie de test ou extrait de
journal) pour chacun :

- [ ] Le PDF de fixture à tableau 4×4 donne 4 lignes et 4 colonnes, avec en-tête identifié.
- [ ] La cellule `-48,30` donne `text="-48,30"` et `value=-48.3`.
- [ ] `(1 250,50)` donne `value=-1250.5` et un texte conservé.
- [ ] La liste déroulante `pays` donne `type="choice"`, `value="Canada"`, `label="Pays"`.
- [ ] La case à cocher `tva` donne `checked=true` et `label="Assujetti TVA"` (plus jamais `'3'`).
- [ ] Un scan synthétique de tableau donne un tableau de mêmes dimensions que le tableau source.
- [ ] Un PDF à deux colonnes est restitué colonne par colonne, pas ligne par ligne.
- [ ] Un PDF à couche texte illisible part en OCR et produit un `warning` explicite.
- [ ] Un PDF chiffré renvoie 422, un fichier non-PDF renvoie 400, jamais 500.
- [ ] `structure=false` renvoie exactement la sortie actuelle (test de non-régression).
- [ ] L'export `docx` contient un vrai tableau Word (vérifié en relisant le `.docx` produit).
- [ ] Les logs d'une requête permettent de savoir, sans deviner : pages, dont OCR, tableaux,
      champs, avertissements et durée par étape.
- [ ] `pytest` passe sur Windows et sur Linux, sans accès réseau.

## 2.14 Interdits

- Pas de solution qui ne fonctionne qu'avec un GPU ou qu'avec un service en ligne payant.
- Pas de `except Exception: pass`. Toute exception est journalisée avec sa trace et traduite en
  code HTTP explicite.
- Pas de nouvelle dépendance qui duplique PyMuPDF (pas d'ajout de `pdfminer` si `pymupdf` couvre
  le besoin).
- Pas de sortie de texte sans coordonnées : sans géométrie, la structure est irrécupérable après
  coup.
- Pas de `dict` nu dans les réponses : des modèles Pydantic typés.
- Pas de refonte silencieuse du format JSON existant : compatibilité ascendante obligatoire.
- Pas d'optimisation non mesurée.

# 3. Annexe : bibliothèques disponibles et arbitrage

| Besoin | Outil | Verdict |
|---|---|---|
| Texte, blocs, spans, coordonnées | **PyMuPDF** (déjà présent) | Suffisant, aucune dépendance de plus |
| Champs de formulaire | **PyMuPDF** `page.widgets()` | Seule source correcte (AcroForm) |
| Tableaux vectoriels | **PyMuPDF** `find_tables()` | Bon premier choix, artefacts à corriger |
| Tableaux vectoriels difficiles | **pdfplumber** | Second recours ciblé, ajout de dépendance à justifier |
| Tableaux scannés | **PP-Structure** (PaddleOCR déjà présent) ou **img2table** | Naturel, même écosystème ; à mesurer |
| OCR | **PaddleOCR** (déjà présent) | À conserver, mais **garder les boîtes** |
| Alternative OCR plus rapide sur CPU | **RapidOCR** (ONNXRuntime) | À évaluer seulement si Paddle reste trop lent |
| Extraction de bout en bout par modèle de layout | **Docling**, **Marker** | Puissants mais lourds (modèles, GPU) ; hors périmètre par défaut |

Ordre de préférence : d'abord tirer tout ce que PyMuPDF expose déjà, ensuite le PaddleOCR déjà
installé, et n'ajouter une brique que si un test montre qu'elle fait mieux que ce qui existe.
