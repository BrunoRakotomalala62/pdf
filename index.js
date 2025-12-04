const express = require('express');
const axios = require('axios');
const cheerio = require('cheerio');
const chromium = require('@sparticuz/chromium');
const puppeteer = require('puppeteer-core');

const app = express();
const PORT = process.env.PORT || 5000;

// URLs sources
const SOURCES = {
  sujetsPC: 'http://mediatheque.accesmad.org/educmad/course/view.php?id=819',
  correctionsPC: 'http://mediatheque.accesmad.org/educmad/course/view.php?id=819&section=2',
  sujetsMath: 'http://mediatheque.accesmad.org/educmad/course/view.php?id=817&section=1',
  correctionsMath: 'http://mediatheque.accesmad.org/educmad/course/view.php?id=817&section=2'
};

// Fonction pour scraper une section
async function scraperSection(url) {
  try {
    const response = await axios.get(url);
    const $ = cheerio.load(response.data);
    const resultats = [];

    $('a[onclick*="window.open"]').each((i, elem) => {
      const titre = $(elem).text().trim();
      const onclick = $(elem).attr('onclick');
      
      if (onclick) {
        const match = onclick.match(/window\.open\('([^']+)'/);
        if (match) {
          const urlPdf = match[1];
          if (urlPdf.includes('view.php')) {
            resultats.push({
              titre: titre,
              url_pdf: urlPdf
            });
          }
        }
      }
    });

    return resultats;
  } catch (error) {
    console.error('Erreur lors du scraping:', error.message);
    return [];
  }
}

// Fonction pour obtenir le lien direct du PDF
async function obtenirLienDirectPDF(urlPage) {
  try {
    const response = await axios.get(urlPage);
    const $ = cheerio.load(response.data);
    
    let lienPDF = null;
    $('a').each((i, elem) => {
      const href = $(elem).attr('href');
      if (href && href.endsWith('.pdf')) {
        lienPDF = href;
        return false;
      }
    });

    return lienPDF;
  } catch (error) {
    console.error('Erreur lors de la récupération du lien direct:', error.message);
    return null;
  }
}

// Fonction pour filtrer les résultats
function filtrerResultats(resultats, terme) {
  if (!terme || terme.toLowerCase() === 'liste') {
    return resultats;
  }
  
  const termeNormalise = terme.toLowerCase();
  return resultats.filter(r => 
    r.titre.toLowerCase().includes(termeNormalise)
  );
}

// Route principale
app.get('/', (req, res) => {
  res.json({
    message: 'API PDF Scraper EDUCMAD',
    usage: {
      recherche: '/recherche?pdf=<terme>',
      exemples: [
        '/recherche - Tous les sujets PC',
        '/recherche?pdf=PC A 2020 - Sujet spécifique',
        '/recherche?pdf=cor PC A 2023 - Correction PC',
        '/recherche?pdf=Math A 2022 - Sujet Math',
        '/recherche?pdf=cor Math A 2014 - Correction Math',
        '/recherche?pdf=PC A 2023&direct=true - Avec lien direct du PDF'
      ],
      convertir: '/convertir?url=<url> - Convertir HTML en PDF'
    }
  });
});

// Route de recherche
app.get('/recherche', async (req, res) => {
  try {
    const recherche = req.query.pdf || 'tous';
    const demanderLienDirect = req.query.direct === 'true';
    
    let resultats = [];
    let sourceUrl = '';
    let typeRecherche = '';

    // Déterminer le type de recherche
    if (recherche.toLowerCase().startsWith('cor math')) {
      // Corrections Mathématiques
      sourceUrl = SOURCES.correctionsMath;
      typeRecherche = 'Corrections Mathématiques série A';
      resultats = await scraperSection(sourceUrl);
      const terme = recherche.replace(/^cor math\s*/i, '').trim();
      resultats = filtrerResultats(resultats, terme);
    } else if (recherche.toLowerCase().startsWith('cor')) {
      // Corrections PC
      sourceUrl = SOURCES.correctionsPC;
      typeRecherche = 'Corrections PC série A';
      resultats = await scraperSection(sourceUrl);
      const terme = recherche.replace(/^cor\s*/i, '').trim();
      resultats = filtrerResultats(resultats, terme);
    } else if (recherche.toLowerCase().startsWith('math')) {
      // Sujets Mathématiques
      sourceUrl = SOURCES.sujetsMath;
      typeRecherche = 'Sujets Mathématiques série A';
      resultats = await scraperSection(sourceUrl);
      const terme = recherche.replace(/^math\s*/i, '').trim();
      resultats = filtrerResultats(resultats, terme);
    } else {
      // Sujets PC par défaut
      sourceUrl = SOURCES.sujetsPC;
      typeRecherche = 'Sujets PC série A';
      resultats = await scraperSection(sourceUrl);
      resultats = filtrerResultats(resultats, recherche === 'tous' ? '' : recherche);
    }

    // Obtenir les liens directs si demandé
    if (demanderLienDirect && resultats.length > 0) {
      for (let resultat of resultats) {
        const lienDirect = await obtenirLienDirectPDF(resultat.url_pdf);
        if (lienDirect) {
          resultat.lien_direct_pdf = lienDirect;
        }
      }
    }

    res.json({
      success: true,
      type: typeRecherche,
      source: sourceUrl,
      recherche: recherche,
      count: resultats.length,
      resultats: resultats
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Route de conversion HTML vers PDF
app.get('/convertir', async (req, res) => {
  const url = req.query.url;

  if (!url) {
    return res.status(400).json({
      success: false,
      error: 'URL manquante. Usage: /convertir?url=<url>'
    });
  }

  try {
    const browser = await puppeteer.launch({
      args: chromium.args,
      defaultViewport: chromium.defaultViewport,
      executablePath: await chromium.executablePath(),
      headless: chromium.headless,
    });

    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'networkidle0' });
    
    const pdf = await page.pdf({
      format: 'A4',
      printBackground: true
    });

    await browser.close();

    res.contentType('application/pdf');
    res.send(pdf);

  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Démarrage du serveur
app.listen(PORT, '0.0.0.0', () => {
  console.log(`✅ Serveur démarré sur le port ${PORT}`);
  console.log(`📚 API PDF Scraper EDUCMAD prête`);
});

module.exports = app;
