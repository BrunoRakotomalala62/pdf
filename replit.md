# API Scraper PDF Baccalauréat Madagascar

## Overview
API Flask pour récupérer les PDFs des sujets et corrections du Baccalauréat de Madagascar depuis le site ACCESMAD (http://mediatheque.accesmad.org). L'API permet de scraper, filtrer et télécharger les sujets d'examen et leurs corrections.

## Matières disponibles
- **Mathematiques** (série A) - id: 817
- **Physique** (série A) - id: 819

## Fonctionnalités
- Scraping automatique des titres et URLs des PDFs
- Séparation entre sujets (énoncés) et corrections (corrigés)
- URLs simples pour téléchargement direct: `/pdf/<id>`
- Filtrage par matière, série, année et type
- Conversion automatique des pages HTML en PDF (années 1999-2012)
- Support des PDFs directs (années 2013-2023)

## Endpoints API

### GET /
Page d'accueil avec la liste des endpoints et exemples

### GET /recherche
Recherche avec filtres:
- `pdf` : filtre par nom/matière (mathematiques, physique)
- `serie` : filtre par série (A, C, D, L)
- `annee` : filtre par année (1999 à 2023)
- `type` : filtre par type (`sujet` ou `correction`)

**Exemples Mathématiques:**
```
/recherche?pdf=mathematiques&serie=A&type=sujet
/recherche?pdf=mathematiques&serie=A&type=correction
/recherche?pdf=mathematiques&serie=A&type=correction&annee=2023
```

**Exemples Physique:**
```
/recherche?pdf=physique&serie=A&type=sujet
/recherche?pdf=physique&serie=A&type=correction
/recherche?pdf=physique&serie=A&type=sujet&annee=2019
/recherche?pdf=physique&serie=A&type=correction&annee=2019
```

**Réponse JSON:**
```json
{
  "filtres": {
    "pdf": "physique",
    "serie": "A",
    "annee": "2019",
    "type": "sujet"
  },
  "total": 2,
  "resultats": [
    {
      "titre": "Sciences Physiques série A 1ère session 2019 - énoncé",
      "annee": "2019",
      "serie": "A",
      "matiere": "Physique",
      "type": "sujet",
      "format": "pdf",
      "id": "44720",
      "url_telechargement": "https://.../pdf/44720"
    }
  ]
}
```

### GET /pdf/<id>
Télécharge un PDF directement via son ID de ressource Moodle.
- Redirige automatiquement vers le fichier PDF
- Pour les pages HTML (1999-2012): conversion automatique en PDF
- Exemple: `/pdf/57064`

### GET /page/<id>
Télécharge une page HTML convertie en PDF.
- Utile pour les anciens sujets (1999-2012)
- Exemple: `/page/26053`

## Structure des fichiers
```
├── main.py           # Application Flask principale
├── requirements.txt  # Dépendances Python
├── vercel.json       # Configuration Vercel (optionnel)
└── replit.md         # Documentation
```

## Dépendances
- Flask 3.0.0
- requests 2.31.0
- beautifulsoup4 4.12.2
- gunicorn 21.2.0
- wkhtmltopdf (système) pour la conversion HTML vers PDF

## Démarrage
```bash
gunicorn --bind=0.0.0.0:5000 --reuse-port main:app
```

## Sources de données
- Section 1: Énoncés/Sujets
- Section 2: Corrigés/Corrections

## Notes techniques
- Les URLs `/pdf/<id>` redirigent directement vers le PDF
- Compatible téléphone: cliquez sur `url_telechargement` pour télécharger
- Années anciennes (1999-2012): conversion HTML→PDF automatique avec wkhtmltopdf
- Années récentes (2013-2023): téléchargement PDF direct

## Configuration des cours
Les cours sont configurés dans `main.py` via le dictionnaire `COURSES`:
```python
COURSES = {
    'mathematiques': {'id': 817, 'name': 'Mathematiques', 'serie': 'A'},
    'physique': {'id': 819, 'name': 'Physique', 'serie': 'A'}
}
```
