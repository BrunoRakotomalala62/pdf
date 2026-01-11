from flask import Flask, jsonify, request, Response, redirect
import pdfkit
import requests
from bs4 import BeautifulSoup
import re
import subprocess
import tempfile
import os
from urllib.parse import urlparse, quote, unquote
import unicodedata
import threading
import time
from datetime import datetime

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL', '')
PING_INTERVAL = 840

def keep_alive():
    while True:
        try:
            time.sleep(PING_INTERVAL)
            response = requests.get(f"{RENDER_URL}/health", timeout=30)
            print(f"[Keep-Alive] Ping sent at {datetime.now().isoformat()} - Status: {response.status_code}")
        except Exception as e:
            print(f"[Keep-Alive] Ping failed at {datetime.now().isoformat()}: {e}")

def start_keep_alive():
    if os.environ.get('RENDER') or os.environ.get('RENDER_EXTERNAL_URL'):
        thread = threading.Thread(target=keep_alive, daemon=True)
        thread.start()
        print(f"[Keep-Alive] Auto-ping started for {RENDER_URL} (every {PING_INTERVAL}s)")

def clean_filename(titre):
    if not titre:
        return "document"
    titre = unquote(titre)
    titre = titre.replace('Fichier', '').replace('Page', '').strip()
    titre = unicodedata.normalize('NFD', titre)
    titre = ''.join(c for c in titre if unicodedata.category(c) != 'Mn')
    titre = re.sub(r'[^\w\s\-]', '', titre)
    titre = re.sub(r'\s+', '_', titre.strip())
    titre = re.sub(r'_+', '_', titre)
    titre = titre.strip('_')
    if len(titre) > 80:
        titre = titre[:80]
    return titre if titre else "document"

COURSES = {
    'mathematiques': {'id': 817, 'name': 'Mathematiques', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 2}},
    'physique': {'id': 819, 'name': 'Physique', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 2}},
    'hg_a': {'id': 132, 'name': 'Histoire-Geo', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 1}},
    'hg_cd': {'id': 132, 'name': 'Histoire-Geo', 'serie': 'C-D', 'sections': {'sujet': 2, 'correction': 2}},
    'malagasy_a': {'id': 130, 'name': 'Malagasy', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 1}},
    'malagasy_cd': {'id': 130, 'name': 'Malagasy', 'serie': 'C-D', 'sections': {'sujet': 2, 'correction': 2}},
    'malagasy_s': {'id': 130, 'name': 'Malagasy', 'serie': 'S', 'sections': {'sujet': 3, 'correction': 3}},
    'malagasy_ose': {'id': 130, 'name': 'Malagasy', 'serie': 'OSE', 'sections': {'sujet': 4, 'correction': 4}},
    'philosophie_a': {'id': 131, 'name': 'Philosophie', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 1}},
    'philosophie_cd': {'id': 131, 'name': 'Philosophie', 'serie': 'C-D', 'sections': {'sujet': 2, 'correction': 2}},
    'philosophie_l': {'id': 131, 'name': 'Philosophie', 'serie': 'L', 'sections': {'sujet': 3, 'correction': 3}},
    'francais_acd': {'id': 134, 'name': 'Francais', 'serie': 'A-C-D', 'sections': {'sujet': 1, 'correction': 1}},
    'francais_l': {'id': 134, 'name': 'Francais', 'serie': 'L', 'sections': {'sujet': 1, 'correction': 1}},
    'francais_s': {'id': 134, 'name': 'Francais', 'serie': 'S', 'sections': {'sujet': 1, 'correction': 1}},
    'francais_ose': {'id': 134, 'name': 'Francais', 'serie': 'OSE', 'sections': {'sujet': 1, 'correction': 1}},
    'svt_a': {'id': 821, 'name': 'SVT', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 2}},
    'anglais_a': {'id': 135, 'name': 'Anglais', 'serie': 'A', 'sections': {'sujet': 1, 'correction': 1}},
    'anglais_cd': {'id': 135, 'name': 'Anglais', 'serie': 'C-D', 'sections': {'sujet': 2, 'correction': 2}},
    'anglais_acd': {'id': 135, 'name': 'Anglais', 'serie': 'A-C-D', 'sections': {'sujet': 3, 'correction': 3}},
    'anglais_ose': {'id': 135, 'name': 'Anglais', 'serie': 'OSE', 'sections': {'sujet': 4, 'correction': 4}}
}

