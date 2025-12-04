# API Scraper PDF Baccalauréat Madagascar

## Overview
API Flask pour récupérer les PDFs des sujets et corrections du Baccalauréat de Madagascar depuis le site ACCESMAD (http://mediatheque.accesmad.org). L'API permet de scraper, filtrer et télécharger les sujets d'examen et leurs corrections.

## Matières disponibles
- **Mathematiques** (série A) - id: 817
- **Physique** (série A) - id: 819
- **Histoire-Géographie** (série A et C-D) - id: 132

## Fonctionnalités
- Scraping automatique des titres et URLs des PDFs
- Séparation entre sujets (énoncés) et corrections (corrigés)
- URLs simples pour téléchargement direct: `/pdf/<id>`
- Filtrage par matière, série, année et type
- Conversion automatique des pages HTML en PDF (années 1999-2011)
- Support des PDFs directs (années 2013-2023)

## Endpoints API

### GET /
Page d'accueil avec la liste des endpoints et exemples

### GET /recherche
Recherche avec filtres:
- `pdf` : filtre par nom/matière (mathematiques, physique, hg)
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

**Exemples Histoire-Géographie:**
```
/recherche?pdf=hg&serie=A&type=sujet
/recherche?pdf=hg&serie=A&type=sujet&annee=2023
/recherche?pdf=hg&serie=C&type=sujet
/recherche?pdf=hg&serie=D&type=sujet
/recherche?pdf=hg&serie=C&type=sujet&annee=2017
```

Note: Les séries C et D partagent le même contenu pour HG.

**Réponse JSON:**
```json
{
  "filtres": {
    "pdf": "hg",
    "serie": "A",
    "annee": "2023",
    "type": "sujet"
  },
  "total": 1,
  "resultats": [
    {
      "titre": "Histo Géo série A 2023 -énoncé",
      "annee": "2023",
      "serie": "A",
      "matiere": "Histoire-Geo",
      "type": "sujet",
      "format": "pdf",
      "id": "57567",
      "url_telechargement": "https://.../pdf/57567"
    }
  ]
}
```

### GET /pdf/<id>
Télécharge un PDF directement via son ID de ressource Moodle.
- Redirige automatiquement vers le fichier PDF
- Pour les pages HTML (1999-2011): conversion automatique en PDF
- Exemple: `/pdf/57567`

### GET /page/<id>
Télécharge une page HTML convertie en PDF.
- Utile pour les anciens sujets (1999-2011)
- Exemple: `/page/6191`

## Années disponibles par matière

### Mathématiques (série A)
1999-2023 (toutes les années)

### Physique (série A)
1999-2023 (toutes les années)

### Histoire-Géographie
- **Série A**: 1999-2005, 2008-2011, 2013-2017, 2023
- **Séries C-D**: 1999-2005, 2008-2011, 2013-2017, 2023

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
- Mathématiques/Physique: Section 1 = Sujets, Section 2 = Corrections
- HG série A: Section 1 = Sujets et Corrections
- HG séries C-D: Section 2 = Sujets et Corrections

## Notes techniques
- Les URLs `/pdf/<id>` redirigent directement vers le PDF
- Compatible téléphone: cliquez sur `url_telechargement` pour télécharger
- Années anciennes (1999-2011): conversion HTML→PDF automatique avec wkhtmltopdf
- Années récentes (2013-2023): téléchargement PDF direct

## Configuration des cours
Les cours sont configurés dans `main.py` via le dictionnaire `COURSES`:
```python
COURSES = {
    'mathematiques': {'id': 817, 'name': 'Mathematiques', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 2}},
    'physique': {'id': 819, 'name': 'Physique', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 2}},
    'hg_a': {'id': 132, 'name': 'Histoire-Geo', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 1}},
    'hg_cd': {'id': 132, 'name': 'Histoire-Geo', 'serie': 'C-D', 'sections': {'sujet': 2, 'correction': 2}}
}
```
