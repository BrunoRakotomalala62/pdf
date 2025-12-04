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

PAGE_YEARS = ['2000', '2002', '2003', '2005', '2006', '2007', '2008', '2009', '2011']

def get_api_base_url():
    return request.host_url.rstrip('/')

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
            
            if '.pdf' in href.lower() or 'resource' in href.lower() or 'mod/resource' in href or 'mod/page' in href or 'page/view' in href:
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

def capture_page_as_pdf(url):
    if not WKHTMLTOPDF_AVAILABLE:
        return None, "wkhtmltopdf non disponible"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, timeout=30, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        elements_to_remove = [
            'footer',
            'nav',
            'header',
            '.navbar',
            '#page-footer',
            '.footer',
            '.logininfo',
            '.modifiedinfo',
            '#page-header',
            '.drawer',
            '.usermenu',
            '.accesshide',
            '.skip-block',
            '.nav-item',
            '.breadcrumb',
            '#nav-drawer',
            '.secondary-navigation',
            '.primary-navigation',
            '.page-context-header',
            '[data-region="drawer"]',
        ]
        
        for selector in elements_to_remove:
            for element in soup.select(selector):
                element.decompose()
        
        for text in soup.find_all(string=re.compile(r'Modifié le:|Fourni par Moodle|Copyright.*Educmad|Contacter l\'assistance|connecté anonymement|conservation de données|Obtenir l\'app mobile', re.I)):
            parent = text.find_parent()
            if parent:
                parent.decompose()
        
        for a_tag in soup.find_all('a'):
            if a_tag.get('href', '').startswith(('javascript:', '#')) or 'Connexion' in a_tag.get_text():
                a_tag.decompose()
        
        content_div = None
        for selector in ['div.box.generalbox', 'div#region-main', 'section#region-main', '.course-content']:
            content_div = soup.select_one(selector)
            if content_div:
                break
        
        if content_div:
            html_content = str(content_div)
        else:
            body = soup.find('body')
            html_content = str(body) if body else str(soup)
        
        clean_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Times New Roman', Times, serif;
            font-size: 12pt;
            line-height: 1.5;
            padding: 20px;
            max-width: 100%;
            background: white;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
        }}
        td, th {{
            border: 1px solid #333;
            padding: 8px;
        }}
        .no-overflow {{
            overflow: visible !important;
        }}
        footer, nav, .footer, .navbar, .logininfo, .breadcrumb {{
            display: none !important;
        }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as html_file:
            html_file.write(clean_html)
            html_path = html_file.name
        
        pdf_path = html_path.replace('.html', '.pdf')
        
        result = subprocess.run(
            ['wkhtmltopdf', 
             '--quiet',
             '--encoding', 'utf-8',
             '--page-size', 'A4',
             '--margin-top', '15mm',
             '--margin-bottom', '15mm',
             '--margin-left', '15mm',
             '--margin-right', '15mm',
             '--enable-local-file-access',
             '--disable-smart-shrinking',
             '--zoom', '1.0',
             html_path, pdf_path],
            capture_output=True,
            timeout=120
        )
        
        os.unlink(html_path)
        
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            return pdf_path, None
        return None, "Échec de la capture de la page"
    except subprocess.TimeoutExpired:
        return None, "Timeout lors de la capture"
    except Exception as e:
        return None, str(e)

@app.route('/')
def home():
    base_url = get_api_base_url()
    return jsonify({
        'message': 'API Baccalauréat Madagascar - Téléchargement PDF',
        'endpoints': {
            '/recherche': 'Recherche et téléchargement des sujets de bac',
            '/capturer': 'Télécharge une page en PDF (capture)'
        },
        'exemples': {
            'Tous les maths série A': f'{base_url}/recherche?pdf=mathematiques&serie=A',
            'Maths série A année 2009': f'{base_url}/recherche?pdf=mathematiques&serie=A&annee=2009',
            'Physique série C': f'{base_url}/recherche?pdf=physique&serie=C'
        },
        'note': 'Les URLs retournées sont directement téléchargeables sur votre téléphone'
    })

@app.route('/recherche')
def recherche():
    pdf_filter = request.args.get('pdf', '').lower()
    serie_filter = request.args.get('serie', '').upper()
    annee_filter = request.args.get('annee', '')
    
    base_url = get_api_base_url()
    
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
            annee = pdf['annee']
            url_source = pdf['url']
            
            if annee in PAGE_YEARS or pdf['type'] == 'page':
                url_telechargement = f"{base_url}/capturer?url={url_source}"
            else:
                url_telechargement = f"{base_url}/telecharger?url={url_source}"
            
            resultats.append({
                'titre': pdf['titre'],
                'annee': annee,
                'serie': pdf['serie'],
                'matiere': pdf['matiere'],
                'url_telechargement': url_telechargement
            })
    
    return jsonify({
        'filtres': {
            'pdf': pdf_filter or None,
            'serie': serie_filter or None,
            'annee': annee_filter or None
        },
        'total': len(resultats),
        'resultats': resultats
    })

@app.route('/capturer')
def capturer_page():
    url = request.args.get('url', '')
    if not url:
        return jsonify({'error': 'Paramètre url requis'}), 400
    
    if not is_allowed_url(url):
        return jsonify({'error': 'URL non autorisée. Seuls les domaines accesmad.org sont acceptés.'}), 403
    
    if not WKHTMLTOPDF_AVAILABLE:
        return jsonify({'error': 'La capture PDF n\'est pas disponible sur ce serveur'}), 503
    
    try:
        year_match = re.search(r'(19\d{2}|20\d{2})', url)
        year = year_match.group(1) if year_match else ''
        
        pdf_path, error = capture_page_as_pdf(url)
        
        if error:
            return jsonify({'error': error}), 500
        
        if pdf_path and os.path.exists(pdf_path):
            def generate():
                with open(pdf_path, 'rb') as f:
                    yield f.read()
                os.unlink(pdf_path)
            
            filename = f"bac_maths_{year}.pdf" if year else "bac_capture.pdf"
            
            return Response(
                generate(),
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        else:
            return jsonify({'error': 'Impossible de capturer la page'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
            year_match = re.search(r'(19\d{2}|20\d{2})', url)
            year = year_match.group(1) if year_match else ''
            
            filename = f"bac_maths_{year}.pdf" if year else "document.pdf"
            
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