BASE_COURSE_URL = "http://mediatheque.accesmad.org/educmad/course/view.php?id="
ALLOWED_DOMAINS = ['mediatheque.accesmad.org', 'accesmad.org']

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
        if object_tag and hasattr(object_tag, 'get'):
            data_url = object_tag.get('data')
            if data_url and isinstance(data_url, str):
                if not data_url.startswith('http'):
                    data_url = f"http://mediatheque.accesmad.org{data_url}"
                if is_allowed_url(data_url):
                    return data_url, None
        embed_tag = soup.find('embed', {'src': re.compile(r'\.pdf', re.I)})
        if embed_tag and hasattr(embed_tag, 'get'):
            src_url = embed_tag.get('src')
            if src_url and isinstance(src_url, str):
                if not src_url.startswith('http'):
                    src_url = f"http://mediatheque.accesmad.org{src_url}"
                if is_allowed_url(src_url):
                    return src_url, None
        iframe_tag = soup.find('iframe', {'src': re.compile(r'pluginfile\.php', re.I)})
        if iframe_tag and hasattr(iframe_tag, 'get'):
            iframe_url = iframe_tag.get('src')
            if iframe_url and isinstance(iframe_url, str):
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

def detect_type_from_title(text):
    text_lower = text.lower()
    if 'corrigé' in text_lower or 'corrige' in text_lower or 'correction' in text_lower:
        return 'correction'
    elif 'énoncé' in text_lower or 'enonce' in text_lower or 'sujet' in text_lower:
        return 'sujet'
    return None

def extract_serie(text):
    text_lower = text.lower()
    if 'série a-c-d' in text_lower or 'serie a-c-d' in text_lower:
        return 'A-C-D'
    elif 'série c-d' in text_lower or 'serie c-d' in text_lower:
        return 'C-D'
    elif 'série ose' in text_lower or 'serie ose' in text_lower:
        return 'OSE'
    elif 'série a' in text_lower or 'serie a' in text_lower:
        return 'A'
    elif 'série c' in text_lower or 'serie c' in text_lower:
        return 'C'
    elif 'série d' in text_lower or 'serie d' in text_lower:
        return 'D'
    elif 'série l' in text_lower or 'serie l' in text_lower:
        return 'L'
    elif 'série s' in text_lower or 'serie s' in text_lower:
        return 'S'
    return None

def extract_subject(text):
    text_lower = text.lower()
    if 'physique' in text_lower or 'pc' in text_lower:
        return 'Physique'
    elif 'math' in text_lower:
        return 'Mathematiques'
    elif 'svt' in text_lower:
        return 'SVT'
    elif 'français' in text_lower or 'francais' in text_lower:
        return 'Francais'
    elif 'anglais' in text_lower:
        return 'Anglais'
    elif 'philo' in text_lower:
        return 'Philosophie'
    elif 'histo' in text_lower or 'géo' in text_lower or 'geo' in text_lower:
        return 'Histoire-Geo'
    elif 'malagasy' in text_lower:
        return 'Malagasy'
    return None

