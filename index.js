const express = require('express');
const axios = require('axios');
const cheerio = require('cheerio');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 5000;

const RENDER_EXTERNAL_URL = process.env.RENDER_EXTERNAL_URL;
const PING_INTERVAL = 14 * 60 * 1000;

const BASE_URL = 'http://mediatheque.accesmad.org/educmad/course/view.php?id=819';
const BASE_URL_CORRECTIONS = 'http://mediatheque.accesmad.org/educmad/course/view.php?id=819&section=2';
const BASE_URL_MATHS = 'http://mediatheque.accesmad.org/educmad/course/view.php?id=817&section=1';
const BASE_URL_MATHS_CORRECTIONS = 'http://mediatheque.accesmad.org/educmad/course/view.php?id=817&section=2';

const isReplit = process.env.REPL_ID !== undefined || process.env.REPLIT !== undefined;
const isVercel = process.env.VERCEL === '1' || process.env.VERCEL_ENV !== undefined;

const pdfCache = new Map();
const PDF_CACHE_DURATION = 10 * 60 * 1000;

let persistentBrowser = null;
let browserLock = false;
let lastBrowserActivity = Date.now();
const BROWSER_IDLE_TIMEOUT = 5 * 60 * 1000;

function generatePdfId() {
  return crypto.randomBytes(8).toString('hex');
}

function cleanExpiredPdfs() {
  const now = Date.now();
  for (const [id, data] of pdfCache.entries()) {
    if (now - data.createdAt > PDF_CACHE_DURATION) {
      pdfCache.delete(id);
    }
  }
}

setInterval(cleanExpiredPdfs, 60000);

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForBrowserLock(maxWait = 60000) {
  const startTime = Date.now();
  while (browserLock) {
    if (Date.now() - startTime > maxWait) {
      throw new Error('Timeout en attente du navigateur');
    }
    await sleep(100);
  }
  browserLock = true;
}

function releaseBrowserLock() {
  browserLock = false;
  lastBrowserActivity = Date.now();
}

async function createBrowser() {
  const puppeteerCore = require('puppeteer-core');
  
  console.log('Création du navigateur...');
  console.log('Environnement: Replit=' + isReplit + ', Vercel=' + isVercel);
  
  if (isReplit) {
    return await puppeteerCore.launch({
      headless: 'new',
      executablePath: '/nix/store/qa9cnw4v5xkxyip6mb9kxqfq1z4x2dx1-chromium-138.0.7204.100/bin/chromium',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-extensions',
        '--disable-background-networking',
        '--no-first-run'
      ]
    });
  } else {
    const chromium = require('@sparticuz/chromium');
    
    chromium.setGraphicsMode = false;
    
    const executablePath = await chromium.executablePath();
    console.log('Chromium path:', executablePath);
    
    return await puppeteerCore.launch({
      args: chromium.args,
      defaultViewport: chromium.defaultViewport,
      executablePath: executablePath,
      headless: chromium.headless,
      ignoreHTTPSErrors: true,
    });
  }
}

async function getPersistentBrowser() {
  if (isVercel) {
    return await createBrowser();
  }
  
  if (persistentBrowser && persistentBrowser.isConnected()) {
    return persistentBrowser;
  }
  
  persistentBrowser = await createBrowser();
  
  persistentBrowser.on('disconnected', () => {
    console.log('Navigateur déconnecté');
    persistentBrowser = null;
  });
  
  console.log('Navigateur persistant créé avec succès');
  return persistentBrowser;
}

async function closeBrowserIfIdle() {
  if (persistentBrowser && !browserLock) {
    const idleTime = Date.now() - lastBrowserActivity;
    if (idleTime > BROWSER_IDLE_TIMEOUT) {
      console.log('Fermeture du navigateur inactif...');
      try {
        await persistentBrowser.close();
      } catch (e) { }
      persistentBrowser = null;
    }
  }
}

if (!isVercel) {
  setInterval(closeBrowserIfIdle, 60000);
}

