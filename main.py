from flask import Flask, jsonify, request, Response, redirect
import requests
from bs4 import BeautifulSoup
import re
import subprocess
import tempfile
import os
from urllib.parse import urlparse, quote, unquote
import unicodedata

app = Flask(__name__)

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

app.config['JSON_AS_ASCII'] = False

COURSES = {
    'mathematiques': {
        'id': 817,
        'name': 'Mathematiques',
        'serie': 'A',
        'sections': {'sujet': 1, 'correction': 2}
    },
    'physique': {
        'id': 819,
        'name': 'Physique',
        'serie': 'A',
        'sections': {'sujet': 1, 'correction': 2}
    },
    'hg_a': {
        'id': 132,
        'name': 'Histoire-Geo',
        'serie': 'A',
        'sections': {'sujet': 1, 'correction': 1}
    },
    'hg_cd': {
        'id': 132,
        'name': 'Histoire-Geo',
        'serie': 'C-D',
        'sections': {'sujet': 2, 'correction': 2}
    },
    'malagasy_a': {
        'id': 130,
        'name': 'Malagasy',
        'serie': 'A',
        'sections': {'sujet': 1, 'correction': 1}
    },
    'malagasy_cd': {
        'id': 130,
        'name': 'Malagasy',
        'serie': 'C-D',
        'sections': {'sujet': 2, 'correction': 2}
    },
    'malagasy_s': {
        'id': 130,
        'name': 'Malagasy',
        'serie': 'S',
        'sections': {'sujet': 3, 'correction': 3}
    },
    'malagasy_ose': {
        'id': 130,
        'name': 'Malagasy',
        'serie': 'OSE',
        'sections': {'sujet': 4, 'correction': 4}
    },
    'philosophie_a': {
        'id': 131,
        'name': 'Philosophie',
        'serie': 'A',
        'sections': {'sujet': 1, 'correction': 1}
    },
    'philosophie_cd': {
        'id': 131,
        'name': 'Philosophie',
        'serie': 'C-D',
        'sections': {'sujet': 2, 'correction': 2}
    },
    'philosophie_l': {
        'id': 131,
        'name': 'Philosophie',
        'serie': 'L',
        'sections': {'sujet': 3, 'correction': 3}
    },
    'francais_acd': {
        'id': 134,
        'name': 'Francais',
        'serie': 'A-C-D',
        'sections': {'sujet': 1, 'correction': 1}
    },
    'francais_l': {
        'id': 134,
        'name': 'Francais',
        'serie': 'L',
        'sections': {'sujet': 1, 'correction': 1}
    },
    'francais_s': {
        'id': 134,
        'name': 'Francais',
        'serie': 'S',
        'sections': {'sujet': 1, 'correction': 1}
    },
    'francais_ose': {
        'id': 134,
        'name': 'Francais',
        'serie': 'OSE',
        'sections': {'sujet': 1, 'correction': 1}
    },
    'svt_a': {
        'id': 821,
        'name': 'SVT',
        'serie': 'A',
        'sections': {'sujet': 1, 'correction': 2}
    }
}

BASE_COURSE_URL = "http://mediatheque.accesmad.org/educmad/course/view.php?id="
SECTION_SUJET = "&section=1"
SECTION_CORRECTION = "&section=2"
ALLOWED_DOMAINS = ['mediatheque.accesmad.org', 'accesmad.org']