def clean_title(text):
    text = re.sub(r'\s*Fichier\s*$', '', text)
    text = re.sub(r'\s*Page\s*$', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def scrape_section(url, default_type, default_subject=None, default_serie=None):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, timeout=30, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        pdfs = []
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if '.pdf' in href.lower() or 'resource' in href.lower() or 'mod/resource' in href or 'mod/page' in href:
                clean_text = clean_title(text)
                year_match = re.search(r'(19\d{2}|20\d{2})', clean_text)
                year = year_match.group(1) if year_match else None
                serie = extract_serie(clean_text) or default_serie
                subject = extract_subject(clean_text) or default_subject
                doc_type = detect_type_from_title(clean_text) or default_type
                if clean_text and href:
                    full_url = href if href.startswith('http') else f"http://mediatheque.accesmad.org{href}"
                    if is_allowed_url(full_url):
                        is_page = 'mod/page' in href or 'page/view' in href
                        pdfs.append({
                            'titre': clean_text,
                            'url': full_url,
                            'annee': year,
                            'serie': serie,
                            'matiere': subject,
                            'type_doc': doc_type,
                            'format': 'page' if is_page else 'pdf'
                        })
        return pdfs
    except Exception as e:
        return {'error': str(e)}

def scrape_course(course_id, default_subject=None, sections=None, default_serie=None):
    all_pdfs = []
    if sections is None:
        sections = {'sujet': 1, 'correction': 2}
    sujet_section = sections.get('sujet', 1)
    correction_section = sections.get('correction', 2)
    sujets_url = f"{BASE_COURSE_URL}{course_id}&section={sujet_section}"
    sujets = scrape_section(sujets_url, 'sujet', default_subject, default_serie)
    if isinstance(sujets, list):
        all_pdfs.extend(sujets)
    if correction_section != sujet_section:
        corrections_url = f"{BASE_COURSE_URL}{course_id}&section={correction_section}"
        corrections = scrape_section(corrections_url, 'correction', default_subject, default_serie)
        if isinstance(corrections, list):
            all_pdfs.extend(corrections)
    return all_pdfs

def scrape_all_pdfs(subject_filter=None, serie_filter=None):
    all_pdfs = []
    if subject_filter:
        subject_lower = subject_filter.lower()
        if subject_lower == 'hg':
            courses_to_scrape = ['hg_a', 'hg_cd']
            if serie_filter:
                serie_upper = serie_filter.upper()
                if serie_upper == 'A':
                    courses_to_scrape = ['hg_a']
                elif serie_upper in ['C', 'D', 'C-D']:
                    courses_to_scrape = ['hg_cd']
            for course_key in courses_to_scrape:
                course = COURSES[course_key]
                pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
                if isinstance(pdfs, list):
                    all_pdfs.extend(pdfs)
        elif subject_lower == 'malagasy':
            courses_to_scrape = ['malagasy_a', 'malagasy_cd', 'malagasy_s', 'malagasy_ose']
            if serie_filter:
                serie_upper = serie_filter.upper()
                if serie_upper == 'A':
                    courses_to_scrape = ['malagasy_a']
                elif serie_upper in ['C', 'D', 'C-D']:
                    courses_to_scrape = ['malagasy_cd']
                elif serie_upper == 'S':
                    courses_to_scrape = ['malagasy_s']
                elif serie_upper == 'OSE':
                    courses_to_scrape = ['malagasy_ose']
            for course_key in courses_to_scrape:
                course = COURSES[course_key]
                pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
                if isinstance(pdfs, list):
                    all_pdfs.extend(pdfs)
        elif subject_lower in ['philosophie', 'philo']:
            for course_key in ['philosophie_a', 'philosophie_cd', 'philosophie_l']:
                course = COURSES[course_key]
                pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
                if isinstance(pdfs, list):
                    all_pdfs.extend(pdfs)
        elif subject_lower in ['francais', 'français']:
            courses_to_scrape = ['francais_acd', 'francais_l', 'francais_s', 'francais_ose']
            if serie_filter:
                serie_upper = serie_filter.upper()
                if serie_upper in ['A', 'C', 'D', 'A-C-D', 'ACD']:
                    courses_to_scrape = ['francais_acd']
                elif serie_upper == 'L':
                    courses_to_scrape = ['francais_l']
                elif serie_upper == 'S':
                    courses_to_scrape = ['francais_s']
                elif serie_upper == 'OSE':
                    courses_to_scrape = ['francais_ose']
            for course_key in courses_to_scrape:
                course = COURSES[course_key]
                pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
                if isinstance(pdfs, list):
                    all_pdfs.extend(pdfs)
        elif subject_lower == 'svt':
            course = COURSES['svt_a']
            pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
            if isinstance(pdfs, list):
                all_pdfs.extend(pdfs)
        elif subject_lower == 'anglais':
            courses_to_scrape = ['anglais_a', 'anglais_cd', 'anglais_acd', 'anglais_ose']
            if serie_filter:
                serie_upper = serie_filter.upper()
                if serie_upper == 'A':
                    courses_to_scrape = ['anglais_a']
                elif serie_upper in ['C', 'D', 'C-D', 'CD']:
                    courses_to_scrape = ['anglais_cd']
                elif serie_upper in ['A-C-D', 'ACD']:
                    courses_to_scrape = ['anglais_acd']
                elif serie_upper == 'OSE':
                    courses_to_scrape = ['anglais_ose']
            for course_key in courses_to_scrape:
                course = COURSES[course_key]
                pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
                if isinstance(pdfs, list):
                    all_pdfs.extend(pdfs)
        elif subject_lower in COURSES:
            course = COURSES[subject_lower]
            pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
            if isinstance(pdfs, list):
                all_pdfs.extend(pdfs)
        else:
            for course_key, course in COURSES.items():
                if subject_lower in course['name'].lower():
                    pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
                    if isinstance(pdfs, list):
                        all_pdfs.extend(pdfs)
    else:
        for course_key, course in COURSES.items():
            pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
            if isinstance(pdfs, list):
                all_pdfs.extend(pdfs)
    return all_pdfs

def capture_page_as_pdf(url):
    if not WKHTMLTOPDF_AVAILABLE:
        return None, "wkhtmltopdf non disponible sur ce serveur"
    try:
        # Configuration de pdfkit pour utiliser wkhtmltopdf
        config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
        
        # Options pour une capture propre
        options = {
            'page-size': 'A4',
            'margin-top': '10mm',
            'margin-right': '10mm',
            'margin-bottom': '10mm',
            'margin-left': '10mm',
            'encoding': "UTF-8",
            'no-outline': None,
            'quiet': ''
        }
        
        # Création d'un fichier temporaire pour le PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output:
            pdf_path = output.name
            
        # Conversion directe de l'URL en PDF via pdfkit
        pdfkit.from_url(url, pdf_path, configuration=config, options=options)
        
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            return pdf_path, None
        else:
            return None, "Le PDF généré est vide ou inexistant"
            
    except Exception as e:
        print(f"Erreur capture_page_as_pdf: {str(e)}")
        return None, str(e)


@app.route('/')
def index():
    base_url = get_api_base_url()
    return jsonify({
        "message": "API Baccalauréat Madagascar - Scraper de PDFs",
        "description": "API pour récupérer les sujets et corrections du Baccalauréat depuis mediatheque.accesmad.org",
        "endpoints": {
            "/": "Documentation de l'API",
            "/health": "Vérification de l'état du serveur",
            "/matieres": "Liste des matières disponibles",
            "/pdfs": "Récupérer tous les PDFs (paramètres: matiere, serie, type, annee)",
            "/pdf/<matiere>": "Récupérer les PDFs d'une matière spécifique",
            "/telecharger": "Télécharger un PDF (paramètre: url, titre)",
            "/capturer": "Capturer une page en PDF (paramètre: url, titre)"
        },
        "exemples": {
            "Tous les PDFs de Mathématiques": f"{base_url}/pdf/mathematiques",
            "PDFs de Physique série A": f"{base_url}/pdfs?matiere=physique&serie=A",
            "Sujets de Français 2020": f"{base_url}/pdfs?matiere=francais&type=sujet&annee=2020",
            "Liste des matières": f"{base_url}/matieres",
            "Télécharger un PDF": f"{base_url}/telecharger?url=http://mediatheque.accesmad.org/...",
            "État du serveur": f"{base_url}/health"
        },
        "matieres_disponibles": list(set(c['name'] for c in COURSES.values()))
    })

@app.route('/matieres')
def liste_matieres():
    matieres = {}
    for key, course in COURSES.items():
        name = course['name']
        if name not in matieres:
            matieres[name] = {'series': [], 'id': course['id']}
        if course.get('serie') and course['serie'] not in matieres[name]['series']:
            matieres[name]['series'].append(course['serie'])
    return jsonify({
        'matieres': matieres,
        'total': len(matieres)
    })

@app.route('/pdfs')
def get_pdfs():
    matiere = request.args.get('matiere', '')
    serie = request.args.get('serie', '')
    type_doc = request.args.get('type', '')
    annee = request.args.get('annee', '')
    pdfs = scrape_all_pdfs(matiere if matiere else None, serie if serie else None)
    if type_doc:
        pdfs = [p for p in pdfs if p.get('type_doc') == type_doc]
    if annee:
        pdfs = [p for p in pdfs if p.get('annee') == annee]
    base_url = get_api_base_url()
    for pdf in pdfs:
        pdf['url_telechargement'] = f"{base_url}/telecharger?url={quote(pdf['url'], safe='')}&titre={quote(pdf.get('titre', ''), safe='')}"
    return jsonify({
        'pdfs': pdfs,
        'total': len(pdfs),
        'filtres': {'matiere': matiere, 'serie': serie, 'type': type_doc, 'annee': annee}
    })

@app.route('/pdf/<matiere>')
def get_pdfs_by_matiere(matiere):
    serie = request.args.get('serie', '')
    type_doc = request.args.get('type', '')
    annee = request.args.get('annee', '')
    pdfs = scrape_all_pdfs(matiere, serie if serie else None)
    if type_doc:
        pdfs = [p for p in pdfs if p.get('type_doc') == type_doc]
    if annee:
        pdfs = [p for p in pdfs if p.get('annee') == annee]
    base_url = get_api_base_url()
    for pdf in pdfs:
        pdf['url_telechargement'] = f"{base_url}/telecharger?url={quote(pdf['url'], safe='')}&titre={quote(pdf.get('titre', ''), safe='')}"
    return jsonify({
        'pdfs': pdfs,
        'total': len(pdfs),
        'matiere': matiere,
        'filtres': {'serie': serie, 'type': type_doc, 'annee': annee}
    })

@app.route('/telecharger')
def telecharger_pdf():
    url = request.args.get('url', '')
    titre = request.args.get('titre', '')
    if not url:
        return jsonify({'error': 'Paramètre url requis'}), 400
    if not is_allowed_url(url):
        return jsonify({'error': 'URL non autorisée. Seuls les domaines accesmad.org sont acceptés.'}), 403
    try:
        pdf_url, error = resolve_pdf_url(url)
        
        # Si aucun PDF n'est trouvé, on tente une capture directe s'il s'agit d'une page
        if (error or not pdf_url) and ('mod/page' in url or 'page/view' in url):
            print(f"Tentative de capture directe pour: {url}")
            pdf_path, capture_error = capture_page_as_pdf(url)
            if not capture_error and pdf_path:
                with open(pdf_path, 'rb') as f:
                    pdf_content = f.read()
                os.unlink(pdf_path)
                
                filename = f"{clean_filename(titre)}.pdf" if titre else "capture.pdf"
                return Response(
                    pdf_content,
                    mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )
            else:
                return jsonify({'error': capture_error or 'Échec de la capture', 'url_originale': url}), 404

        if error or not pdf_url:
            return jsonify({'error': error or 'PDF non trouvé', 'url_originale': url}), 404
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(pdf_url, timeout=60, stream=True, headers=headers, allow_redirects=True)
        if not is_allowed_url(response.url):
            return jsonify({'error': 'Redirection vers un domaine non autorisé'}), 403
        content_type = response.headers.get('Content-Type', '')
        if 'application/pdf' in content_type or str(pdf_url).lower().endswith('.pdf'):
            if titre:
                filename = f"{clean_filename(titre)}.pdf"
            else:
                year_match = re.search(r'(19\d{2}|20\d{2})', url)
                year = year_match.group(1) if year_match else ''
                filename = f"bac_{year}.pdf" if year else "document.pdf"
            return Response(
                response.content,
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        else:
            return jsonify({'error': 'Le fichier trouvé n\'est pas un PDF valide', 'url_resolue': pdf_url}), 415
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Timeout lors du téléchargement'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/capturer')
def capturer_page():
    url = request.args.get('url', '')
    titre = request.args.get('titre', '')
    if not url:
        return jsonify({'error': 'Paramètre url requis'}), 400
    if not is_allowed_url(url):
        return jsonify({'error': 'URL non autorisée. Seuls les domaines accesmad.org sont acceptés.'}), 403
    if not WKHTMLTOPDF_AVAILABLE:
        return jsonify({'error': 'La capture PDF n\'est pas disponible sur ce serveur'}), 503
    try:
        pdf_path, error = capture_page_as_pdf(url)
        if error:
            return jsonify({'error': error}), 500
        if pdf_path and os.path.exists(pdf_path):
            def generate():
                with open(pdf_path, 'rb') as f:
                    yield f.read()
                os.unlink(pdf_path)
            if titre:
                filename = f"{clean_filename(titre)}.pdf"
            else:
                year_match = re.search(r'(19\d{2}|20\d{2})', url)
                year = year_match.group(1) if year_match else ''
                filename = f"bac_{year}.pdf" if year else "bac_capture.pdf"
            return Response(
                generate(),
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        else:
            return jsonify({'error': 'Impossible de capturer la page'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

import json

CACHE_FILE = 'cache_url_json.json'
DOWNLOAD_BASE_URL = "https://create-pdf-url.onrender.com/download"
DEFAULT_EMAIL = "monsieurbruno0@gmail.com"

def load_cache():
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"pdfs": []}

@app.route('/recherche')
def recherche():
    query = request.args.get('pdf', '').strip().lower()
    if not query:
        return jsonify({'error': 'Paramètre pdf requis. Exemple: /recherche?pdf=math 3'}), 400
    
    cache_data = load_cache()
    pdfs = cache_data.get('pdfs', [])
    
    resultats = []
    for pdf in pdfs:
        nom = pdf.get('nom', '')
        if query in nom.lower():
            url_papermark = pdf.get('url_papermark', '')
            url_telechargement = f"{DOWNLOAD_BASE_URL}?pdf={quote(url_papermark, safe='')}&email={quote(DEFAULT_EMAIL, safe='')}"
            resultats.append({
                'titre': nom,
                'url_telechargement': url_telechargement
            })
    
    return jsonify({'resultats': resultats})

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': 'API Baccalauréat Madagascar',
        'wkhtmltopdf_disponible': WKHTMLTOPDF_AVAILABLE
    }), 200

@app.route('/ping')
def ping():
    return jsonify({'status': 'pong', 'timestamp': datetime.now().isoformat()}), 200

start_keep_alive()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
