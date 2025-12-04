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
        
        content_div = None
        for selector in ['div.box.py-3.generalbox', 'div#region-main-box', 'div.region-content', 'div#region-main', 'div.content', 'section#region-main']:
            if '.' in selector:
                parts = selector.split('.')
                tag = parts[0]
                classes = parts[1:]
                content_div = soup.find(tag, class_=lambda x: x and all(c in x.split() for c in classes))
            elif '#' in selector:
                parts = selector.split('#')
                content_div = soup.find(parts[0], id=parts[1])
            else:
                content_div = soup.find(selector)
            if content_div:
                break
        
        if content_div:
            text = content_div.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)
        
        start_markers = [
            "Baccalauréat de l'enseignement général",
            "Baccalauréat de l'enseignement",
            "BACCALAURÉAT",
            "Baccalauréat"
        ]
        
        start_idx = -1
        for marker in start_markers:
            start_idx = text.find(marker)
            if start_idx != -1:
                break
        
        if start_idx != -1:
            text = text[start_idx:]
        
        end_markers = ["Modifié le:", "Dernière modification", "Navigation"]
        for end_marker in end_markers:
            end_idx = text.find(end_marker)
            if end_idx != -1:
                text = text[:end_idx]
        
        return text.strip()
    except Exception as e:
        return f"Erreur: {str(e)}"

def get_page_html_for_pdf(url):
    if not is_allowed_url(url):
        return None, "URL non autorisée"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
        
        if not is_allowed_url(response.url):
            return None, "Redirection vers un domaine non autorisé"
        
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        for link in soup.find_all('a'):
            link.unwrap() if link.string else link.decompose()
        
        content_div = None
        selectors = [
            ('div', {'class_': lambda x: x and 'generalbox' in x.split()}),
            ('div', {'id': 'region-main'}),
            ('section', {'id': 'region-main'}),
            ('div', {'class_': 'content'}),
        ]
        
        for tag, attrs in selectors:
            content_div = soup.find(tag, **attrs)
            if content_div:
                break
        
        if not content_div:
            content_div = soup.find('body')
        
        if content_div:
            html_content = str(content_div)
            
            start_markers = [
                "Baccalauréat de l'enseignement général",
                "Baccalauréat de l'enseignement",
                "BACCALAURÉAT",
                "Baccalauréat"
            ]
            
            for marker in start_markers:
                start_idx = html_content.find(marker)
                if start_idx != -1:
                    tag_start = html_content.rfind('<', 0, start_idx)
                    if tag_start != -1:
                        html_content = html_content[tag_start:]
                    break
            
            end_markers = ["Modifié le:", "Dernière modification", "Navigation"]
            for end_marker in end_markers:
                end_idx = html_content.find(end_marker)
                if end_idx != -1:
                    tag_end = html_content.find('>', end_idx)
                    if tag_end != -1:
                        html_content = html_content[:end_idx]
            
            return html_content, None
        
        return None, "Contenu non trouvé"
    except Exception as e:
        return None, str(e)