PAGE_YEARS = ['1999', '2000', '2001', '2002', '2003', '2004', '2005', '2006', '2007', '2008', '2009', '2010', '2011', '2012']

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
    if 'série a-c-d' in text_lower or 'serie a-c-d' in text_lower or 'séries a-c-d' in text_lower or 'series a-c-d' in text_lower:
        return 'A-C-D'
    elif 'série acd' in text_lower or 'serie acd' in text_lower or 'séries acd' in text_lower or 'series acd' in text_lower:
        return 'A-C-D'
    elif 'série c-d' in text_lower or 'serie c-d' in text_lower or 'séries c-d' in text_lower or 'series c-d' in text_lower:
        return 'C-D'
    elif 'série cd' in text_lower or 'serie cd' in text_lower or 'séries cd' in text_lower or 'series cd' in text_lower:
        return 'C-D'
    elif 'série ose' in text_lower or 'serie ose' in text_lower or ' ose ' in text_lower:
        return 'OSE'
    elif 'série a' in text_lower or 'serie a' in text_lower or ' a ' in text_lower:
        return 'A'
    elif 'série c' in text_lower or 'serie c' in text_lower or ' c ' in text_lower:
        return 'C'
    elif 'série d' in text_lower or 'serie d' in text_lower or ' d ' in text_lower:
        return 'D'
    elif 'série l' in text_lower or 'serie l' in text_lower or ' l ' in text_lower:
        return 'L'
    elif 'série s' in text_lower or 'serie s' in text_lower or ' s ' in text_lower:
        return 'S'
    return None

