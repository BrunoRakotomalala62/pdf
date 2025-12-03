const express = require('express');
const axios = require('axios');
const cheerio = require('cheerio');

const app = express();
const PORT = process.env.PORT || 5000;

const BASE_URL = 'http://mediatheque.accesmad.org/educmad/course/view.php?id=819';
const BASE_URL_CORRECTIONS = 'http://mediatheque.accesmad.org/educmad/course/view.php?id=819&section=2';
const BASE_URL_MATHS = 'http://mediatheque.accesmad.org/educmad/course/view.php?id=817&section=1';
const BASE_URL_MATHS_CORRECTIONS = 'http://mediatheque.accesmad.org/educmad/course/view.php?id=817&section=2';

const isVercel = process.env.VERCEL === '1' || process.env.VERCEL_ENV !== undefined;

let browser = null;

async function getBrowser() {
  if (!browser || !browser.isConnected()) {
    if (isVercel) {
      const chromium = require('@sparticuz/chromium-min');
      const puppeteerCore = require('puppeteer-core');
      
      browser = await puppeteerCore.launch({
        args: [
          ...chromium.args,
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--single-process',
          '--hide-scrollbars',
          '--disable-web-security'
        ],
        defaultViewport: chromium.defaultViewport,
        executablePath: await chromium.executablePath(
          'https://github.com/Sparticuz/chromium/releases/download/v121.0.0/chromium-v121.0.0-pack.tar'
        ),
        headless: chromium.headless,
        ignoreHTTPSErrors: true,
      });
    } else {
      const puppeteer = require('puppeteer');
      browser = await puppeteer.launch({
        headless: 'new',
        executablePath: '/nix/store/qa9cnw4v5xkxyip6mb9kxqfq1z4x2dx1-chromium-138.0.7204.100/bin/chromium',
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-gpu',
          '--disable-software-rasterizer'
        ]
      });
    }
  }
  return browser;
}

async function convertPageToPdf(pageUrl) {
  const browserInstance = await getBrowser();
  const page = await browserInstance.newPage();
  
  try {
    await page.goto(pageUrl, { 
      waitUntil: 'networkidle2',
      timeout: 30000
    });
    
    await page.evaluate(() => {
      const header = document.querySelector('#header, .navbar, nav');
      const footer = document.querySelector('#footer, footer');
      const sidebar = document.querySelector('.drawer, #nav-drawer');
      if (header) header.style.display = 'none';
      if (footer) footer.style.display = 'none';
      if (sidebar) sidebar.style.display = 'none';
    });
    
    const pdfBuffer = await page.pdf({
      format: 'A4',
      printBackground: true,
      margin: {
        top: '20mm',
        right: '15mm',
        bottom: '20mm',
        left: '15mm'
      }
    });
    
    return pdfBuffer;
  } finally {
    await page.close();
  }
}

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

async function scrapeCorrections(searchTerm = '', getDirectLinks = false) {
  try {
    const response = await axios.get(BASE_URL_CORRECTIONS, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });
    
    const $ = cheerio.load(response.data);
    const corrections = [];
    
    $('li.activity.modtype_resource, div.activity.modtype_resource').each((index, element) => {
      const linkElement = $(element).find('a.aalink');
      const titleElement = $(element).find('span.instancename');
      
      if (titleElement.length && linkElement.length) {
        let title = titleElement.clone().children('span.accesshide').remove().end().text().trim();
        const url = linkElement.attr('href');
        
        const titleLower = title.toLowerCase();
        if (title && url && (titleLower.includes('corrig') || titleLower.includes('correction'))) {
          corrections.push({
            titre: title,
            url_page: url,
            type: 'pdf',
            url_pdf: null
          });
        }
      }
    });
    
    if (getDirectLinks) {
      const pdfPromises = corrections.map(async (pdf) => {
        const directUrl = await getDirectPdfUrl(pdf.url_page);
        if (directUrl) {
          pdf.url_pdf = directUrl;
        }
        return pdf;
      });
      
      await Promise.all(pdfPromises);
    }
    
    if (searchTerm) {
      const normalizedSearch = searchTerm.toLowerCase().trim();
      const searchWords = normalizedSearch.split(/\s+/).filter(word => word.length > 0);
      
      if (searchWords.includes('liste') || searchWords.includes('all') || searchWords.includes('tout') || searchWords.includes('tous')) {
        return corrections;
      }
      
      return corrections.filter(pdf => {
        const titleLower = pdf.titre.toLowerCase()
          .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        
        return searchWords.every(word => {
          const normalizedWord = word.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
          
          if (normalizedWord === 'pc' || normalizedWord === 'spc') {
            return titleLower.includes('physique') || titleLower.includes('pc') || titleLower.includes('spc');
          }
          
          if (normalizedWord === 'a') {
            return titleLower.includes('serie a') || titleLower.includes('série a');
          }
          
          return titleLower.includes(normalizedWord);
        });
      });
    }
    
    return corrections;
  } catch (error) {
    console.error('Erreur lors du scraping des corrections:', error.message);
    throw error;
  }
}

