# PDF Scraper EDUCMAD

## Overview
API Node.js pour scraper les liens PDF du site EDUCMAD (Sciences Physiques série A).

## Project Architecture
- `index.js` - Serveur Express avec logique de scraping
- `package.json` - Dépendances Node.js
- `vercel.json` - Configuration pour déploiement Vercel
- `web.html` - Fichier HTML de référence pour la structure du site

## Technologies
- Node.js
- Express.js
- Axios (requêtes HTTP)
- Cheerio (parsing HTML)

## API Endpoints
- `GET /` - Message de bienvenue et usage
- `GET /recherche` - Retourne tous les PDFs
- `GET /recherche?pdf=<terme>` - Recherche filtrée par terme

## Source des données
http://mediatheque.accesmad.org/educmad/course/view.php?id=819
