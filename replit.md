# API Baccalauréat Madagascar

API pour récupérer les sujets et corrections du Baccalauréat depuis mediatheque.accesmad.org

## Structure du Projet

```
├── main.py           # Application Flask principale
├── requirements.txt  # Dépendances Python
├── vercel.json       # Configuration Vercel (optionnel)
└── attached_assets/  # Fichiers attachés
```

## Dépendances

- Flask 3.0.0
- Requests 2.31.0
- BeautifulSoup4 4.12.2
- Gunicorn 21.2.0
- PyPDF2 3.0.1

## Lancer le Serveur

```bash
gunicorn --bind=0.0.0.0:5000 --reuse-port main:app
```

## Endpoints API

### Documentation
- `GET /` - Documentation complète de l'API

### État du Serveur
- `GET /health` - Vérifier l'état du serveur
- `GET /ping` - Simple ping/pong

### Liste des Matières
- `GET /matieres` - Liste de toutes les matières disponibles

### Récupérer les PDFs
- `GET /pdfs` - Tous les PDFs avec filtres optionnels
- `GET /pdf/<matiere>` - PDFs d'une matière spécifique

### Téléchargement
- `GET /telecharger` - Télécharger un PDF
- `GET /capturer` - Capturer une page en PDF

## Exemples d'Utilisation

### Lister les matières disponibles
```
GET /matieres
```

### Récupérer tous les PDFs de Mathématiques
```
GET /pdf/mathematiques
```

### Filtrer par matière et série
```
GET /pdfs?matiere=physique&serie=A
```

### Filtrer par type et année
```
GET /pdfs?matiere=francais&type=sujet&annee=2020
```

### Télécharger un PDF
```
GET /telecharger?url=http://mediatheque.accesmad.org/...&titre=Mon_PDF
```

## Matières Disponibles

- Mathematiques
- Physique
- Histoire-Geo (séries A, C-D)
- Malagasy (séries A, C-D, S, OSE)
- Philosophie (séries A, C-D, L)
- Francais (séries A-C-D, L, S, OSE)
- SVT (série A)
- Anglais (séries A, C-D, A-C-D, OSE)

## Paramètres de Filtrage

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| matiere | Nom de la matière | mathematiques, physique, francais |
| serie | Série du bac | A, C-D, L, S, OSE |
| type | Type de document | sujet, correction |
| annee | Année du sujet | 2020, 2019, etc. |
