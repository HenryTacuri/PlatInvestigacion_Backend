import os
import json
import re
from openai import OpenAI
import unicodedata
import pandas as pd

# Configuración de la API de OpenAI

client = None

def procesar_list_refs_paper(texto):
    print("Ejecutando procesar_list_refs_paper")
    pattern = re.compile(r'(?:listRefsPaper|\\textbf{listRefsPaper})\s*\[(.*?)\]')
    match = pattern.search(texto)
    if match:
        citas = [cita.strip() for cita in match.group(1).split(',')]
        texto = pattern.sub('', texto)
        texto = re.sub(r'\n\s*\n', '\n\n', texto).strip()
    else:
        citas = []
    return texto, citas

def summarize_section(client, general_title, section_title, articles, lineas_investigacion, areas_interes, max_words, model="gpt-4o mini", max_tokens=8000, temperature=0.7):
    texts = "\n\n".join([f"Texto: {article['Text']}\nCita: ({article['Citation']})\nCodigo:({article['Codigo']})" for article in articles])
    codes = "\n".join([article['Codigo'] for article in articles])
    
    prompt = (
        f"Como experto en investigación en {lineas_investigacion} y {areas_interes}, escribe un resumen para la sección {section_title} en inglés basado exclusivamente en el siguiente texto: {texts}. "
        f"\n\n**Instrucciones detalladas:**"
        f"\n1. **Citas obligatorias**:"
        f"\n   - Cada afirmación relevante debe incluir al menos tres citas en el formato \\cite{{...}} basándose en los códigos de referencia encontrados en Codigo:[]."
        f"\n   - Es obligatorio que el texto tenga al menos tres citas con su respectivo código."
        f"\n   - Solo deves poner los codigos que estan en Codigo:[]"
        f"\n\n2. **Formato del resumen**:"
        f"\n   - No inicies con un título de sección."
        f"\n   - Mantén un hilo conductor en todo el resumen."
        f"\n   - No incluyas nombres de autores dentro del texto. Solo usa \\cite{{...}} para referenciar."
        f"\n   - Usa un máximo de {max_words} palabras."
        f"\n\n3. **Lista de referencias usadas**:"
        f"\n   - Al final del resumen, incluye una lista llamada listRefsPaper con TODOS los códigos de referencia utilizados en orden de aparición."
        f"\n   - Ejemplo: listRefsPaper[E._2019, Jonathan_2023, Hafsa_2023]."
        f"\n   - Esta lista no debe tener formato LaTeX, solo texto plano."
        f"\n   - En la lista deven de estar todos los codigo que agregas al texto revisa y agrega a la lista"
        f"\n\n4. **Revisión final**:"
        f"\n   - Asegúrate de que el resumen tenga al menos tres citas bien distribuidas."
        f"\n   - Valida la gramática y la coherencia del texto."
        f"\n   - No uses caracteres especiales que puedan causar problemas en LaTeX."
        f"\n\nRecuerda: **Las citas son obligatorias y deben estar en el formato correcto**."
    )



    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    summary = response.choices[0].message.content.strip()
    return summary

def generate_section_summaries(json_data, lineas_investigacion, areas_interes, max_words, model="gpt-4o mini", max_tokens=1000, temperature=0.7):
    general_title = json_data.get("General_Title", "No Title")
    tema = json_data.get("Tema", {})
    
    todas_referencias = []
    referencias_usadas = set()
    secciones = []
    fundamentals_section = None

    for i, (section, articles) in enumerate(tema.items(), 1):
        if section.lower() == "related work":
            continue
        
        section_title = f"{section}"
        summary = summarize_section(client, general_title, section_title, articles, lineas_investigacion, areas_interes, max_words, model, max_tokens, temperature)
        
        texto_limpio, listCites = procesar_list_refs_paper(summary)
        nuevas_referencias = [cita for cita in listCites if cita not in referencias_usadas]
        referencias_usadas.update(nuevas_referencias)
        todas_referencias.extend(nuevas_referencias)

        section_data = {
            "titulo": section_title,
            "contenido": texto_limpio
        }

        if "fundamentals" in section_title.lower():
            fundamentals_section = section_data
        else:
            secciones.append(section_data)

    # Colocar la sección de fundamentos al inicio
    if fundamentals_section:
        secciones.insert(0, fundamentals_section)

    return secciones, todas_referencias