def extract_subject(text):
    text_lower = text.lower()
    if 'physique' in text_lower or 'pc' in text_lower or 'spc' in text_lower:
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
    elif 'histo' in text_lower or 'géo' in text_lower or 'geo' in text_lower or 'hg' in text_lower:
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
            
            if '.pdf' in href.lower() or 'resource' in href.lower() or 'mod/resource' in href or 'mod/page' in href or 'page/view' in href:
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
            courses_to_scrape = []
            if serie_filter:
                serie_upper = serie_filter.upper()
                if serie_upper == 'A':
                    courses_to_scrape = ['hg_a']
                elif serie_upper in ['C', 'D', 'C-D']:
                    courses_to_scrape = ['hg_cd']
                else:
                    courses_to_scrape = ['hg_a', 'hg_cd']
            else:
                courses_to_scrape = ['hg_a', 'hg_cd']
            
            for course_key in courses_to_scrape:
                course = COURSES[course_key]
                pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
                if isinstance(pdfs, list):
                    all_pdfs.extend(pdfs)
        elif subject_lower == 'malagasy':
            courses_to_scrape = []
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
                else:
                    courses_to_scrape = ['malagasy_a', 'malagasy_cd', 'malagasy_s', 'malagasy_ose']
            else:
                courses_to_scrape = ['malagasy_a', 'malagasy_cd', 'malagasy_s', 'malagasy_ose']
            
            for course_key in courses_to_scrape:
                course = COURSES[course_key]
                pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
                if isinstance(pdfs, list):
                    all_pdfs.extend(pdfs)
        elif subject_lower == 'philosophie' or subject_lower == 'philo':
            courses_to_scrape = ['philosophie_a', 'philosophie_cd', 'philosophie_l']
            
            for course_key in courses_to_scrape:
                course = COURSES[course_key]
                pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
                if isinstance(pdfs, list):
                    all_pdfs.extend(pdfs)
        elif subject_lower == 'francais' or subject_lower == 'français':
            courses_to_scrape = []
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
                else:
                    courses_to_scrape = ['francais_acd', 'francais_l', 'francais_s', 'francais_ose']
            else:
                courses_to_scrape = ['francais_acd', 'francais_l', 'francais_s', 'francais_ose']
            
            for course_key in courses_to_scrape:
                course = COURSES[course_key]
                pdfs = scrape_course(course['id'], course['name'], course.get('sections'), course.get('serie'))
                if isinstance(pdfs, list):
                    all_pdfs.extend(pdfs)
        elif subject_lower == 'svt':
            courses_to_scrape = []
            if serie_filter:
                serie_upper = serie_filter.upper()
                if serie_upper == 'A':
                    courses_to_scrape = ['svt_a']
                else:
                    courses_to_scrape = ['svt_a']
            else:
                courses_to_scrape = ['svt_a']
            
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
        'matieres_disponibles': ['mathematiques', 'physique', 'svt', 'hg', 'malagasy', 'philosophie', 'francais'],
        'endpoints': {
            '/recherche': 'Recherche des sujets et corrections de bac',
            '/pdf/<id>': 'Télécharge un PDF directement (redirige vers le fichier)'
        },
        'parametres': {
            'pdf': 'Filtre par matière (mathematiques, physique, svt, hg, malagasy, philosophie, francais)',
            'serie': 'Filtre par série (A, C, D, L, S, OSE)',
            'annee': 'Filtre par année (1999 à 2023)',
            'type': 'Filtre par type (sujet ou correction)'
        },
        'exemples_mathematiques': {
            'Sujets maths série A': f'{base_url}/recherche?pdf=mathematiques&serie=A&type=sujet',
            'Corrections maths série A': f'{base_url}/recherche?pdf=mathematiques&serie=A&type=correction',
            'Correction maths série A 2023': f'{base_url}/recherche?pdf=mathematiques&serie=A&type=correction&annee=2023'
        },
        'exemples_physique': {
            'Sujets physique série A': f'{base_url}/recherche?pdf=physique&serie=A&type=sujet',
            'Corrections physique série A': f'{base_url}/recherche?pdf=physique&serie=A&type=correction',
            'Sujet physique série A 2019': f'{base_url}/recherche?pdf=physique&serie=A&type=sujet&annee=2019',
            'Correction physique série A 2019': f'{base_url}/recherche?pdf=physique&serie=A&type=correction&annee=2019'
        },
        'exemples_hg': {
            'Sujets HG série A': f'{base_url}/recherche?pdf=hg&serie=A&type=sujet',
            'Sujet HG série A 2019': f'{base_url}/recherche?pdf=hg&serie=A&type=sujet&annee=2019',
            'Sujets HG série C (ou D)': f'{base_url}/recherche?pdf=hg&serie=C&type=sujet',
            'Sujet HG série C 2019': f'{base_url}/recherche?pdf=hg&serie=C&type=sujet&annee=2019'
        },
        'exemples_malagasy': {
            'Sujets Malagasy série A': f'{base_url}/recherche?pdf=malagasy&serie=A&type=sujet',
            'Sujet Malagasy série A 2019': f'{base_url}/recherche?pdf=malagasy&serie=A&type=sujet&annee=2019',
            'Sujets Malagasy série C (ou D)': f'{base_url}/recherche?pdf=malagasy&serie=C&type=sujet',
            'Sujet Malagasy série C 2019': f'{base_url}/recherche?pdf=malagasy&serie=C&type=sujet&annee=2019',
            'Sujets Malagasy série S': f'{base_url}/recherche?pdf=malagasy&serie=S&type=sujet',
            'Sujet Malagasy série S 2022': f'{base_url}/recherche?pdf=malagasy&serie=S&type=sujet&annee=2022',
            'Sujets Malagasy série OSE': f'{base_url}/recherche?pdf=malagasy&serie=OSE&type=sujet',
            'Sujet Malagasy série OSE 2022': f'{base_url}/recherche?pdf=malagasy&serie=OSE&type=sujet&annee=2022'
        },
        'exemples_philosophie': {
            'Sujets Philosophie série A': f'{base_url}/recherche?pdf=philosophie&serie=A&type=sujet',
            'Sujet Philosophie série A 2019': f'{base_url}/recherche?pdf=philosophie&serie=A&type=sujet&annee=2019',
            'Sujets Philosophie série C (ou D)': f'{base_url}/recherche?pdf=philosophie&serie=C&type=sujet',
            'Sujet Philosophie série C 2019': f'{base_url}/recherche?pdf=philosophie&serie=C&type=sujet&annee=2019',
            'Sujets Philosophie série L': f'{base_url}/recherche?pdf=philosophie&serie=L&type=sujet',
            'Sujet Philosophie série L 2022': f'{base_url}/recherche?pdf=philosophie&serie=L&type=sujet&annee=2022'
        },
        'exemples_francais': {
            'Sujets Français série A': f'{base_url}/recherche?pdf=francais&serie=A&type=sujet',
            'Sujet Français série A 2019': f'{base_url}/recherche?pdf=francais&serie=A&type=sujet&annee=2019',
            'Sujets Français série C (ou D)': f'{base_url}/recherche?pdf=francais&serie=C&type=sujet',
            'Sujet Français série C 2019': f'{base_url}/recherche?pdf=francais&serie=C&type=sujet&annee=2019',
            'Sujets Français série L': f'{base_url}/recherche?pdf=francais&serie=L&type=sujet',
            'Sujet Français série L 2022': f'{base_url}/recherche?pdf=francais&serie=L&type=sujet&annee=2022',
            'Sujets Français série S': f'{base_url}/recherche?pdf=francais&serie=S&type=sujet',
            'Sujet Français série S 2023': f'{base_url}/recherche?pdf=francais&serie=S&type=sujet&annee=2023',
            'Sujets Français série OSE': f'{base_url}/recherche?pdf=francais&serie=OSE&type=sujet',
            'Sujet Français série OSE 2023': f'{base_url}/recherche?pdf=francais&serie=OSE&type=sujet&annee=2023'
        },
        'exemples_svt': {
            'Sujets SVT série A': f'{base_url}/recherche?pdf=svt&serie=A&type=sujet',
            'Corrections SVT série A': f'{base_url}/recherche?pdf=svt&serie=A&type=correction',
            'Sujet SVT série A 2019': f'{base_url}/recherche?pdf=svt&serie=A&type=sujet&annee=2019',
            'Correction SVT série A 2019': f'{base_url}/recherche?pdf=svt&serie=A&type=correction&annee=2019',
            'Sujet SVT série A 2023': f'{base_url}/recherche?pdf=svt&serie=A&type=sujet&annee=2023',
            'Correction SVT série A 2023': f'{base_url}/recherche?pdf=svt&serie=A&type=correction&annee=2023'
        },
        'notes': {
            'pdf_direct': 'Les années 2013-2023 sont des fichiers PDF directs',
            'page_capture': 'Les années 1999-2011 sont des pages HTML converties en PDF automatiquement',
            'serie_cd': 'Pour HG, Malagasy et Philosophie, les séries C et D partagent le même contenu',
            'serie_acd_francais': 'Pour Français, les séries A, C et D partagent le même contenu',
            'serie_s_ose': 'Pour Malagasy, les séries S et OSE ne contiennent que les années 2022-2023',
            'serie_l': 'Pour Philosophie, la série L ne contient que les années 2022-2023',
            'francais_series': 'Pour Français: séries A-C-D (1999-2023), L (2022), S (2023), OSE (2023)'
        },
        'utilisation': 'Faites une recherche, puis cliquez sur url_telechargement pour télécharger le PDF'
    })

