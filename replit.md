# API Scraper PDF Baccalauréat Madagascar

## Overview
API Flask pour récupérer les PDFs des sujets et corrections du Baccalauréat de Madagascar depuis le site ACCESMAD (http://mediatheque.accesmad.org). L'API permet de scraper, filtrer et télécharger les sujets d'examen et leurs corrections.

## Matières disponibles
- **Mathematiques** (série A) - id: 817
- **Physique** (série A) - id: 819
- **Histoire-Géographie** (série A et C-D) - id: 132
- **Malagasy** (séries A, C-D, S, OSE) - id: 130
- **Philosophie** (séries A, C-D, L) - id: 131
- **Français** (séries A-C-D, L, S, OSE) - id: 134
- **Anglais** (séries A, C-D, A-C-D (Remplacement), OSE) - id: 135

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
- `pdf` : filtre par nom/matière (mathematiques, physique, hg, malagasy, philosophie, francais, anglais)
- `serie` : filtre par série (A, C, D, L, S, OSE, A-C-D)
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

**Exemples Malagasy:**
```
/recherche?pdf=malagasy&serie=A&type=sujet
/recherche?pdf=malagasy&serie=A&type=sujet&annee=2019
/recherche?pdf=malagasy&serie=C&type=sujet
/recherche?pdf=malagasy&serie=D&type=sujet
/recherche?pdf=malagasy&serie=C&type=sujet&annee=2019
/recherche?pdf=malagasy&serie=S&type=sujet
/recherche?pdf=malagasy&serie=S&type=sujet&annee=2022
/recherche?pdf=malagasy&serie=OSE&type=sujet
/recherche?pdf=malagasy&serie=OSE&type=sujet&annee=2022
```

Note: Les séries C et D partagent le même contenu pour Malagasy. Les séries S et OSE ne contiennent que les années 2022-2023.

**Exemples Philosophie:**
```
/recherche?pdf=philosophie&serie=A&type=sujet
/recherche?pdf=philosophie&serie=A&type=sujet&annee=2017
/recherche?pdf=philosophie&serie=C&type=sujet
/recherche?pdf=philosophie&serie=D&type=sujet
/recherche?pdf=philosophie&serie=C&type=sujet&annee=2019
/recherche?pdf=philosophie&serie=L&type=sujet
/recherche?pdf=philosophie&serie=L&type=sujet&annee=2022
```

Note: Les séries C et D partagent le même contenu pour Philosophie. La série L ne contient que les années 2022-2023.

**Exemples Français:**
```
/recherche?pdf=francais&serie=A&type=sujet
/recherche?pdf=francais&serie=A&type=sujet&annee=2017
/recherche?pdf=francais&serie=C&type=sujet
/recherche?pdf=francais&serie=D&type=sujet
/recherche?pdf=francais&serie=C&type=sujet&annee=2015
/recherche?pdf=francais&serie=L&type=sujet
/recherche?pdf=francais&serie=L&type=sujet&annee=2022
/recherche?pdf=francais&serie=S&type=sujet
/recherche?pdf=francais&serie=S&type=sujet&annee=2023
/recherche?pdf=francais&serie=OSE&type=sujet
/recherche?pdf=francais&serie=OSE&type=sujet&annee=2023
```

Note: Les séries A, C et D partagent le même contenu pour Français. Les séries L, S et OSE ne contiennent que les années 2022-2023.

**Exemples Anglais:**
```
/recherche?pdf=anglais&serie=A&type=sujet
/recherche?pdf=anglais&serie=A&type=sujet&annee=2016
/recherche?pdf=anglais&serie=C&type=sujet
/recherche?pdf=anglais&serie=D&type=sujet
/recherche?pdf=anglais&serie=C&type=sujet&annee=2017
/recherche?pdf=anglais&serie=ACD&type=sujet
/recherche?pdf=anglais&serie=OSE&type=sujet
```

Note: Les séries C et D partagent le même contenu. La série A-C-D contient les sujets de Remplacement (2000, 2002). La série OSE ne contient que 2022.

**Réponse JSON:**
```json
{
  "filtres": {
    "pdf": "malagasy",
    "serie": "A",
    "annee": "2023",
    "type": "sujet"
  },
  "total": 1,
  "resultats": [
    {
      "titre": "Malagasy série A 2023 énoncé",
      "annee": "2023",
      "serie": "A",
      "matiere": "Malagasy",
      "type": "sujet",
      "format": "pdf",
      "id": "57580",
      "url_telechargement": "https://.../pdf/57580"
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

### Malagasy
- **Série A**: 1999-2023 (2013-2023 en PDF, 1999-2011 en pages)
- **Séries C-D**: 1999-2023 (2013-2023 en PDF, 1999-2011 en pages)
- **Série S**: 2022-2023 (PDF uniquement)
- **Série OSE**: 2022-2023 (PDF uniquement)

### Philosophie
- **Série A**: 1999-2022 (2013-2022 en PDF, 1999-2011 en pages)
- **Séries C-D**: 1999-2023 (2013-2023 en PDF, 1999-2011 en pages)
- **Série L**: 2022-2023 (PDF uniquement)

### Français
- **Séries A-C-D**: 1999-2023 (2013-2023 en PDF, 1999-2011 en pages)
- **Série L**: 2022-2023 (PDF uniquement)
- **Série S**: 2023 (PDF uniquement)
- **Série OSE**: 2023 (PDF uniquement)

### Anglais
- **Série A**: 1999-2022 (2013-2022 en PDF, 1999-2011 en pages)
- **Séries C-D**: 1999-2023 (2013-2023 en PDF, 1999-2011 en pages)
- **Série A-C-D (Remplacement)**: 2000, 2002 (pages HTML)
- **Série OSE**: 2022 (PDF uniquement)

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
- Malagasy série A: Section 1 = Sujets et Corrections
- Malagasy séries C-D: Section 2 = Sujets et Corrections
- Malagasy série S: Section 3 = Sujets et Corrections
- Malagasy série OSE: Section 4 = Sujets et Corrections
- Philosophie série A: Section 1 = Sujets et Corrections (contient aussi L 2023 et CD 2019)
- Philosophie séries C-D: Section 2 = Sujets et Corrections
- Philosophie série L: Section 3 = Sujets et Corrections (+ L 2023 dans section 1)
- Français séries A-C-D, L, S, OSE: Section 1 = Sujets
- Anglais série A: Section 1 = Sujets et Corrections
- Anglais séries C-D: Section 2 = Sujets et Corrections
- Anglais série A-C-D (Remplacement): Section 3 = Sujets et Corrections
- Anglais série OSE: Section 4 = Sujets et Corrections

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
    'hg_cd': {'id': 132, 'name': 'Histoire-Geo', 'serie': 'C-D', 'sections': {'sujet': 2, 'correction': 2}},
    'malagasy_a': {'id': 130, 'name': 'Malagasy', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 1}},
    'malagasy_cd': {'id': 130, 'name': 'Malagasy', 'serie': 'C-D', 'sections': {'sujet': 2, 'correction': 2}},
    'malagasy_s': {'id': 130, 'name': 'Malagasy', 'serie': 'S', 'sections': {'sujet': 3, 'correction': 3}},
    'malagasy_ose': {'id': 130, 'name': 'Malagasy', 'serie': 'OSE', 'sections': {'sujet': 4, 'correction': 4}},
    'philosophie_a': {'id': 131, 'name': 'Philosophie', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 1}},
    'philosophie_cd': {'id': 131, 'name': 'Philosophie', 'serie': 'C-D', 'sections': {'sujet': 2, 'correction': 2}},
    'philosophie_l': {'id': 131, 'name': 'Philosophie', 'serie': 'L', 'sections': {'sujet': 3, 'correction': 3}},
    'francais_acd': {'id': 134, 'name': 'Francais', 'serie': 'A-C-D', 'sections': {'sujet': 1, 'correction': 1}},
    'francais_l': {'id': 134, 'name': 'Francais', 'serie': 'L', 'sections': {'sujet': 1, 'correction': 1}},
    'francais_s': {'id': 134, 'name': 'Francais', 'serie': 'S', 'sections': {'sujet': 1, 'correction': 1}},
    'francais_ose': {'id': 134, 'name': 'Francais', 'serie': 'OSE', 'sections': {'sujet': 1, 'correction': 1}},
    'anglais_a': {'id': 135, 'name': 'Anglais', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 1}},
    'anglais_cd': {'id': 135, 'name': 'Anglais', 'serie': 'C-D', 'sections': {'sujet': 2, 'correction': 2}},
    'anglais_acd': {'id': 135, 'name': 'Anglais', 'serie': 'A-C-D', 'sections': {'sujet': 3, 'correction': 3}},
    'anglais_ose': {'id': 135, 'name': 'Anglais', 'serie': 'OSE', 'sections': {'sujet': 4, 'correction': 4}}
}
```