def generarTR(secciones, texto_completo, referencias_nuevas_secciones, contribucioneOriginalesLatex):
    with open("resultados_busquedaTR.json", "r", encoding="utf-8") as file:
        articulosTR = json.load(file)
    
    # Construir el prompt para la API de ChatGPT
    prompt = "Genera una sección de trabajo relacionado basada en los siguientes artículos. Para cada artículo, escribe un párrafo indicando su aporte y menciona su código al final del párrafo con \\cite{...}. Luego, compara con el siguiente texto completo y menciona qué es lo que se aporta.\n\n"

    # Agregar los artículos al prompt
    for articulo in articulosTR:
        prompt += f"- **Título:** {articulo['titulo']}\n"
        prompt += f"- **Autor:** {articulo['autor']}\n"
        prompt += f"- **Resumen:** {articulo['abstract']}\n"
        prompt += f"- **Código:** {articulo['codigo']}\n\n"

    # Agregar el texto completo para comparación
    prompt += f"Texto completo:\n\n'{texto_completo}'\n\n"
    prompt += "Ahora, identifica que es lo que aporta y crea la seccion para un peaper en ingles. no pongas titulos"

    # Llamar a la API de OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "Eres un asistente experto en procesamiento de lenguaje natural."},
                {"role": "user", "content": prompt}],
        max_tokens=15000
    )

    # Imprimir la respuesta generada
    related_work = response.choices[0].message.content.strip()
    related_work += "\n\n" + contribucioneOriginalesLatex

    section_data = {
        "titulo": "Related works and original contributions of the paper",
        "contenido": related_work
    }
    secciones.append(section_data)

    referenTR = [item["codigo"] for item in articulosTR]
    referenTR = [ref for ref in referenTR if ref not in referencias_nuevas_secciones]

    citas_bibtexTR = []
    for articulo in articulosTR:
        if articulo["codigo"] in referenTR:
            cita_bibtex = f"\\bibitem{{{articulo['codigo']}}} {articulo['cita']}."
            citas_bibtexTR.append(cita_bibtex)

    return secciones, citas_bibtexTR

def estructuraDoc(metodologia, secciones):
    prompt = (
        f"Generame un parrafo pequeno de la strucutura del documento."
        f"text :'{metodologia}', '{secciones}'"
    )
    
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        model="gpt-4o-mini",
        max_tokens=10000,
        temperature=0.7,
    )
    estructuraDocu = response.choices[0].message.content.strip()
    
    return estructuraDocu

def generate_introduction(json_data, client, general_title, texto_completo, lineas_investigacion, areas_interes, principales_contribuciones, metodologia, secciones, max_words, model, max_tokens=1000, temperature=0.7):
    print("1i")
    prompt = (
        f"Como experto en investigación y en las líneas de investigación: {lineas_investigacion} y las áreas de interés {areas_interes}, "
        f"y para un artículo en inglés con el título 'Survey of {general_title}'. "
        f"Específicamente, para la sección de Introducción, escribe esta sección de forma fluida, sin subsecciones, con la siguiente estructura: "
        f"1. Fundamentos principales del tema, 2. Un hook o motivación para atraer a los lectores, 3. Presentación del problema general y sub-problemas, "
        f"4. Justificación de la importancia para abordar estos problemas, 5. Soluciones más relevantes, 6. Breve descripción de nuestra metodología para desarrollo del survey del tema {general_title}, "
        f"Esto basándote solamente y exclusivamente en el siguiente texto que incluye las referencias respectivas {texto_completo}. "
        f"No incluyas al inicio como título el tema de la sección. Genera el texto con máximo {max_words} palabras y manteniendo un hilo conductor en toda la sección. "
        f"Incluye las citas en el lugar adecuado dentro del texto con formato para LaTeX, es decir, cada cita con \\cite asignando el código correspondiente de la referencia que encuentras dentro de Codigo:() asociado a la referencia. "
        f"No incluyas los nombres de autores en el texto. Por ejemplo, para citar indica: 'In \\cite ...' o 'as presented in \\cite'. "
        f"Valida la gramática y el hilo conductor de toda la sección, y verifica que el texto tenga un máximo de {max_words} palabras. "
        f"No incluyas caracteres especiales en el texto que puedan dañar la compilacion de mi latex y recuerda todo en ingles"
    )
    print("2i")
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        model="gpt-4o-mini",
        max_tokens=10000,
        temperature=temperature,
    )
    print("3i")
    introduction = response.choices[0].message.content.strip()
    print("4i")
    introduction += "\n\nThe key contributions of our study can be summarized as follows: \n\n" 
    print("5i")
    introduction += principales_contribuciones
    print("6i")
    print("general_title:", general_title)
    t = ""
    for i in range(2,len(secciones)-2):
        t += secciones[i]['titulo']+", "
    print("6i.1")
    estructuraDocu = "In the remainder of the document, the following is presented: The development methodology of this study, then, the evaluation in the field, the topics: "+t+" subsequently, the trends in "+general_title+", related works and original contributions, and finally, the conclusions."
    print("7i")
    introduction += "\n\n" + estructuraDocu
    print("8i")
    return introduction