def format_content_to_html(content, title="Baccalauréat Madagascar"):
    lines = content.split('\n')
    formatted_lines = []
    
    exercise_pattern = re.compile(r'^(Exercice\s*\d+|EXERCICE\s*\d+)', re.IGNORECASE)
    problem_pattern = re.compile(r'^(Problème|PROBLÈME)', re.IGNORECASE)
    question_pattern = re.compile(r'^(\d+[\.\)]\s*|[a-z][\.\)]\s*)', re.IGNORECASE)
    points_pattern = re.compile(r'\((\d+(?:[,\.]\d+)?)\s*(?:pt|pts|points?)\)', re.IGNORECASE)
    header_keywords = ['Madagascar', 'Session', 'Série', 'mathematiques', 'MATHEMATIQUES', 'Mathématiques', 
                       'Physique', 'PHYSIQUE', 'Durée', 'DURÉE', 'Coefficient']
    
    in_table = False
    table_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            if in_table and table_lines:
                formatted_lines.append(build_table_html(table_lines))
                table_lines = []
                in_table = False
            formatted_lines.append('<div class="spacer"></div>')
            continue
        
        if exercise_pattern.match(line) or problem_pattern.match(line):
            if in_table and table_lines:
                formatted_lines.append(build_table_html(table_lines))
                table_lines = []
                in_table = False
            points = points_pattern.search(line)
            points_text = f' ({points.group(1)} points)' if points else ''
            clean_line = points_pattern.sub('', line).strip()
            formatted_lines.append(f'<h2 class="exercise">{clean_line}{points_text}</h2>')
            continue
        
        if any(keyword in line for keyword in header_keywords) and i < 15:
            formatted_lines.append(f'<p class="header-info">{line}</p>')
            continue
        
        if 'corrigé' in line.lower() and len(line) < 20:
            formatted_lines.append(f'<p class="corrige-link"><em>[{line}]</em></p>')
            continue
        
        if 'N.B.' in line or 'NB:' in line or 'NB :' in line:
            note_content = line.replace("N.B.", "").replace("NB:", "").replace("NB :", "").strip()
            formatted_lines.append(f'<div class="note"><strong>N.B. :</strong> {note_content}</div>')
            continue
        
        if looks_like_table_row(line):
            in_table = True
            table_lines.append(line)
            continue
        elif in_table and table_lines:
            formatted_lines.append(build_table_html(table_lines))
            table_lines = []
            in_table = False
        
        points = points_pattern.search(line)
        if points:
            points_text = f' <span class="points-inline">({points.group(1)} pts)</span>'
            clean_line = points_pattern.sub('', line).strip()
            if question_pattern.match(line):
                formatted_lines.append(f'<p class="question">{clean_line}{points_text}</p>')
            else:
                formatted_lines.append(f'<p>{clean_line}{points_text}</p>')
            continue
        
        if question_pattern.match(line):
            formatted_lines.append(f'<p class="question">{line}</p>')
            continue
        
        formatted_lines.append(f'<p>{line}</p>')
    
    if in_table and table_lines:
        formatted_lines.append(build_table_html(table_lines))
    
    return '\n'.join(formatted_lines)

def looks_like_table_row(line):
    parts = re.split(r'\s{2,}|\t', line)
    if len(parts) >= 3:
        numeric_count = sum(1 for p in parts if re.match(r'^[\d,\.\-]+$', p.strip()))
        return numeric_count >= 2
    return False

def build_table_html(lines):
    if not lines:
        return ''
    
    html = '<table class="data-table">'
    for i, line in enumerate(lines):
        parts = re.split(r'\s{2,}|\t', line)
        parts = [p.strip() for p in parts if p.strip()]
        
        if i == 0:
            html += '<tr class="table-header">'
            for part in parts:
                html += f'<th>{part}</th>'
            html += '</tr>'
        else:
            html += '<tr>'
            for part in parts:
                html += f'<td>{part}</td>'
            html += '</tr>'
    
    html += '</table>'
    return html

def create_pdf_from_content(content, title="Baccalauréat Madagascar"):
    if not WKHTMLTOPDF_AVAILABLE:
        return None, "wkhtmltopdf non disponible"
    
    formatted_content = format_content_to_html(content, title)
    
    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            margin: 2cm;
            size: A4;
        }}
        body {{
            font-family: 'Times New Roman', Times, serif;
            font-size: 12pt;
            line-height: 1.6;
            color: #000;
            max-width: 100%;
        }}
        .title {{
            text-align: center;
            font-size: 20pt;
            font-weight: bold;
            margin-bottom: 25px;
            border-bottom: 3px double #333;
            padding-bottom: 15px;
        }}
        .header-info {{
            text-align: center;
            font-size: 13pt;
            margin: 8px 0;
            font-weight: 500;
        }}
        .exercise {{
            font-size: 14pt;
            font-weight: bold;
            margin-top: 30px;
            margin-bottom: 15px;
            color: #000;
            border-left: 5px solid #444;
            background-color: #f0f0f0;
            padding: 10px 15px;
        }}
        .question {{
            margin: 12px 0 12px 25px;
            padding-left: 5px;
        }}
        .points-inline {{
            color: #555;
            font-style: italic;
            font-size: 10pt;
        }}
        .note {{
            background-color: #fffde7;
            border: 1px solid #ffc107;
            border-left: 5px solid #ffc107;
            padding: 12px 15px;
            margin: 20px 0;
        }}
        .corrige-link {{
            color: #888;
            font-size: 10pt;
            margin: 5px 0;
        }}
        .data-table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        .data-table th, .data-table td {{
            border: 1px solid #333;
            padding: 10px;
            text-align: center;
        }}
        .data-table .table-header {{
            background-color: #e0e0e0;
            font-weight: bold;
        }}
        p {{
            margin: 10px 0;
            text-align: justify;
        }}
        .spacer {{
            height: 10px;
        }}
    </style>
