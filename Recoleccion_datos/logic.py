import os
import requests
import pandas as pd
from PyPDF2 import PdfReader
import bibtexparser
import xml.etree.ElementTree as ET
import fitz  # PyMuPDF para extraer texto de PDFs
import time
import gc  # 🔹 Para liberar memoria cuando sea necesario
import xmltodict
import pandas as pd
from bs4 import BeautifulSoup

global contador
contador = 0

def download_pdf(pdf_url, temp_path='temp.pdf'):
    """Descarga un PDF desde la URL y lo guarda en un archivo temporal."""
    global contador  # Usamos una variable global para contar los errores

    try:
        response = requests.get(pdf_url, timeout=1)  # 🔹 Agregamos timeout para evitar bloqueos
        if response.status_code == 200 and response.content:  # 🔹 Verificamos que el contenido no esté vacío
            with open(temp_path, 'wb') as pdf_file:
                pdf_file.write(response.content)

            # 🔹 Verificar que el archivo realmente es un PDF válido
            if not temp_path.endswith('.pdf'):
                print(f"\n⚠️ Advertencia: '{temp_path}' podría no ser un PDF válido.")
                return None

            print(f"\n✅ PDF descargado correctamente: {temp_path}")
            
            # 🔹 Evitar sobrecarga en descargas
            time.sleep(0.5)  # 🔹 Agregar un pequeño retraso para evitar bloqueos del servidor
            
            return temp_path
        else:
            contador += 1
            print(f"\r⚠️ Error en la obtención de documento {contador}: {pdf_url}", end='', flush=True)
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error descargando PDF: {e}")
    return None

def is_valid_pdf(file_path):
    """Verifica si un archivo PDF es válido y puede abrirse."""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)  # Leer los primeros 4 bytes
        return header == b'%PDF'  # Un archivo PDF válido siempre comienza con %PDF
    except Exception:
        return False

def extract_text_from_pdf(pdf_path, remove_after_extract=False):
    """Extrae el texto de un archivo PDF con manejo de errores y verificación de validez."""
    if not os.path.exists(pdf_path):  
        print(f"❌ Error: El archivo PDF '{pdf_path}' no existe.")
        return None

    if not is_valid_pdf(pdf_path):  
        print(f"❌ Error: El archivo '{pdf_path}' no es un PDF válido.")
        return None

    try:
        doc = fitz.open(pdf_path)  
        if len(doc) == 0:  
            print(f"⚠️ Advertencia: El PDF '{pdf_path}' está vacío.")
            return None

        text = "\n".join([page.get_text("text") for page in doc])

        try:
            clean_text = text.encode('utf-8', errors='replace').decode('utf-8')
        except UnicodeEncodeError:
            clean_text = text  

        doc.close()
        gc.collect()

        if not clean_text.strip():
            print(f"⚠️ Advertencia: No se pudo extraer texto útil de '{pdf_path}'.")
            return None

        if remove_after_extract:
            os.remove(pdf_path)  # 🔥 Eliminar solo si el parámetro es True
        
        return clean_text
    except Exception as e:
        print(f"❌ Error extrayendo texto del PDF '{pdf_path}': {e}")
        return None