def generate_conclusion(client, general_title, texto_completo, lineas_investigacion, areas_interes, max_words=250, model="gpt-4o mini", max_tokens=1000, temperature=0.7):
    
    prompt = (
        f"Como experto en investigación y en las líneas de investigación: {lineas_investigacion} y las áreas de interés {areas_interes}, "
        f"y para un artículo en inglés con el título {general_title}. "
        f"Específicamente, para la sección de Conclucion, escribe esta sección de forma fluida, sin subsecciones. "
        f"1. El texto es el siguiente: {texto_completo}. "
        f"2. de las the main contributions saca una Conclucion en un parrafo. "
        f"3. Valida la gramática , y verifica que el texto tenga un máximo de 250 palabras. "
        f"4. No agregues el titulo de la seccion al inicio de tu respuesta"
        f"5. No incluyas caracteres especiales en el texto que puedan dañar la compilacion de mi latex y recuerda todo en ingles"
    )

    
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    conclusion = response.choices[0].message.content.strip()
    return conclusion

def generate_keywords(client, general_title, texto_completo, lineas_investigacion, areas_interes, num_keywords=5, model="gpt-4o mini", max_tokens=1000, temperature=0.7):
    
    prompt = (
        f"Como experto en investigación y en las líneas de investigación: {lineas_investigacion} y las áreas de interés {areas_interes}, "
        f"y para un artículo en inglés con el título {general_title}. "
        f"Específicamente, para la sección de Keywords en donde solo escribirás {num_keywords} keywords tu respuesta será solo estos {num_keywords} como ejemplo 'palabra1, palabra2, palabra3, ..., palabra{num_keywords}'. "
        f"El texto es el siguiente: {texto_completo}. "
        f"Los mismos que podrán ser unigramas, bigramas o trigramas. "
        f"No agregues el título de la sección al inicio de tu respuesta, únicamente las {num_keywords} palabras."
        f"No incluyas caracteres especiales en el texto que puedan dañar la compilación de mi LaTeX y recuerda escribir todo en inglés."
    )
    
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    keywords = response.choices[0].message.content.strip()
    return keywords


def generate_abstract(client, general_title, texto_completo, lineas_investigacion, areas_interes, max_words=150, model="gpt-4o mini", max_tokens=1000, temperature=0.7):
    
    prompt = (
        f"Como experto en investigación y en las líneas de investigación: {lineas_investigacion} y las áreas de interés {areas_interes}, "
        f"y para un artículo en inglés con el título {general_title}. "
        f"Específicamente, para la sección de Abstract, escribe esta sección de forma fluida, sin subsecciones. "
        f"1. El texto es el siguiente: {texto_completo}. "
        f"2. Valida la gramática , y verifica que el texto tenga un máximo de 250 palabras. "
        f"3. No agregues el titulo de la seccion al inicio de tu respuesta"
        f"4. No incluyas caracteres especiales en el texto que puedan dañar la compilacion de mi latex y recuerda todo en ingles"
    )

    
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    abstract = response.choices[0].message.content.strip()
    return abstract

def combinar_referencias(*listas_de_referencias):
    todas_referencias = set()
    for lista in listas_de_referencias:
        todas_referencias.update(lista)
    return list(todas_referencias)