async function convertPageToPdfBuffer(pageUrl) {
  await waitForBrowserLock();
  
  let browser = null;
  let page = null;
  const shouldCloseBrowser = isVercel;
  
  try {
    browser = await getPersistentBrowser();
    page = await browser.newPage();
    
    await page.setRequestInterception(true);
    page.on('request', (req) => {
      const resourceType = req.resourceType();
      if (['image', 'stylesheet', 'font', 'media'].includes(resourceType)) {
        req.abort();
      } else {
        req.continue();
      }
    });
    
    await page.goto(pageUrl, { 
      waitUntil: 'domcontentloaded',
      timeout: 25000
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
    if (page) {
      try { await page.close(); } catch (e) { }
    }
    if (shouldCloseBrowser && browser) {
      try { await browser.close(); } catch (e) { }
    }
    releaseBrowserLock();
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
    const startTime = Date.now();
    
    const pdfBuffer = await convertPageToPdfBuffer(pageUrl);
    
    const duration = Date.now() - startTime;
    console.log(`PDF généré en ${duration}ms`);
    
    const pdfId = generatePdfId();
    const filename = pageUrl.includes('id=') 
      ? `educmad_${pageUrl.split('id=')[1].split('&')[0]}.pdf`
      : 'document.pdf';
    
    pdfCache.set(pdfId, {
      buffer: Buffer.from(pdfBuffer),
      filename: filename,
      sourceUrl: pageUrl,
      createdAt: Date.now()
    });
    
    const baseUrl = `${req.protocol}://${req.get('host')}`;
    
    res.json({
      success: true,
      message: 'PDF converti avec succes',
      titre: filename.replace('.pdf', ''),
      type: 'PDF converti',
      url_source: pageUrl,
      url_pdf: `${baseUrl}/download/${pdfId}`,
      taille: Buffer.from(pdfBuffer).length,
      duree_conversion_ms: duration,
      expire_dans: '10 minutes'
    });
    
  } catch (error) {
    console.error('Erreur conversion PDF:', error.message);
    res.status(500).json({
      success: false,
      error: 'Erreur lors de la conversion en PDF',
      message: error.message
    });
  }
});

app.get('/download/:id', (req, res) => {
  const pdfId = req.params.id;
  const pdfData = pdfCache.get(pdfId);
  
  if (!pdfData) {
    return res.status(404).json({
      success: false,
      error: 'PDF non trouve ou expire',
      message: 'Le PDF demande n\'existe pas ou a expire. Veuillez le reconvertir.'
    });
  }
  
  res.setHeader('Content-Type', 'application/pdf');
  res.setHeader('Content-Disposition', `attachment; filename="${pdfData.filename}"`);
  res.setHeader('Content-Length', pdfData.buffer.length);
  
  res.end(pdfData.buffer);
});

app.get('/warmup', async (req, res) => {
  try {
    console.log('Warmup: initialisation du navigateur...');
    const browser = await getPersistentBrowser();
    const ready = browser !== null && browser.isConnected();
    if (isVercel) {
      await browser.close();
    }
    res.json({ 
      success: true, 
      message: 'Navigateur pret',
      browserReady: ready
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/', (req, res) => {
  res.json({
    message: 'API Scraper PDF EDUCMAD',
    environment: isReplit ? 'Replit' : (isVercel ? 'Vercel' : 'Other'),
    routes: {
      '/recherche': 'Rechercher les PDFs (sujets PC, corrections PC, mathematiques, corrections mathematiques)',
      '/convertir': 'Convertir une page HTML en PDF (retourne JSON avec URL de telechargement)',
      '/download/:id': 'Telecharger un PDF converti',
      '/warmup': 'Pre-charger le navigateur pour des conversions plus rapides'
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
      'Convertir_page': {
        'Convertir': '/convertir?url=http://mediatheque.accesmad.org/educmad/mod/page/view.php?id=26053',
        'Reponse': 'JSON avec url_pdf pour telecharger'
      }
    }
  });
});

app.get('/health', (req, res) => {
  res.status(200).json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    environment: isReplit ? 'Replit' : (isVercel ? 'Vercel' : 'Other'),
    browserReady: !isVercel && persistentBrowser !== null && persistentBrowser.isConnected(),
    browserLocked: browserLock,
    pdfsEnCache: pdfCache.size
  });
});

function startKeepAlive() {
  if (RENDER_EXTERNAL_URL) {
    console.log(`Auto-ping active pour: ${RENDER_EXTERNAL_URL}`);
    
    setInterval(async () => {
      try {
        const response = await axios.get(`${RENDER_EXTERNAL_URL}/health`);
        console.log(`[${new Date().toISOString()}] Ping OK - Status: ${response.status}`);
      } catch (error) {
        console.error(`[${new Date().toISOString()}] Ping erreur:`, error.message);
      }
    }, PING_INTERVAL);
    
    setTimeout(async () => {
      try {
        console.log('Auto-warmup du navigateur...');
        await getPersistentBrowser();
        console.log('Navigateur pret pour les conversions');
      } catch (error) {
        console.error('Erreur warmup:', error.message);
      }
    }, 5000);
  }
}

if (!isVercel) {
  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Serveur demarre sur le port ${PORT}`);
    startKeepAlive();
  });
}

process.on('SIGTERM', async () => {
  console.log('Arret du serveur...');
  if (persistentBrowser) {
    await persistentBrowser.close();
  }
  process.exit(0);
});

module.exports = app;
