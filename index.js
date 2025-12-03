const express = require('express');
const axios = require('axios');
const cheerio = require('cheerio');

const app = express();
const PORT = process.env.PORT || 5000;

const BASE_URL = 'http://mediatheque.accesmad.org/educmad/course/view.php?id=819';

async function scrapePDFs(searchTerm = '') {
  try {
    const response = await axios.get(BASE_URL, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });
    
    const $ = cheerio.load(response.data);
    const pdfs = [];
    
    $('li.activity.modtype_resource').each((index, element) => {
      const titleElement = $(element).find('span.instancename');
      const linkElement = $(element).find('a.aalink');
      
      if (titleElement.length && linkElement.length) {
        let title = titleElement.clone().children('span.accesshide').remove().end().text().trim();
        
        const url = linkElement.attr('href');
        
        if (title && url) {
          pdfs.push({
            titre: title,
            url_pdf: url
          });
        }
      }
    });
    
    if (searchTerm) {
      const normalizedSearch = searchTerm.toLowerCase().trim();
      const searchWords = normalizedSearch.split(/\s+/).filter(word => word.length > 0);
      
      if (searchWords.includes('liste') || searchWords.includes('all') || searchWords.includes('tout') || searchWords.includes('tous')) {
        return pdfs;
      }
      
      return pdfs.filter(pdf => {
        const titleLower = pdf.titre.toLowerCase()
          .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        
        return searchWords.every(word => {
          const normalizedWord = word.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
          
          if (normalizedWord === 'pc' || normalizedWord === 'spc') {
            return titleLower.includes('physique') || titleLower.includes('pc') || titleLower.includes('spc');
          }
          
          return titleLower.includes(normalizedWord);
        });
      });
    }
    
    return pdfs;
  } catch (error) {
    console.error('Erreur lors du scraping:', error.message);
    throw error;
  }
}

app.get('/recherche', async (req, res) => {
  try {
    const searchTerm = req.query.pdf || '';
    const pdfs = await scrapePDFs(searchTerm);
    
    res.json({
      success: true,
      count: pdfs.length,
      recherche: searchTerm || 'tous',
      resultats: pdfs
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Erreur lors de la récupération des PDFs',
      message: error.message
    });
  }
});

app.get('/', (req, res) => {
  res.json({
    message: 'API Scraper PDF EDUCMAD',
    usage: '/recherche?pdf=<termes>',
    exemples: {
      'PDF specifique': '/recherche?pdf=PC A 2020',
      'Par annee': '/recherche?pdf=2019',
      'Tous les PDFs': '/recherche?pdf=PC A liste'
    }
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Serveur démarré sur le port ${PORT}`);
});

module.exports = app;