def generar_bibtex(json_data, referencias):
    bibitems = []
    
    for codigo in referencias:
        cita = None
        for section in json_data["Tema"].values():
            for articulo in section:
                if articulo["Codigo"] == codigo:
                    cita = articulo["Citation"]
                    break
            if cita:
                break
        if cita:
            cita_sin_tildes = eliminar_tildes(cita)
            bibitem = f"\\bibitem{{{codigo}}} {cita_sin_tildes}"
            bibitems.append(bibitem)
    
    return bibitems

def eliminar_tildes(texto):
    texto_normalizado = unicodedata.normalize('NFD', texto)
    texto_sin_tildes = re.sub(r'[\u0300-\u036f]', '', texto_normalizado)
    texto_sin_especiales = re.sub(r'[^\x00-\x7F]+', '', texto_sin_tildes)
    return texto_sin_especiales

def escapado_latex(texto):
    texto = texto.replace('\\', '\\\\').replace('$', '\\$')
    texto = texto.replace('&', r'\&')
    texto = texto.replace('-', r'\textendash{}')
    return texto

def escapado_latex2(texto):
    texto = texto.replace('&', r'\&')
    return texto

def escapado_bibliografia(texto):
    return texto.replace('&', r'\&')

def nuevoTitulo(texto, general_title):
    print("chatGPT new Tema", general_title)
    prompt = (
        f"genera una nuevo titulo en inglés de 3 palabras que esté muy relacionada con el texto proporcionado y tenga relacion con el tema del peaper '{general_title}'. "
        f"Texto en el que te debes basar por completo para el etiquetado: '{texto}'"
        f" Respondeme unicamente la etiqueta sin caracteres especiales ni nada por el estilo"
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()
    
def genrarNuevosTitulos(secciones, general_title):
    print("Generando Nuevos Titulos")
    for i, seccion in enumerate(secciones[3:], start=3):  # Comienza desde el índice 2
        newtitulo = nuevoTitulo(seccion['contenido'], general_title)
        print(newtitulo)
        secciones[i]['titulo'] = newtitulo
    return secciones

def latexPrinContribuciones(principales_contribuciones):
        prompt = (
            f"""
            Translate the following text from Spanish to English and format it as a LaTeX list using `\\begin{{itemize}}` and `\\item` for each contribution. 
            Ensure that the main contribution titles are in bold using `\\textbf{{}}`. The output should be in LaTeX format only, without additional explanations.
            
            Text:
            \"\"\"
            {principales_contribuciones}
            \"\"\"
            
            Expected output format:
            \"\"\"
            \\begin{{itemize}}d
                \\item \\textbf{{[Translated Title 1]}}: [Translated Description 1].
                \\item \\textbf{{[Translated Title 2]}}: [Translated Description 2].
                \\item \\textbf{{[Translated Title 3]}}: [Translated Description 3].
                \\item \\textbf{{[Translated Title 4]}}: [Translated Description 4].
                \\item \\textbf{{[Translated Title 5]}}: [Translated Description 5].
            \\end{{itemize}}
            \"\"\"
            """
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            n=1,
            stop=None,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

def generateOriginalContri(secciones):
    
    prompt = (
        f"Genremae un pequeno parrafo de una 25 palabras no mas que comience con Provides a comprehensive survey on... y completa con un resumen muy corto de lo siguiente: '{secciones}'"
        f"\n  es parrafo es para la seccion de contribuciones originales de un peaper, solo dame el parrafo nada mas y en ingles"
        f"\n  recuerda no deve de tener mas de 25 palabras"
    )
    
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        model="gpt-4o-mini",
        max_tokens=10000,
        temperature=0.7,
    )
    oriCon = response.choices[0].message.content.strip()
    
    return oriCon

def generateOriginalContri2(secciones):
    
    prompt = (
        f"Genremae un pequeno parrafo de manera general no tecnico de 25 palabras no mas por cada una de las secciones: '{secciones}' en toltal '{len(secciones)}' una por cada seccion"
        f"\n  los parrafos son para la seccion de contribuciones originales de un peaper, solo dame los parrafos no numerados nada mas"
        f"\n  comienza por el titulo dentro del mismo parrafo no como titulo y lo que aporta por ejemplo Fundamentals of Brain Cancer Deep Learning ..."
        f"\n  no es nesesario que tengan relacion entre los parrafos y debe de estar en ingles"
        f"\n  recuerda no deve de tener mas de 25 palabras"
    )
    
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        model="gpt-4o-mini",
        max_tokens=10000,
        temperature=0.7,
    )
    oriCon2 = response.choices[0].message.content.strip()
    
    return oriCon2

