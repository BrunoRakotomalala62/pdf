# PDF Scraper EDUCMAD

API pour scraper les liens PDF du site EDUCMAD (mediatheque.accesmad.org)

## Utilisation

### Route principale

```
GET /recherche?pdf=<terme_recherche>
```

### Exemples

- Tous les PDFs: `/recherche`
- Recherche par annee: `/recherche?pdf=2020`
- Recherche par serie: `/recherche?pdf=série A`

### Reponse JSON

```json
{
  "success": true,
  "count": 12,
  "recherche": "tous",
  "resultats": [
    {
      "titre": "Sciences Physique série A 2023 énoncé",
      "url_pdf": "http://mediatheque.accesmad.org/educmad/mod/resource/view.php?id=57571"
    }
  ]
}
```

## Deploiement

Le projet est configure pour Vercel via `vercel.json`.
