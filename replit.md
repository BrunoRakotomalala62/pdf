# PDF Scraper EDUCMAD

## Overview
API Node.js pour scraper les liens PDF du site EDUCMAD - Sujets, Corrections du Bacc Sciences Physiques série A et Mathématiques série A.

## Project Architecture
- `index.js` - Serveur Express avec logique de scraping (sujets PC, corrections PC, mathématiques)
- `package.json` - Dépendances Node.js
- `vercel.json` - Configuration pour déploiement Vercel
- `web.html` - Fichier HTML de référence pour la structure du site (section 1 - sujets PC)
- `web2.html` - Fichier HTML de référence pour la structure du site (section 2 - corrections PC)
- `web3.html` - Fichier HTML de référence pour la structure du site (mathématiques)

## Technologies
- Node.js
- Express.js
- Axios (requêtes HTTP)
- Cheerio (parsing HTML)
- Puppeteer (conversion HTML en PDF)

## API Endpoints
- `GET /` - Message de bienvenue et usage
- `GET /recherche` - Retourne tous les PDFs (sujets PC)
- `GET /recherche?pdf=<terme>` - Recherche filtrée par terme (sujets PC)
- `GET /recherche?pdf=cor <terme>` - Recherche des corrections PC (préfixe "cor")
- `GET /recherche?pdf=Math <terme>` - Recherche des mathématiques (préfixe "Math")
- `GET /convertir?url=<url>` - Convertir une page HTML en PDF

## Exemples de recherche
### Sujets PC
- `/recherche?pdf=PC A 2020` - PDF spécifique
- `/recherche?pdf=PC A 2023&direct=true` - Avec lien direct du PDF
- `/recherche?pdf=PC A liste` - Tous les sujets

### Corrections PC
- `/recherche?pdf=cor PC A 2000` - Correction spécifique
- `/recherche?pdf=cor PC A 2023&direct=true` - Avec lien direct du PDF
- `/recherche?pdf=cor PC A liste` - Toutes les corrections (31 corrections de 1999 à 2023)

### Mathématiques série A
- `/recherche?pdf=Math A 2000` - Énoncé Math spécifique
- `/recherche?pdf=Math A 2022&direct=true` - Avec lien direct du PDF
- `/recherche?pdf=Math A liste` - Tous les énoncés Math (24 énoncés de 1999 à 2022 + Bacc Blanc)

## Source des données
- Sujets PC: http://mediatheque.accesmad.org/educmad/course/view.php?id=819
- Corrections PC: http://mediatheque.accesmad.org/educmad/course/view.php?id=819&section=2
- Mathématiques: http://mediatheque.accesmad.org/educmad/course/view.php?id=817&section=1