def latexOrigContribuciones(contribucioneOriginales):
    prompt = (
        f"""
        Formatea el siguiente texto como una lista en LaTeX usando `\\begin{{itemize}}` y `\\item` para cada contribución. 
        Asegúrate de que cada contribución termine en un punto y mantenga el formato de viñetas con puntos.
        El resultado debe estar solo en formato LaTeX, sin explicaciones adicionales no me pondras por ejemplo latex.

        Texto:
        \"\"\"
        {contribucioneOriginales}
        \"\"\"

        Formato esperado:
        \"\"\"
        \\begin{{itemize}}[label=\\textbullet]
            \\item Contribución 1.
            \\item Contribución 2.
            \\item .....
            \\item .....
            \\item Contribución n.
        \\end{{itemize}}
        \"\"\"
        """
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un asistente útil."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0.7
    )
    contribucioneOriginalesLatex = response.choices[0].message.content.strip()
    contribucioneOriginalesLatex = re.sub(r"```[a-zA-Z]*\n|```", "", contribucioneOriginalesLatex).strip()
    return contribucioneOriginalesLatex

def escape_ampersand(text):
    """
    Reemplaza '&' por '\&' si no tiene un '\' antes.
    """
    return re.sub(r'(?<!\\)&', r'\&', text)

def generar_texto_con_template(titulo, abstract_content, keywords_content, nuevo_contenido_footnote, nueva_introduccion, nueva_conclusion, secciones, bibtex_items, base_dir=None):
    if base_dir is None:
        base_dir = os.getcwd()  # Usar el directorio actual como base
    
    # Cambiar la obtención del path al template
    path_documento_tex = os.path.join(base_dir, './sn-article.tex')

    try:
        with open(path_documento_tex, 'r') as f:
            content = f.read()

        titulo = escapado_latex(titulo)
        abstract_content = escapado_latex(abstract_content)
        keywords_content = escapado_latex(keywords_content)
        nuevo_contenido_footnote = escapado_latex(nuevo_contenido_footnote)
        nueva_introduccion = escapado_latex(nueva_introduccion)
        nueva_conclusion = escapado_latex(nueva_conclusion)

        content = re.sub(r'\\title\{.*?\}', r'\\title{' + f'Survey of {titulo}' + '}', content)
        content = re.sub(r'\\begin\{abstract\}.*?\\end\{abstract\}', rf'\\begin{{abstract}}\n{abstract_content}\n\\end{{abstract}}', content, flags=re.DOTALL)
        content = re.sub(r'\\begin\{keywords\}.*?\\end\{keywords\}', rf'\\begin{{keywords}}\n{keywords_content}\n\\end{{keywords}}', content, flags=re.DOTALL)
        content = re.sub(r'\\section\{introduction\}.*?(?=\\section|\Z)', rf'\\section{{Introduction}}\n{nueva_introduccion}\n', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'\\section\{conclusions\}.*?(?=\\begin{thebibliography})', rf'\\section{{Conclusions}}\n{nueva_conclusion}\n', content, flags=re.DOTALL | re.IGNORECASE)

        insert_position = content.lower().find('\\section{conclusions}')
        if insert_position != -1:
            new_sections = ""
            for i, seccion in enumerate(secciones):
                new_sections += f'\\section{{{seccion["titulo"].capitalize()}}}\n{seccion["contenido"]}\n'
                if i == 0:  # Agregar la imagen después de la primera sección
                    new_sections += '\\begin{figure}[h]\n\\centering\n\\includegraphics[width=1\\textwidth]{Figures/lda_topic_graph_simplified.png}\n\\caption{Grafo de relaciones temáticas generado mediante LDA, donde los nodos representan temas identificados y sus palabras clave asociadas. La palabra clave central conecta los temas, y las palabras compartidas aparecen enlazadas a múltiples etiquetas según su relevancia en el modelo. Los pesos de los enlaces reflejan la importancia de cada término dentro de su tópico.}\n\\end{figure}\n'
            
            content = content[:insert_position] + new_sections + content[insert_position:]
        else:
            print('No se encontró la sección de conclusión en el documento.')




        biblio_start = content.find(r'\begin{thebibliography}{00}')
        if biblio_start != -1:
            biblio_end = content.find(r'\bibitem', biblio_start)
            if biblio_end == -1:
                biblio_end = content.find(r'\end{thebibliography}', biblio_start)
            new_references = '\n'.join([escapado_bibliografia(eliminar_tildes(ref)) for ref in bibtex_items]) + '\n'
            content = content[:biblio_end] + new_references + content[biblio_end:]
        else:
            print('No se encontró el entorno de bibliografía en el documento.')

        return content

    except Exception as e:
        print(f"Error al generar el texto con el template: {e}")