@app.route('/recherche')
def recherche():
    pdf_filter = request.args.get('pdf', '').lower()
    serie_filter = request.args.get('serie', '').upper()
    annee_filter = request.args.get('annee', '')
    type_filter = request.args.get('type', '').lower()
    
    base_url = get_api_base_url()
    
    pdfs = scrape_all_pdfs(pdf_filter if pdf_filter else None, serie_filter if serie_filter else None)
    
    if isinstance(pdfs, dict) and 'error' in pdfs:
        return jsonify(pdfs), 500
    
    resultats = []
    for pdf in pdfs:
        match = True
        
        if pdf_filter:
            titre_lower = pdf['titre'].lower() if pdf['titre'] else ''
            matiere_lower = (pdf['matiere'] or '').lower()
            if pdf_filter == 'hg':
                if matiere_lower != 'histoire-geo' and 'histo' not in titre_lower and 'géo' not in titre_lower and 'geo' not in titre_lower:
                    match = False
            elif pdf_filter not in titre_lower and pdf_filter not in matiere_lower:
                match = False
        
        if serie_filter:
            pdf_serie = pdf['serie'] or ''
            if serie_filter in ['A', 'C', 'D']:
                if pdf_serie != serie_filter and pdf_serie != 'C-D' and pdf_serie != 'A-C-D':
                    match = False
            elif pdf_serie != serie_filter:
                match = False
        
        if annee_filter and pdf['annee'] != annee_filter:
            match = False
        
        if type_filter:
            if type_filter not in ['sujet', 'correction']:
                match = False
            elif pdf['type_doc'] != type_filter:
                match = False
        
        if match:
            annee = pdf['annee']
            url_source = pdf['url']
            titre = pdf['titre']
            
            id_match = re.search(r'id=(\d+)', url_source)
            resource_id = id_match.group(1) if id_match else None
            
            url_telechargement = f"{base_url}/pdf/{resource_id}" if resource_id else None
            
            resultats.append({
                'titre': titre,
                'annee': annee,
                'serie': pdf['serie'],
                'matiere': pdf['matiere'],
                'type': pdf['type_doc'],
                'format': pdf['format'],
                'id': resource_id,
                'url_telechargement': url_telechargement
            })
    
    resultats.sort(key=lambda x: (x['annee'] or '0000'), reverse=True)
    
    return jsonify({
        'filtres': {
            'pdf': pdf_filter or None,
            'serie': serie_filter or None,
            'annee': annee_filter or None,
            'type': type_filter or None
        },
        'total': len(resultats),
        'resultats': resultats
    })

