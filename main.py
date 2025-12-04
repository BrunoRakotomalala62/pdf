from flask import Flask, jsonify, request, Response
import requests
from bs4 import BeautifulSoup
import re
import io

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

BASE_URL = "http://mediatheque.accesmad.org/educmad/course/view.php?id=817"

def scrape_pdfs():
    try:
        response = requests.get(BASE_URL, timeout=30)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        pdfs = []
        
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if '.pdf' in href.lower() or 'resource' in href.lower():
                year_match = re.search(r'(19\d{2}|20\d{2})', text)
                year = year_match.group(1) if year_match else None
                
                serie = None
                if 'série A' in text or 'Serie A' in text or 'serie A' in text.lower():
                    serie = 'A'
                elif 'série C' in text or 'Serie C' in text or 'serie C' in text.lower():
                    serie = 'C'
                elif 'série D' in text or 'Serie D' in text or 'serie D' in text.lower():
                    serie = 'D'
                
                subject = None
                if 'math' in text.lower():
                    subject = 'Mathematiques'
                elif 'physique' in text.lower():
                    subject = 'Physique'
                elif 'svt' in text.lower() or 'science' in text.lower():
                    subject = 'SVT'
                elif 'français' in text.lower() or 'francais' in text.lower():
                    subject = 'Francais'
                elif 'anglais' in text.lower():
                    subject = 'Anglais'
                elif 'philo' in text.lower():
                    subject = 'Philosophie'
                elif 'histoire' in text.lower() or 'géo' in text.lower():
                    subject = 'Histoire-Geo'
                elif 'malagasy' in text.lower():
                    subject = 'Malagasy'
                
                if text and href:
                    full_url = href if href.startswith('http') else f"http://mediatheque.accesmad.org{href}"
                    
                    pdfs.append({
                        'titre': text,
                        'url': full_url,
                        'annee': year,
                        'serie': serie,
                        'matiere': subject
                    })
        
        return pdfs
    except Exception as e:
        return {'error': str(e)}

def get_page_content_as_text(url):
    try:
        response = requests.get(url, timeout=30)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content_div = soup.find('div', class_='region-content') or soup.find('div', id='region-main') or soup.find('div', class_='content')
        
        if content_div:
            text = content_div.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)
        
        start_marker = "Baccalauréat de l'enseignement général"
        start_idx = text.find(start_marker)
        if start_idx != -1:
            text = text[start_idx:]
        
        return text
    except Exception as e:
        return f"Erreur: {str(e)}"

@app.route('/')
def home():
    return jsonify({
        'message': 'API Scraper PDF Baccalauréat Madagascar',
        'endpoints': {
            '/pdfs': 'Liste tous les PDFs disponibles',
            '/recherche': 'Recherche avec filtres (pdf, serie, annee)',
            '/contenu': 'Récupère le contenu d\'une page (paramètre: url)'
        }
    })

@app.route('/pdfs')
def get_pdfs():
    pdfs = scrape_pdfs()
    return jsonify({
        'total': len(pdfs) if isinstance(pdfs, list) else 0,
        'source': BASE_URL,
        'pdfs': pdfs
    })

@app.route('/recherche')
def recherche():
    pdf_filter = request.args.get('pdf', '').lower()
    serie_filter = request.args.get('serie', '').upper()
    annee_filter = request.args.get('annee', '')
    
    pdfs = scrape_pdfs()
    
    if isinstance(pdfs, dict) and 'error' in pdfs:
        return jsonify(pdfs), 500
    
    resultats = []
    for pdf in pdfs:
        match = True
        
        if pdf_filter:
            titre_lower = pdf['titre'].lower() if pdf['titre'] else ''
            matiere_lower = (pdf['matiere'] or '').lower()
            if pdf_filter not in titre_lower and pdf_filter not in matiere_lower:
                match = False
        
        if serie_filter and pdf['serie'] != serie_filter:
            match = False
        
        if annee_filter and pdf['annee'] != annee_filter:
            match = False
        
        if match:
            resultats.append(pdf)
    
    return jsonify({
        'filtres': {
            'pdf': pdf_filter or None,
            'serie': serie_filter or None,
            'annee': annee_filter or None
        },
        'total': len(resultats),
        'resultats': resultats
    })

@app.route('/contenu')
def get_contenu():
    url = request.args.get('url', '')
    if not url:
        return jsonify({'error': 'Paramètre url requis'}), 400
    
    content = get_page_content_as_text(url)
    return jsonify({
        'url': url,
        'contenu': content
    })

@app.route('/telecharger/<path:pdf_url>')
def telecharger_pdf(pdf_url):
    try:
        if not pdf_url.startswith('http'):
            pdf_url = f"http://mediatheque.accesmad.org{pdf_url}"
        
        response = requests.get(pdf_url, timeout=60, stream=True)
        
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename=document.pdf'}
            )
        else:
            return jsonify({'error': f'Impossible de télécharger: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