def generar_articulo_texto(apikey, general_title, json_data, lineas_investigacion, areas_interes, principales_contribuciones, metodologia, max_words, modelo="gpt-4o-mini", num_keywords=5, max_tokens=8000, temperatura=0.7):
    print(f"Iniciando generación de texto para: {general_title}")
    global client
    client = OpenAI(api_key=apikey)

    print("1b")
    secciones, referencias_nuevas_secciones = generate_section_summaries(json_data, lineas_investigacion, areas_interes, max_words, modelo, max_tokens)
    print("2b")
    secciones = genrarNuevosTitulos(secciones, general_title)
    secciones.append(secciones.pop(2))

    texto_completo = (
        metodologia + "\n\n" +
        "\n\n".join([seccion['contenido'] for seccion in secciones]) + "\n\n"
    )

    contribucioneOriginales="User a machine learning-based methodology to select the most relevant papers, standing out the latest and most cited papers in the area"
    contribucioneOriginales +="\n\n" + generateOriginalContri(secciones)
    contribucioneOriginales +="\n\n" + generateOriginalContri2(secciones)
    contribucioneOriginalesLatex=latexOrigContribuciones(contribucioneOriginales)
    secciones, citas_bibtexTR = generarTR(secciones, texto_completo, referencias_nuevas_secciones, contribucioneOriginalesLatex)

    texto_completo = (
        metodologia + "\n\n" +
        "\n\n".join([seccion['contenido'] for seccion in secciones]) + "\n\n"
    )

    prinContri = latexPrinContribuciones(principales_contribuciones)
    # Extraer solo el contenido LaTeX eliminando las comillas invertidas y espacios innecesarios
    principales_contribuciones = re.sub(r"```[a-zA-Z]*\n|```", "", prinContri).strip()

    print("Generando introducción...")
    introduction = generate_introduction(json_data, client, general_title, texto_completo, lineas_investigacion, areas_interes, principales_contribuciones, metodologia, secciones, max_words, modelo)

    print("Generando conclusión...")
    conclusion = generate_conclusion(client, general_title, texto_completo, lineas_investigacion, areas_interes, max_words, modelo)

    print("Generando keywords...")
    keywords = generate_keywords(client, general_title, texto_completo, lineas_investigacion, areas_interes, num_keywords, modelo)

    print("Generando abstract...")
    abstract = generate_abstract(client, general_title, texto_completo, lineas_investigacion, areas_interes, max_words, modelo)

    referencias_combinadas = combinar_referencias(referencias_nuevas_secciones, procesar_list_refs_paper(introduction)[1])
    bibtex_items = generar_bibtex(json_data, referencias_combinadas)
    bibtex_items = bibtex_items + citas_bibtexTR

    for i in range(len(secciones)):
        secciones[i]["contenido"]=escapado_latex2(secciones[i]["contenido"])    

    print("Generando texto final con el template...")
    texto_final = generar_texto_con_template(
        general_title, 
        abstract, 
        keywords, 
        "Universidad Politecnica Salesiana",
        introduction, 
        conclusion, 
        secciones, 
        bibtex_items
    )

    if texto_final:
        # Cambiar la ruta a la raíz del proyecto
        project_root = os.path.dirname(os.path.abspath(__file__))
        ruta_txt = os.path.join(project_root, f"{general_title.replace(' ', '_')}.tex")

        try:
            with open(ruta_txt, 'w', encoding='utf-8') as file:
                file.write(texto_final)
            print(f"Archivo .txt generado en: {ruta_txt}")
        except Exception as e:
            print(f"Error al guardar el archivo .txt: {str(e)}")
            return None
        return ruta_txt
    else:
        print("No se generó el texto final.")
        return None
