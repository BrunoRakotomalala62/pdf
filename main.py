from flask import Flask, jsonify, request, Response
import requests
from bs4 import BeautifulSoup
import re
import subprocess
import tempfile
import os
from urllib.parse import urlparse

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

BASE_URL = "http://mediatheque.accesmad.org/educmad/course/view.php?id=817"
ALLOWED_DOMAINS = ['mediatheque.accesmad.org', 'accesmad.org']

def is_allowed_url(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not domain:
            return False
        for allowed in ALLOWED_DOMAINS:
            if domain == allowed or domain.endswith('.' + allowed):
                return True
        return False
    except:
        return False

def check_wkhtmltopdf():
    try:
        result = subprocess.run(['wkhtmltopdf', '--version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False

WKHTMLTOPDF_AVAILABLE = check_wkhtmltopdf()

def resolve_pdf_url(resource_url):
    if not is_allowed_url(resource_url):
        return None, "URL non autorisée"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(resource_url, timeout=30, allow_redirects=True, headers=headers)
        response.encoding = 'utf-8'
        
        if 'application/pdf' in response.headers.get('Content-Type', ''):
            if not is_allowed_url(response.url):
                return None, "Redirection vers un domaine non autorisé"
            return response.url, None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        pluginfile_patterns = [
            r'(https?://mediatheque\.accesmad\.org[^"\']+pluginfile\.php[^"\']+\.pdf[^"\']*)',
            r'(https?://mediatheque\.accesmad\.org[^"\']+\.pdf[^"\']*)',
            r'(/pluginfile\.php[^"\']+\.pdf[^"\']*)'
        ]
        
        for pattern in pluginfile_patterns:
            match = re.search(pattern, response.text, re.I)
            if match:
                url = match.group(1)
                if url.startswith('/'):
                    url = f"http://mediatheque.accesmad.org{url}"
                if is_allowed_url(url):
                    return url, None
        
        object_tag = soup.find('object', {'data': re.compile(r'\.pdf', re.I)})
        if object_tag:
            data_url = object_tag.get('data')
            if data_url:
                if not data_url.startswith('http'):
                    data_url = f"http://mediatheque.accesmad.org{data_url}"
                if is_allowed_url(data_url):
                    return data_url, None
        
        embed_tag = soup.find('embed', {'src': re.compile(r'\.pdf', re.I)})
        if embed_tag:
            src_url = embed_tag.get('src')
            if src_url:
                if not src_url.startswith('http'):
                    src_url = f"http://mediatheque.accesmad.org{src_url}"
                if is_allowed_url(src_url):
                    return src_url, None
        
        iframe_tag = soup.find('iframe', {'src': re.compile(r'pluginfile\.php', re.I)})
        if iframe_tag:
            iframe_url = iframe_tag.get('src')
            if iframe_url:
                if not iframe_url.startswith('http'):
                    iframe_url = f"http://mediatheque.accesmad.org{iframe_url}"
                if is_allowed_url(iframe_url):
                    return iframe_url, None
        
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf', re.I))
        for link in pdf_links:
            href = link.get('href', '')
            if href:
                if not href.startswith('http'):
                    href = f"http://mediatheque.accesmad.org{href}"
                if is_allowed_url(href):
                    return href, None
        
        return None, "Aucun PDF trouvé dans cette page"
        
    except requests.exceptions.Timeout:
        return None, "Timeout lors de la connexion"
    except Exception as e:
        return None, str(e)

def scrape_pdfs():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(BASE_URL, timeout=30, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        pdfs = []
        
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if '.pdf' in href.lower() or 'resource' in href.lower() or 'mod/resource' in href:
                year_match = re.search(r'(19\d{2}|20\d{2})', text)
                year = year_match.group(1) if year_match else None
                
                serie = None
                text_lower = text.lower()
                if 'série a' in text_lower or 'serie a' in text_lower:
                    serie = 'A'
                elif 'série c' in text_lower or 'serie c' in text_lower:
                    serie = 'C'
                elif 'série d' in text_lower or 'serie d' in text_lower:
                    serie = 'D'
                
                subject = None
                if 'math' in text_lower:
                    subject = 'Mathematiques'
                elif 'physique' in text_lower:
                    subject = 'Physique'
                elif 'svt' in text_lower or 'science' in text_lower:
                    subject = 'SVT'
                elif 'français' in text_lower or 'francais' in text_lower:
                    subject = 'Francais'
                elif 'anglais' in text_lower:
                    subject = 'Anglais'
                elif 'philo' in text_lower:
                    subject = 'Philosophie'
                elif 'histoire' in text_lower or 'géo' in text_lower:
                    subject = 'Histoire-Geo'
                elif 'malagasy' in text_lower:
                    subject = 'Malagasy'
                
                if text and href:
                    full_url = href if href.startswith('http') else f"http://mediatheque.accesmad.org{href}"
                    
                    if is_allowed_url(full_url):
                        is_page = 'mod/page' in href or 'page/view' in href
                        
                        pdfs.append({
                            'titre': text,
                            'url': full_url,
                            'annee': year,
                            'serie': serie,
                            'matiere': subject,
                            'type': 'page' if is_page else 'pdf'
                        })
        
        return pdfs
    except Exception as e:
        return {'error': str(e)}

def get_page_content_for_pdf(url):
    if not is_allowed_url(url):
        return "URL non autorisée"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
        
        if not is_allowed_url(response.url):
            return "Redirection vers un domaine non autorisé"
        
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(['script', 'style', 'nav', 'header', 'footer']):
            script.decompose()
        
        content_div = soup.find('div', class_='region-content') or soup.find('div', id='region-main') or soup.find('div', class_='content')
        
        if content_div:
            text = content_div.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)
        
        start_marker = "Baccalauréat de l'enseignement général"
        alt_marker = "Baccalauréat"
        
        start_idx = text.find(start_marker)
        if start_idx == -1:
            start_idx = text.find(alt_marker)
        
        if start_idx != -1:
            text = text[start_idx:]
        
        return text
    except Exception as e:
        return f"Erreur: {str(e)}"

def create_pdf_from_content(content, title="Baccalauréat Madagascar"):
    if not WKHTMLTOPDF_AVAILABLE:
        return None, "wkhtmltopdf non disponible"
    
    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ text-align: center; margin-bottom: 30px; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; font-family: Arial, sans-serif; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <pre>{content}</pre>
</body>
</html>"""
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as html_file:
            html_file.write(html_template)
            html_path = html_file.name
        
        pdf_path = html_path.replace('.html', '.pdf')
        
        result = subprocess.run(
            ['wkhtmltopdf', '--quiet', '--encoding', 'utf-8', html_path, pdf_path],
            capture_output=True,
            timeout=60
        )
        
        os.unlink(html_path)
        
        if os.path.exists(pdf_path):
            return pdf_path, None
        return None, "Échec de la génération du PDF"
    except Exception as e:
        return None, str(e)

@app.route('/')
def home():
    return jsonify({
        'message': 'API Scraper PDF Baccalauréat Madagascar',
        'wkhtmltopdf_disponible': WKHTMLTOPDF_AVAILABLE,
        'endpoints': {
            '/pdfs': 'Liste tous les PDFs disponibles',
            '/recherche': 'Recherche avec filtres (pdf, serie, annee)',
            '/contenu': 'Récupère le contenu d\'une page (paramètre: url)',
            '/telecharger': 'Télécharge un PDF (paramètre: url)',
            '/convertir': 'Convertit une page en PDF (paramètre: url)'
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
    
    if not is_allowed_url(url):
        return jsonify({'error': 'URL non autorisée. Seuls les domaines accesmad.org sont acceptés.'}), 403
    
    content = get_page_content_for_pdf(url)
    return jsonify({
        'url': url,
        'contenu': content
    })

@app.route('/telecharger')
def telecharger_pdf():
    url = request.args.get('url', '')
    if not url:
        return jsonify({'error': 'Paramètre url requis'}), 400
    
    if not is_allowed_url(url):
        return jsonify({'error': 'URL non autorisée. Seuls les domaines accesmad.org sont acceptés.'}), 403
    
    try:
        pdf_url, error = resolve_pdf_url(url)
        
        if error:
            return jsonify({'error': error, 'url_originale': url}), 404
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(pdf_url, timeout=60, stream=True, headers=headers, allow_redirects=True)
        
        if not is_allowed_url(response.url):
            return jsonify({'error': 'Redirection vers un domaine non autorisé'}), 403
        
        content_type = response.headers.get('Content-Type', '')
        
        if 'application/pdf' in content_type or pdf_url.lower().endswith('.pdf'):
            filename = pdf_url.split('/')[-1].split('?')[0]
            if not filename.endswith('.pdf'):
                filename = 'document.pdf'
            
            return Response(
                response.content,
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        else:
            return jsonify({
                'error': 'Le fichier trouvé n\'est pas un PDF valide',
                'url_resolue': pdf_url,
                'content_type': content_type
            }), 415
                
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Timeout lors du téléchargement'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/convertir')
def convertir_page():
    url = request.args.get('url', '')
    if not url:
        return jsonify({'error': 'Paramètre url requis'}), 400
    
    if not is_allowed_url(url):
        return jsonify({'error': 'URL non autorisée. Seuls les domaines accesmad.org sont acceptés.'}), 403
    
    if not WKHTMLTOPDF_AVAILABLE:
        return jsonify({'error': 'La conversion PDF n\'est pas disponible sur ce serveur'}), 503
    
    try:
        content = get_page_content_for_pdf(url)
        
        year_match = re.search(r'(19\d{2}|20\d{2})', url)
        year = year_match.group(1) if year_match else ''
        title = f"Baccalauréat Madagascar {year}"
        
        pdf_path, error = create_pdf_from_content(content, title)
        
        if error:
            return jsonify({'error': error}), 500
        
        if pdf_path and os.path.exists(pdf_path):
            def generate():
                with open(pdf_path, 'rb') as f:
                    yield f.read()
                os.unlink(pdf_path)
            
            filename = f"bac_madagascar_{year}.pdf" if year else "bac_madagascar.pdf"
            
            return Response(
                generate(),
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        else:
            return jsonify({'error': 'Impossible de générer le PDF'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