async function scrapeMaths(searchTerm = '', getDirectLinks = false) {
  try {
    const response = await axios.get(BASE_URL_MATHS, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });
    
    const $ = cheerio.load(response.data);
    const maths = [];
    
    $('li.activity.modtype_resource, div.activity.modtype_resource').each((index, element) => {
      const linkElement = $(element).find('a.aalink');
      const titleElement = $(element).find('span.instancename');
      
      if (titleElement.length && linkElement.length) {
        let title = titleElement.clone().children('span.accesshide').remove().end().text().trim();
        const url = linkElement.attr('href');
        
        const titleLower = title.toLowerCase();
        if (title && url && (titleLower.includes('math') || titleLower.includes('bacc'))) {
          maths.push({
            titre: title,
            url_page: url,
            type: 'pdf',
            url_pdf: null
          });
        }
      }
    });
    
    $('li.activity.modtype_page, div.activity.modtype_page').each((index, element) => {
      const linkElement = $(element).find('a.aalink');
      const titleElement = $(element).find('span.instancename');
      
      if (titleElement.length && linkElement.length) {
        let title = titleElement.clone().children('span.accesshide').remove().end().text().trim();
        const url = linkElement.attr('href');
        
        const titleLower = title.toLowerCase();
        if (title && url && (titleLower.includes('math') || titleLower.includes('bacc'))) {
          maths.push({
            titre: title,
            url_page: url,
            type: 'page',
            url_pdf: null
          });
        }
      }
    });
    
    if (getDirectLinks) {
      const pdfPromises = maths.map(async (pdf) => {
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
        return maths;
      }
      
      return maths.filter(pdf => {
        const titleLower = pdf.titre.toLowerCase()
          .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        
        return searchWords.every(word => {
          const normalizedWord = word.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
          
          if (normalizedWord === 'a') {
            return titleLower.includes('serie a') || titleLower.includes('série a');
          }
          
          return titleLower.includes(normalizedWord);
        });
      });
    }
    
    return maths;
  } catch (error) {
    console.error('Erreur lors du scraping des maths:', error.message);
    throw error;
  }
}

async function scrapeMathsCorrections(searchTerm = '', getDirectLinks = false) {
  try {
    const response = await axios.get(BASE_URL_MATHS_CORRECTIONS, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });
    
    const $ = cheerio.load(response.data);
    const corrections = [];
    
    $('li.activity.modtype_resource, div.activity.modtype_resource').each((index, element) => {
      const linkElement = $(element).find('a.aalink');
      const titleElement = $(element).find('span.instancename');
      
      if (titleElement.length && linkElement.length) {
        let title = titleElement.clone().children('span.accesshide').remove().end().text().trim();
        const url = linkElement.attr('href');
        
        const titleLower = title.toLowerCase();
        if (title && url && (titleLower.includes('corrig') || titleLower.includes('math'))) {
          corrections.push({
            titre: title,
            url_page: url,
            type: 'pdf',
            url_pdf: null
          });
        }
      }
    });
    
    if (getDirectLinks) {
      const pdfPromises = corrections.map(async (pdf) => {
        const directUrl = await getDirectPdfUrl(pdf.url_page);
        if (directUrl) {
          pdf.url_pdf = directUrl;
        }
        return pdf;
      });
      
      await Promise.all(pdfPromises);
    }
    
    if (searchTerm) {
      const normalizedSearch = searchTerm.toLowerCase().trim();
      const searchWords = normalizedSearch.split(/\s+/).filter(word => word.length > 0);
      
      if (searchWords.includes('liste') || searchWords.includes('all') || searchWords.includes('tout') || searchWords.includes('tous')) {
        return corrections;
      }
      
      return corrections.filter(pdf => {
        const titleLower = pdf.titre.toLowerCase()
          .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        
        return searchWords.every(word => {
          const normalizedWord = word.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
          
          if (normalizedWord === 'a') {
            return titleLower.includes('serie a') || titleLower.includes('série a');
          }
          
          return titleLower.includes(normalizedWord);
        });
      });
    }
    
    return corrections;
  } catch (error) {
    console.error('Erreur lors du scraping des corrections maths:', error.message);
    throw error;
  }
}