def is_error_page(html_content):
    error_indicators = [
        'Identifiant de module de cours non valide',
        '<title>Erreur',
        'errorbox',
        'error-content'
    ]
    for indicator in error_indicators:
        if indicator in html_content:
            return True
    return False

@app.route('/pdf/<resource_id>')
def download_pdf(resource_id):
    if not resource_id or not resource_id.isdigit():
        return jsonify({'error': 'ID de ressource invalide'}), 400
    
    resource_url = f"http://mediatheque.accesmad.org/educmad/mod/resource/view.php?id={resource_id}"
    page_url = f"http://mediatheque.accesmad.org/educmad/mod/page/view.php?id={resource_id}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        error = None
        
        response = requests.get(resource_url, timeout=30, allow_redirects=True, headers=headers)
        response.encoding = 'utf-8'
        
        if 'application/pdf' in response.headers.get('Content-Type', ''):
            return redirect(response.url)
        
        resource_is_error = is_error_page(response.text)
        
        if not resource_is_error:
            pdf_url, error = resolve_pdf_url(resource_url)
            if pdf_url:
                return redirect(pdf_url)
        
        page_response = requests.get(page_url, timeout=30, allow_redirects=True, headers=headers)
        page_response.encoding = 'utf-8'
        page_is_valid = not is_error_page(page_response.text)
        
        if WKHTMLTOPDF_AVAILABLE:
            if page_is_valid:
                pdf_path, capture_error = capture_page_as_pdf(page_url)
            elif not resource_is_error:
                pdf_path, capture_error = capture_page_as_pdf(resource_url)
            else:
                return jsonify({'error': 'Ressource non trouvée', 'id': resource_id}), 404
            
            if pdf_path and os.path.exists(pdf_path):
                def generate():
                    with open(pdf_path, 'rb') as f:
                        yield f.read()
                    os.unlink(pdf_path)
                
                return Response(
                    generate(),
                    mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="bac_{resource_id}.pdf"'}
                )
            else:
                return jsonify({'error': capture_error or 'Échec de la conversion'}), 500
        
        return jsonify({'error': error or 'PDF non trouvé', 'id': resource_id}), 404
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Timeout lors de la connexion'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/page/<page_id>')
def download_page_as_pdf(page_id):
    if not page_id or not page_id.isdigit():
        return jsonify({'error': 'ID de page invalide'}), 400
    
    page_url = f"http://mediatheque.accesmad.org/educmad/mod/page/view.php?id={page_id}"
    
    if not WKHTMLTOPDF_AVAILABLE:
        return jsonify({'error': 'La conversion PDF n\'est pas disponible'}), 503
    
    try:
        pdf_path, error = capture_page_as_pdf(page_url)
        
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
                headers={'Content-Disposition': f'attachment; filename="bac_page_{page_id}.pdf"'}
            )
        else:
            return jsonify({'error': 'Impossible de capturer la page'}), 500
            
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
        
        if error or not pdf_url:
            return jsonify({'error': error or 'PDF non trouvé', 'url_originale': url}), 404
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
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
