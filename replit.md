# PDF Scraper EDUCMAD

## Overview
API Node.js pour scraper les liens PDF du site EDUCMAD (Sciences Physiques série A) - Sujets et Corrections du Bacc.

## Project Architecture
- `index.js` - Serveur Express avec logique de scraping (sujets + corrections)
- `package.json` - Dépendances Node.js
- `vercel.json` - Configuration pour déploiement Vercel
- `web.html` - Fichier HTML de référence pour la structure du site (section 1 - sujets)
- `web2.html` - Fichier HTML de référence pour la structure du site (section 2 - corrections)

## Technologies
- Node.js
- Express.js
- Axios (requêtes HTTP)
- Cheerio (parsing HTML)
- Puppeteer (conversion HTML en PDF)

## API Endpoints
- `GET /` - Message de bienvenue et usage
- `GET /recherche` - Retourne tous les PDFs (sujets)
- `GET /recherche?pdf=<terme>` - Recherche filtrée par terme (sujets)
- `GET /recherche?pdf=cor <terme>` - Recherche des corrections (préfixe "cor")
- `GET /convertir?url=<url>` - Convertir une page HTML en PDF

## Exemples de recherche
### Sujets
- `/recherche?pdf=PC A 2020` - PDF spécifique
- `/recherche?pdf=PC A 2023&direct=true` - Avec lien direct du PDF
- `/recherche?pdf=PC A liste` - Tous les sujets

### Corrections
- `/recherche?pdf=cor PC A 2000` - Correction spécifique
- `/recherche?pdf=cor PC A 2023&direct=true` - Avec lien direct du PDF
- `/recherche?pdf=cor PC A liste` - Toutes les corrections (31 corrections de 1999 à 2023)

## Source des données
- Sujets: http://mediatheque.accesmad.org/educmad/course/view.php?id=819
- Corrections: http://mediatheque.accesmad.org/educmad/course/view.php?id=819&section=2
