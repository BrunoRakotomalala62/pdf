const express = require('express');
const axios = require('axios');
const cheerio = require('cheerio');

const app = express();
const PORT = process.env.PORT || 5000;

const BASE_URL = 'http://mediatheque.accesmad.org/educmad/course/view.php?id=819';

async function getDirectPdfUrl(viewUrl) {
  try {
    const redirectUrl = viewUrl.includes('?') ? viewUrl + '&redirect=1' : viewUrl + '?redirect=1';
    const response = await axios.head(redirectUrl, {
      maxRedirects: 0,
      validateStatus: status => status >= 200 && status < 400,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    });
    
    if (response.headers.location) {
      return response.headers.location;
    }
    return null;
  } catch (error) {
    if (error.response && error.response.headers && error.response.headers.location) {
      return error.response.headers.location;
    }
    return null;
  }
}

async function scrapePDFs(searchTerm = '', getDirectLinks = false) {
  try {
    const response = await axios.get(BASE_URL, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });
    
    const $ = cheerio.load(response.data);
    const pdfs = [];
    
    $('li.activity.modtype_resource, li.activity.modtype_page').each((index, element) => {
      const titleElement = $(element).find('span.instancename');
      const linkElement = $(element).find('a.aalink');
      const isResource = $(element).hasClass('modtype_resource');
      
      if (titleElement.length && linkElement.length) {
        let title = titleElement.clone().children('span.accesshide').remove().end().text().trim();
        const url = linkElement.attr('href');
        
        if (title && url) {
          pdfs.push({
            titre: title,
            url_page: url,
            type: isResource ? 'pdf' : 'page',
            url_pdf: null
          });
        }
      }
    });
    
    if (getDirectLinks) {
      const pdfPromises = pdfs.map(async (pdf) => {
        if (pdf.type === 'pdf') {
          const directUrl = await getDirectPdfUrl(pdf.url_page);
          if (directUrl) {
            pdf.url_pdf = directUrl;
          }
        }
        return pdf;
      });
      
      await Promise.all(pdfPromises);
    }
    
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
    const getDirectLinks = req.query.direct === 'true' || req.query.direct === '1';
    const pdfs = await scrapePDFs(searchTerm, getDirectLinks);
    
    const formattedResults = pdfs.map(pdf => {
      const result = {
        titre: pdf.titre,
        type: pdf.type === 'pdf' ? 'PDF telechargeble' : 'Page HTML',
        url_page: pdf.url_page
      };
      
      if (pdf.url_pdf) {
        result.url_pdf_direct = pdf.url_pdf;
      }
      
      return result;
    });
    
    res.json({
      success: true,
      count: formattedResults.length,
      recherche: searchTerm || 'tous',
      info: "Utilisez &direct=true pour obtenir les liens PDF directs (plus lent)",
      resultats: formattedResults
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
    options: {
      'direct': 'Ajouter &direct=true pour obtenir les liens PDF directs'
    },
    exemples: {
      'PDF specifique': '/recherche?pdf=PC A 2020',
      'Avec lien direct': '/recherche?pdf=PC A 2020&direct=true',
      'Tous les PDFs': '/recherche?pdf=PC A liste'
    }
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Serveur démarré sur le port ${PORT}`);
});

module.exports = app;