def clean_xml(xml_string):
    soup = BeautifulSoup(xml_string, "xml")
    for tag in soup.find_all(["fig", "table-wrap", "graphic", "inline-formula", "mml:math"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)

# Extrae metadatos de un archivo .bib y los devuelve como un diccionario.
def extract_metadata_from_bib(file_path):
    metadata = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as bibtex_file:
            bib_database = bibtexparser.load(bibtex_file)
            for entry in bib_database.entries:
                metadata['titulo'] = entry.get('title', 'No disponible')
                metadata['autor'] = entry.get('author', 'Desconocido')
                metadata['ano'] = entry.get('year', 'No disponible')
                metadata['abstract'] = entry.get('abstract', 'No disponible')
                metadata['url'] = entry.get('url', None)  # Extraer el campo 'url' del archivo .bib
    except Exception as e:
        print(f"Error reading BIB: {e}")
        return None
    return metadata

# Busca y procesa artículos en un repositorio local, extrayendo texto y metadatos.
def buscar_articulos_en_repositorio_local(directorio):
    articles_data = []
    try:
        for file_name in os.listdir(directorio):
            if file_name.endswith('.pdf'):
                base_name = os.path.splitext(file_name)[0]
                print(base_name)
                pdf_path = os.path.join(directorio, file_name)
                bib_path = os.path.join(directorio, base_name + '.bib')

                if os.path.exists(bib_path):
                    pdf_content = extract_text_from_pdf(pdf_path, remove_after_extract=False)
                    metadata = extract_metadata_from_bib(bib_path)
                    
                    if pdf_content and metadata:
                        article_info = {
                            'titulo': metadata.get('titulo', 'No disponible'),
                            'autor': metadata.get('autor', 'Desconocido'),
                            'link': metadata.get('url', 'No disponible'),  
                            'ano': metadata.get('ano', 'No disponible'),
                            'Texto': pdf_content,
                            'abstract': metadata.get('abstract', 'No disponible'),
                            'cita': generate_citation(metadata.get('autor', 'Desconocido'), metadata.get('titulo', 'No disponible'), metadata.get('ano', 'No disponible'))
                        }
                        articles_data.append(article_info)
    except Exception as e:
        print(f"Error processing local repository: {e}")
        return None

    return pd.DataFrame(articles_data)

# Genera una cita bibliográfica en formato de texto a partir de los autores, título y año.
def generate_citation(authors, title, year):
    authors_formatted = authors.split('; ')
    if len(authors_formatted) > 1:
        authors_str = ', '.join(authors_formatted[:-1]) + ', & ' + authors_formatted[-1]
    else:
        authors_str = authors_formatted[0]
    return f"{authors_str} ({year}). {title}."

# Verifica si un PDF está disponible en Unpaywall usando el DOI y devuelve la URL si está disponible.
# Verifica si un PDF está disponible en Unpaywall usando el DOI y devuelve la URL si está disponible.
def verificar_pdf_unpaywall(doi):
    global contador
    base_url = f"https://api.unpaywall.org/v2/{doi}"
    params = {'email': 'adrianlopez20000@hotmail.com'}
    
    try:
        response = requests.get(base_url, params=params)
        
        # Si la API responde con un código de error, lo registramos
        if response.status_code != 200:
            contador = contador + 1
            print(f"\rError optecion de documento {contador}", end='', flush=True)
            return None

        # Intentamos parsear la respuesta JSON
        data = response.json()

        # Si la respuesta no es un diccionario, algo salió mal
        if not isinstance(data, dict):
            contador = contador + 1
            print(f"\rError optecion de documento {contador}", end='', flush=True)
            return None

        # Verificamos si existe 'best_oa_location' antes de intentar acceder
        best_oa_location = data.get('best_oa_location', None)

        if best_oa_location and isinstance(best_oa_location, dict):
            return best_oa_location.get('url_for_pdf', None)
        else:
            contador = contador + 1
            print(f"\rError optecion de documento {contador}", end='', flush=True)
            return None

    except requests.exceptions.RequestException as e:
        contador = contador + 1
        print(f"\rError optecion de documento {contador}", end='', flush=True)
        return None
    except ValueError as e:
        contador = contador + 1
        print(f"\rError optecion de documento {contador}", end='', flush=True)
        return None

# Busca artículos en el Directorio de Revistas de Acceso Abierto (DOAJ) utilizando un nombre de artículo y cantidad deseada.
def buscar_articulos_en_doaj(nombre_articulo, cantidad):
    base_url = "https://doaj.org/api/v2/search/articles/"
    query = nombre_articulo
    params = {
        'pageSize': cantidad
    }
    try:
        response = requests.get(f"{base_url}{query}", params=params)
        if response.status_code == 200:
            data = response.json()
            articles_data = []
            for article in data['results']:
                title = article['bibjson']['title']
                authors = article['bibjson'].get('author', [])
                author_names = '; '.join([author['name'] for author in authors]) if authors else 'Desconocido'
                doi = article['bibjson']['identifier'][0]['id']
                pdf_url = verificar_pdf_unpaywall(doi)
                if pdf_url:
                    temp_pdf_path = download_pdf(pdf_url)
                    if temp_pdf_path:
                        content = extract_text_from_pdf(temp_pdf_path, remove_after_extract=True)
                        if content:
                            year = article['created_date'][:4]
                            citation = generate_citation(author_names, title, year)
                            article_info = {
                                'titulo': title,
                                'autor': author_names,
                                'link': pdf_url,
                                'ano': year,
                                'Texto': content,
                                'abstract': article['bibjson'].get('abstract', 'No disponible'),
                                'cita': citation
                            }
                            articles_data.append(article_info)
            return pd.DataFrame(articles_data)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching articles from DOAJ: {e}")
        return None

# Busca artículos en arXiv utilizando un nombre de artículo y cantidad deseada.
def buscar_articulos_en_arxiv(nombre_articulo, cantidad):
    """Obtiene artículos de arXiv con el texto completo."""
    base_url = "https://export.arxiv.org/api/query?"
    params = {
        'search_query': f"all:{nombre_articulo}",
        'start': 0,
        'max_results': cantidad
    }

    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.text
            articles_data = []
            root = ET.fromstring(data)

            for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                title = entry.find("{http://www.w3.org/2005/Atom}title").text
                authors = [author.find("{http://www.w3.org/2005/Atom}name").text for author in entry.findall("{http://www.w3.org/2005/Atom}author")]
                author_names = '; '.join(authors) if authors else 'Desconocido'
                pdf_url = entry.find("{http://www.w3.org/2005/Atom}id").text.replace("abs", "pdf") + ".pdf"
                year = entry.find("{http://www.w3.org/2005/Atom}published").text[:4]
                abstract = entry.find("{http://www.w3.org/2005/Atom}summary").text

                # ✅ Extraer solo el código del DOI en arXiv
                doi_code = f"10.48550/arXiv.{pdf_url.split('/')[-1].replace('.pdf', '')}"

                # Descargar y extraer texto del PDF
                temp_pdf_path = download_pdf(pdf_url)
                text_content = extract_text_from_pdf(temp_pdf_path, remove_after_extract=True) if temp_pdf_path else "No disponible"

                article_info = {
                    'titulo': title,
                    'autor': author_names,
                    'ano': year,
                    'abstract': abstract,
                    'Texto': text_content,  # ✅ Texto completo extraído del PDF
                    'link': pdf_url,
                    'cita': f"{author_names} ({year}). {title}. arXiv: {pdf_url}",
                }
                articles_data.append(article_info)

            return pd.DataFrame(articles_data)
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener artículos de arXiv: {e}")
        return None

def buscar_articulos_en_plos(nombre_articulo, cantidad):
    print("plos entro")
    """Obtiene artículos de PLOS con el texto completo desde el XML."""
    base_url = "https://api.plos.org/search"
    params = {
        'q': nombre_articulo,
        'rows': cantidad,
        'fl': "id,title,author,abstract"
    }

    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            articles_data = []

            for article in data['response']['docs']:
                title = article.get('title', 'No disponible')
                authors = article.get('author', [])
                author_names = '; '.join(authors) if authors else 'Desconocido'
                doi = article.get('id')  # DOI en PLOS ya es un código válido
                abstract = article.get('abstract', 'No disponible')
                article_url = f"https://journals.plos.org/plosone/article?id={doi}"

                # Obtener año desde el XML
                year = "No disponible"
                response_xml = requests.get(f"https://journals.plos.org/plosone/article/file?id={doi}&type=manuscript")
                
                # ✅ Extraer texto completo del XML
                text_content = "No disponible"
                if response_xml.status_code == 200:
                    xml_data = xmltodict.parse(response_xml.content)
                    try:
                        pub_dates = xml_data['article']['front']['article-meta'].get('pub-date', [])
                        if isinstance(pub_dates, list):
                            year = pub_dates[0].get('year', "No disponible")
                        else:
                            year = pub_dates.get('year', "No disponible")

                        # Extraer texto del XML
                        text_content = xml_data['article']['body']
                        if isinstance(text_content, dict):
                            text_content = xmltodict.unparse({'body': text_content}, pretty=True)
                        text_content = clean_xml(text_content)
                    except KeyError:
                        pass

                article_info = {
                    'titulo': title,
                    'autor': author_names,
                    'ano': year,
                    'abstract': abstract,
                    'Texto': text_content,  # ✅ Texto completo del XML
                    'link': article_url,
                    'cita': f"{author_names}. ({year}). {title}. PLOS ONE: {article_url}",
                }
                articles_data.append(article_info)

            return pd.DataFrame(articles_data)
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener artículos de PLOS: {e}")
        return None


def generarJsonTR(resultados):

    ruta_actual = os.getcwd()
    print("Ruta actual:", ruta_actual)

    # Lista de palabras clave
    palabras_clave = [
        "study", "analysis", "review", "assessment", "exploration", "examination",
        "investigation", "overview", "inquiry", "appraisal", "poll", "questionnaire",
        "Ccensus", "audit", "sampling", "feedback study", "literature review",
        "systematic review", "meta analysis", "synthesis", "comparative analysis","survey"
    ]

    # Función para encontrar palabras clave en el título
    def encontrar_palabras(titulo):
        titulo = titulo.lower()
        for palabra in palabras_clave:
            if palabra in titulo:
                return palabra  # Retorna la primera palabra encontrada
        return None

    # Aplicar la función a cada fila y filtrar solo las coincidencias
    df_resultado = resultados.copy()
    df_resultado["palabra_clave"] = df_resultado["titulo"].apply(encontrar_palabras)
    df_resultado = df_resultado.dropna()  # Elimina filas sin coincidencias

    # Si no se encontraron coincidencias, buscar en la carpeta "Repositorio local"
    if df_resultado.empty:
        directorio_relativo = "./DocSurvey"
        df_resultado = buscar_articulos_en_repositorio_local(directorio_relativo)

    # Si después de buscar en el repositorio local sigue vacío, mostrar mensaje
    if df_resultado.empty:
        print("No se encontraron artículos relevantes ni en el CSV ni en el repositorio local.")
    else:
        # Crear un código único basado en el autor y el año
        df_resultado["codigo"] = df_resultado.apply(
            lambda row: f"{row['autor'].split()[0]}_{row['ano']}", axis=1
        )
        # Ordenar por año (descendente) y luego por la longitud del título (ascendente)
        df_resultado = df_resultado.sort_values(by=["ano", "titulo"], ascending=[False, True])
        # Seleccionar los primeros 5 resultados
        df_resultado = df_resultado.head(5)
        # Guardar los resultados en un archivo JSON
        df_resultado.to_json("resultados_busquedaTR.json", orient="records", indent=9)

# Realiza una búsqueda de artículos con variaciones del nombre en múltiples repositorios (local, DOAJ, arXiv, PloXiv).
def buscar_articulos_con_variaciones(nombre_articulo, cantidad=20, repositorios=['doaj'], directorio_local=None):
    print("repositorio: ",repositorios)
    
    resultados = pd.DataFrame()

    if 'local' in repositorios and len(resultados) <= cantidad:
        print("local: ")
        local_result = buscar_articulos_en_repositorio_local(directorio_local)
        if local_result is not None:
            resultados = pd.concat([resultados, local_result], ignore_index=True)
            print("Catidad: ",cantidad)
            cantidad = cantidad - len(resultados)

    if 'plos' in repositorios and len(resultados) <= cantidad:
        print("plos: ")
        ploxiv_result = buscar_articulos_en_plos(nombre_articulo, cantidad)
        if ploxiv_result is not None:
            print(ploxiv_result["titulo"])
            resultados = pd.concat([resultados, ploxiv_result], ignore_index=True)
            print("Catidad: ",cantidad)
            cantidad = cantidad - len(resultados)


    if 'doaj' in repositorios and len(resultados) <= cantidad:
        print("doaj: ")
        doaj_result = buscar_articulos_en_doaj(nombre_articulo, cantidad)
        if doaj_result is not None:
            resultados = pd.concat([resultados, doaj_result], ignore_index=True)
            print("Catidad: ",cantidad)
            cantidad = cantidad - len(resultados)


    if 'arxiv' in repositorios and len(resultados) <= cantidad:
        print("arxiv: ")
        arxiv_result = buscar_articulos_en_arxiv(nombre_articulo, cantidad)
        if arxiv_result is not None:
            resultados = pd.concat([resultados, arxiv_result], ignore_index=True)

    
    if not resultados.empty:
        resultados = resultados.drop_duplicates(subset='titulo', keep='first')
    
    generarJsonTR(resultados)

    return resultados if not resultados.empty else None

