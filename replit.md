# API Scraper PDF Baccalauréat Madagascar

## Overview
API Flask pour récupérer les PDFs des sujets du Baccalauréat de Madagascar depuis le site ACCESMAD (http://mediatheque.accesmad.org). L'API permet de scraper, filtrer et télécharger les sujets d'examen de 1999 à 2022.

## Fonctionnalités
- Scraping automatique des titres et URLs des PDFs
- Résolution des vraies URLs de PDF depuis les pages wrapper
- Filtrage par matière (Mathématiques, Physique, etc.), série (A, C, D) et année
- Récupération du contenu des pages avec extraction du texte depuis "Baccalauréat de l'enseignement général"
- Conversion des pages HTML en PDF téléchargeables
- Téléchargement direct des PDFs

## Endpoints API

### GET /
Page d'accueil avec la liste des endpoints disponibles

### GET /pdfs
Retourne tous les PDFs disponibles au format JSON
```json
{
  "total": 100,
  "source": "http://mediatheque.accesmad.org/...",
  "pdfs": [...]
}
```

### GET /recherche
Recherche avec filtres:
- `pdf` : filtre par nom/matière (ex: Mathematiques)
- `serie` : filtre par série (A, C, D)
- `annee` : filtre par année (1999-2022)

Exemple: `/recherche?pdf=Mathematiques&serie=A`

### GET /contenu
Récupère le contenu textuel d'une page
- `url` : URL de la page à récupérer

### GET /telecharger
Télécharge un PDF directement
- `url` : URL de la ressource à télécharger

### GET /convertir
Convertit une page web en PDF téléchargeable
- `url` : URL de la page à convertir

## Structure des fichiers
```
├── main.py           # Application Flask principale
├── requirements.txt  # Dépendances Python
└── replit.md        # Documentation
```

## Dépendances
- Flask 3.0.0
- requests 2.31.0
- beautifulsoup4 4.12.2
- gunicorn 21.2.0
- wkhtmltopdf (système) pour la conversion HTML vers PDF

## Démarrage
```bash
python main.py
```

Le serveur démarre sur le port 5000.

## Années disponibles
Les sujets couvrent les années de 1999 à 2022 pour différentes séries (A, C, D) et matières.