</head>
<body>
    <div class="title">{title}</div>
    {formatted_content}
</body>
</html>"""
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as html_file:
            html_file.write(html_template)
            html_path = html_file.name
        
        pdf_path = html_path.replace('.html', '.pdf')
        
        result = subprocess.run(
            ['wkhtmltopdf', '--quiet', '--encoding', 'utf-8', 
             '--page-size', 'A4',
             '--margin-top', '20mm',
             '--margin-bottom', '20mm',
             '--margin-left', '20mm',
             '--margin-right', '20mm',
             html_path, pdf_path],
            capture_output=True,
            timeout=60
        )
        
        os.unlink(html_path)
        
        if os.path.exists(pdf_path):
            return pdf_path, None
        return None, "Échec de la génération du PDF"
    except Exception as e:
        return None, str(e)

def create_pdf_from_html(html_content, title="Baccalauréat Madagascar"):
    if not WKHTMLTOPDF_AVAILABLE:
        return None, "wkhtmltopdf non disponible"
    
    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            margin: 2cm;
            size: A4;
        }}
        body {{
            font-family: 'Times New Roman', Times, serif;
            font-size: 12pt;
            line-height: 1.6;
            color: #000;
            max-width: 100%;
            padding: 0;
            margin: 0;
        }}
        .pdf-title {{
            text-align: center;
            font-size: 18pt;
            font-weight: bold;
            margin-bottom: 25px;
            border-bottom: 2px solid #333;
            padding-bottom: 15px;
        }}
        h1, h2, h3 {{
            color: #222;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #333;
            padding: 8px;
            text-align: center;
        }}
        th {{
            background-color: #e9e9e9;
            font-weight: bold;
        }}
        p {{
            margin: 10px 0;
            text-align: justify;
        }}
        .content {{
            padding: 10px;
        }}
    </style>
</head>
<body>
    <div class="pdf-title">{title}</div>
    <div class="content">
        {html_content}
    </div>
</body>
</html>"""
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as html_file:
            html_file.write(html_template)
            html_path = html_file.name
        
        pdf_path = html_path.replace('.html', '.pdf')
        
        result = subprocess.run(
            ['wkhtmltopdf', '--quiet', '--encoding', 'utf-8',
             '--page-size', 'A4',
             '--margin-top', '20mm',
             '--margin-bottom', '20mm',
             '--margin-left', '20mm',
             '--margin-right', '20mm',
             html_path, pdf_path],
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
            '/convertir': 'Convertit une page en PDF formaté (paramètres: url, mode=texte|capture)',
            '/capturer': 'Capture une page web en PDF image (paramètre: url)'
        },
        'modes_conversion': {
            'texte': 'Extrait le texte et le formate en PDF structuré (défaut)',
            'capture': 'Capture la page comme une image/screenshot en PDF'
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
            
            filename = f"bac_capture_{year}.pdf" if year else "bac_capture.pdf"
            
            return Response(
                generate(),
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        else:
            return jsonify({'error': 'Impossible de capturer la page'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/convertir')
def convertir_page():
    url = request.args.get('url', '')
    mode = request.args.get('mode', 'texte')
    
    if not url:
        return jsonify({'error': 'Paramètre url requis'}), 400
    
    if not is_allowed_url(url):
        return jsonify({'error': 'URL non autorisée. Seuls les domaines accesmad.org sont acceptés.'}), 403
    
    if not WKHTMLTOPDF_AVAILABLE:
        return jsonify({'error': 'La conversion PDF n\'est pas disponible sur ce serveur'}), 503
    
    try:
        year_match = re.search(r'(19\d{2}|20\d{2})', url)
        year = year_match.group(1) if year_match else ''
        
        if mode == 'capture' or mode == 'image':
            pdf_path, error = capture_page_as_pdf(url)
            filename = f"bac_capture_{year}.pdf" if year else "bac_capture.pdf"
        else:
            content = get_page_content_for_pdf(url)
            title = f"Baccalauréat Madagascar {year}"
            pdf_path, error = create_pdf_from_content(content, title)
            filename = f"bac_madagascar_{year}.pdf" if year else "bac_madagascar.pdf"
        
        if error:
            return jsonify({'error': error}), 500
        
        if pdf_path and os.path.exists(pdf_path):
            def generate():
                with open(pdf_path, 'rb') as f:
                    yield f.read()
                os.unlink(pdf_path)
            
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