app.get('/recherche', async (req, res) => {
  try {
    const searchTerm = req.query.pdf || '';
    const getDirectLinks = req.query.direct === 'true' || req.query.direct === '1';
    
    const normalizedSearch = searchTerm.toLowerCase().trim();
    const isMathsCorrection = normalizedSearch.startsWith('cor math ') || normalizedSearch.startsWith('cor math');
    const isCorrection = !isMathsCorrection && (normalizedSearch.startsWith('cor ') || (normalizedSearch.startsWith('cor') && normalizedSearch.length <= 3));
    const isMaths = normalizedSearch.startsWith('math ') || (normalizedSearch.startsWith('math') && normalizedSearch.length <= 4);
    
    let results;
    let searchTermForScraper = searchTerm;
    let searchType = 'sujets';
    
    if (isMathsCorrection) {
      searchTermForScraper = searchTerm.replace(/^cor\s*math\s*/i, '').trim();
      results = await scrapeMathsCorrections(searchTermForScraper, getDirectLinks);
      searchType = 'corrections_mathematiques';
    } else if (isCorrection) {
      searchTermForScraper = searchTerm.replace(/^cor\s*/i, '').trim();
      results = await scrapeCorrections(searchTermForScraper, getDirectLinks);
      searchType = 'corrections';
    } else if (isMaths) {
      searchTermForScraper = searchTerm.replace(/^math\s*/i, '').trim();
      results = await scrapeMaths(searchTermForScraper, getDirectLinks);
      searchType = 'mathematiques';
    } else {
      results = await scrapePDFs(searchTerm, getDirectLinks);
    }
    
    const baseUrl = `${req.protocol}://${req.get('host')}`;
    
    const formattedResults = results.map(pdf => {
      const result = {
        titre: pdf.titre,
        type: pdf.type === 'pdf' ? 'PDF telechargeble' : 'Page HTML (convertible en PDF)',
        url_page: pdf.url_page
      };
      
      if (pdf.url_pdf) {
        result.url_pdf_direct = pdf.url_pdf;
      }
      
      if (pdf.type === 'page') {
        result.url_convertir_pdf = `${baseUrl}/convertir?url=${encodeURIComponent(pdf.url_page)}`;
      }
      
      return result;
    });
    
    let infoMessage = "Pour les Pages HTML, utilisez url_convertir_pdf pour telecharger en PDF";
    if (searchType === 'corrections') {
      infoMessage = "Corrections du Bacc PC série A";
    } else if (searchType === 'mathematiques') {
      infoMessage = "Énoncés Bacc Mathématiques série A (1999-2022)";
    } else if (searchType === 'corrections_mathematiques') {
      infoMessage = "Corrections Bacc Mathématiques série A";
    }
    
    res.json({
      success: true,
      count: formattedResults.length,
      recherche: searchTerm || 'tous',
      type: searchType,
      info: infoMessage,
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

app.get('/convertir', async (req, res) => {
  try {
    const pageUrl = req.query.url;
    
    if (!pageUrl) {
      return res.status(400).json({
        success: false,
        error: 'URL manquante',
        usage: '/convertir?url=<url_de_la_page>'
      });
    }
    
    console.log(`Conversion en PDF: ${pageUrl}`);
    
    const pdfBuffer = await convertPageToPdf(pageUrl);
    
    const filename = pageUrl.includes('id=') 
      ? `educmad_${pageUrl.split('id=')[1]}.pdf`
      : 'document.pdf';
    
    const buffer = Buffer.from(pdfBuffer);
    
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.setHeader('Content-Length', buffer.length);
    
    res.end(buffer);
    
  } catch (error) {
    console.error('Erreur conversion PDF:', error.message);
    res.status(500).json({
      success: false,
      error: 'Erreur lors de la conversion en PDF',
      message: error.message
    });
  }
});

app.get('/', (req, res) => {
  res.json({
    message: 'API Scraper PDF EDUCMAD',
    routes: {
      '/recherche': 'Rechercher les PDFs (sujets PC, corrections PC, mathématiques, corrections mathématiques)',
      '/convertir': 'Convertir une page HTML en PDF'
    },
    exemples: {
      'Sujets_PC': {
        'PDF specifique': '/recherche?pdf=PC A 2020',
        'Avec lien direct': '/recherche?pdf=PC A 2023&direct=true',
        'Tous les PDFs': '/recherche?pdf=PC A liste'
      },
      'Corrections_PC': {
        'Correction specifique': '/recherche?pdf=cor PC A 2000',
        'Avec lien direct': '/recherche?pdf=cor PC A 2023&direct=true',
        'Toutes les corrections': '/recherche?pdf=cor PC A liste'
      },
      'Mathematiques': {
        'Math specifique': '/recherche?pdf=Math A 2000',
        'Avec lien direct': '/recherche?pdf=Math A 2022&direct=true',
        'Tous les Maths': '/recherche?pdf=Math A liste'
      },
      'Corrections_Mathematiques': {
        'Correction Math specifique': '/recherche?pdf=cor Math A 2014',
        'Avec lien direct': '/recherche?pdf=cor Math A 2023&direct=true',
        'Toutes les corrections Math': '/recherche?pdf=cor Math A liste'
      },
      'Convertir page': '/convertir?url=http://mediatheque.accesmad.org/educmad/mod/page/view.php?id=26053'
    }
  });
});

process.on('SIGTERM', async () => {
  if (browser) {
    await browser.close();
  }
  process.exit(0);
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Serveur démarré sur le port ${PORT}`);
});

module.exports = app;
