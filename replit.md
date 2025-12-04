# API Scraper PDF Baccalauréat Madagascar

## Overview
API Flask pour récupérer les PDFs des sujets et corrections du Baccalauréat de Madagascar depuis le site ACCESMAD (http://mediatheque.accesmad.org). L'API permet de scraper, filtrer et télécharger les sujets d'examen et leurs corrections.

## Fonctionnalités
- Scraping automatique des titres et URLs des PDFs
- Séparation entre sujets (énoncés) et corrections (corrigés)
- Résolution des vraies URLs de PDF depuis les pages wrapper
- Filtrage par matière (Mathématiques, Physique, etc.), série (A, C, D), année et type
- Conversion des pages HTML en PDF téléchargeables
- Téléchargement direct des PDFs

## Endpoints API

### GET /
Page d'accueil avec la liste des endpoints disponibles et exemples d'utilisation

### GET /recherche
Recherche avec filtres:
- `pdf` : filtre par nom/matière (ex: mathematiques, physique)
- `serie` : filtre par série (A, C, D)
- `annee` : filtre par année (ex: 2005, 2022)
- `type` : filtre par type (`sujet` ou `correction`)

**Exemples:**
```
/recherche?pdf=mathematiques&serie=A&type=correction
/recherche?pdf=mathematiques&serie=A&type=sujet
/recherche?pdf=mathematiques&serie=A&type=correction&annee=2005
/recherche?pdf=physique&serie=C&type=sujet
```

**Réponse JSON:**
```json
{
  "filtres": {
    "pdf": "mathematiques",
    "serie": "A",
    "annee": "2005",
    "type": "correction"
  },
  "total": 3,
  "resultats": [
    {
      "titre": "Corrigé mathématiques exercice 1 série A 2005",
      "annee": "2005",
      "serie": "A",
      "matiere": "Mathematiques",
      "type": "correction",
      "url_telechargement": "https://..."
    }
  ]
}
```

### GET /telecharger
Télécharge un PDF directement
- `url` : URL de la ressource à télécharger
- `titre` : Titre pour le nom du fichier

### GET /capturer
Convertit une page web en PDF téléchargeable
- `url` : URL de la page à convertir
- `titre` : Titre pour le nom du fichier

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
- PyPDF2
- wkhtmltopdf (système) pour la conversion HTML vers PDF

## Démarrage
```bash
gunicorn --bind=0.0.0.0:5000 --reuse-port main:app
```

Le serveur démarre sur le port 5000.

## Sources de données
- Section 1: Énoncés/Sujets (http://mediatheque.accesmad.org/educmad/course/view.php?id=817&section=1)
- Section 2: Corrigés/Corrections (http://mediatheque.accesmad.org/educmad/course/view.php?id=817&section=2)

## Notes techniques
- Les URLs de téléchargement sont directement utilisables sur téléphone
- Certaines années anciennes (2000-2011) utilisent des pages HTML converties en PDF
- L'API détecte automatiquement le type (sujet/correction) basé sur le titre et la section source
