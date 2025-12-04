# API Scraper PDF Baccalauréat Madagascar

## Overview
API Flask pour récupérer les PDFs des sujets et corrections du Baccalauréat de Madagascar depuis le site ACCESMAD (http://mediatheque.accesmad.org). L'API permet de scraper, filtrer et télécharger les sujets d'examen et leurs corrections.

## Fonctionnalités
- Scraping automatique des titres et URLs des PDFs
- Séparation entre sujets (énoncés) et corrections (corrigés)
- URLs simples pour téléchargement direct: `/pdf/<id>`
- Filtrage par matière, série, année et type
- Conversion automatique des pages HTML en PDF

## Endpoints API

### GET /
Page d'accueil avec la liste des endpoints et exemples

### GET /recherche
Recherche avec filtres:
- `pdf` : filtre par nom/matière (ex: mathematiques, physique)
- `serie` : filtre par série (A, C, D)
- `annee` : filtre par année (ex: 2005, 2023)
- `type` : filtre par type (`sujet` ou `correction`)

**Exemples:**
```
/recherche?pdf=mathematiques&serie=A&type=correction
/recherche?pdf=mathematiques&serie=A&type=sujet
/recherche?pdf=mathematiques&serie=A&type=correction&annee=2023
```

**Réponse JSON:**
```json
{
  "filtres": {
    "pdf": "mathematiques",
    "serie": "A",
    "annee": "2023",
    "type": "correction"
  },
  "total": 3,
  "resultats": [
    {
      "titre": "Corrigé Mathématiques Exercices série A 2023",
      "annee": "2023",
      "serie": "A",
      "matiere": "Mathematiques",
      "type": "correction",
      "id": "57064",
      "url_telechargement": "https://.../pdf/57064"
    }
  ]
}
```

### GET /pdf/<id>
Télécharge un PDF directement via son ID de ressource Moodle.
- Redirige automatiquement vers le fichier PDF
- Exemple: `/pdf/57064`

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
- Années anciennes (2000-2011): conversion HTML→PDF automatique
