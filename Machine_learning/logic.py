import pandas as pd
import numpy as np
import json
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
import os
import pickle
import openpyxl
from sklearn.preprocessing import MinMaxScaler

temasNuevos = ["fundamental", "evaluation", "trends"]

# Configuración del cliente de OpenAI
#api_key = os.getenv("OPENAI_API_KEY")
#client = OpenAI(api_key=api_key)

def convertir_a_serializable(obj):
    if isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.to_dict()
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float32)):
        return float(obj)
    if isinstance(obj, (np.ndarray, pd.Index)):
        return obj.tolist()
    return json.JSONEncoder.default(obj)

def matNueva(words, search_query):
    def keyworsGPT(palabra, search_query):
        prompt = (
            f"From the available list of keywords: '{words}', select the 10 most important keywords "
            f"related to the general topic '{search_query}' and the specific section '{palabra}' of an academic article. "
            f"Please select relevant, understandable words that exist within the provided list. "
            f"Respond with exactly 10 keywords—no more, no less—separated by commas, without special characters or additional text. "
            f"Ensure that the selected words are consistent with the topic and the specified section."
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

    temas_y_keywords = {}
    for keyword in temasNuevos:
        palabras = keyworsGPT(keyword, search_query)
        # Convertir a un vector (lista) eliminando espacios adicionales
        vector = [palabra.strip() for palabra in palabras.split(",")]
        # Agregar al diccionario con el tema como clave
        temas_y_keywords[keyword] = vector

    return temas_y_keywords

def procesar_keywords(temas_y_keywords):
    # Convertir las palabras clave al formato del vocabulario (guiones bajos y minúsculas)
    temas_y_keywords_procesados = {
        tema: [palabra.replace(" ", "_").lower() for palabra in palabras]
        for tema, palabras in temas_y_keywords.items()
    }
    return temas_y_keywords_procesados
    
def construirVectoresPredefinidos(words, temas_y_keywords):
    # Crear la matriz c
    predefined_vectors = np.array([[1 if word in keywords else 0 for word in words] 
                                    for _, keywords in temas_y_keywords.items()])
    return predefined_vectors

def matrizSimilaridad(words, lda_components, predefined_topics):
    # Construir los vectores predefinidos
    predefined_vectors = construirVectoresPredefinidos(words, predefined_topics)
    
    # Calcular la matriz de similaridad coseno
    similarity_matrix = cosine_similarity(predefined_vectors, lda_components)
    return similarity_matrix

def realizar_lda(preprocesamiento_df, recoleccion_datos_df, search_query, num_topics, alpha, beta, max_iter, num_palabras, n_docs, apikey,n_palabras_topic=5):

    print("Forma de preprocesamiento_df:", preprocesamiento_df.shape)
    print("Forma de recoleccion_datos_df:", recoleccion_datos_df.shape)

    print("1")
    global client
    client = OpenAI(api_key=apikey)
    print("2")

    # Combinar los datos necesarios
    datos_cargados_df = preprocesamiento_df[['titulo', 'tokenized_text', 'abstract']]
    datos_autores = recoleccion_datos_df[['titulo', 'autor', 'link', 'ano', 'cita']]
    datos_cargados_df = datos_cargados_df.merge(datos_autores, on='titulo', how='left')

    print("3")

    if datos_cargados_df.empty:
        return None, None

    datos_cargados_df['Combined_Text'] = datos_cargados_df['abstract']

    print("4")

    # Vectorizar los textos tokenizados
    global words, term_topic_matrix, doc_topic_matrix, X
    vectorizer = CountVectorizer(token_pattern=r'\b[a-zA-Z]{3,15}\b') # Solo palabras de 3 a 15 caracteres
    X = vectorizer.fit_transform(datos_cargados_df['tokenized_text'])

    print("5.1")

    # Aplicar LDA para identificar temas en los documentos
    lda_model = LatentDirichletAllocation(n_components=num_topics, doc_topic_prior=alpha, topic_word_prior=beta, max_iter=max_iter, random_state=42)
    lda_model.fit(X)
    print("5.2")
    global term_topic_matrix, doc_topic_matrixp, temas_y_keywords_procesados, doc_topic_matrix

    # Obtener la matriz término-tópico y convertirla a probabilidades
    words = vectorizer.get_feature_names_out()
    term_topic_matrix = lda_model.components_
    doc_topic_matrixp = lda_model.transform(X)
    
    term_topic_probabilities = term_topic_matrix / term_topic_matrix.sum(axis=1)[:, np.newaxis] * 100
    print("5.3")
   # Escalar matriz de LDA (ya está entre 0 y 1, pero aseguramos)
    lda_scaler = MinMaxScaler()
    doc_topic_matrixp = lda_scaler.fit_transform(doc_topic_matrixp)
    print("5.4")
    # Generar relevancia de temas predefinidos
    temas_y_keywords_procesados = matNueva(words,search_query)
    print("5.4.1")
    predefined_vectors = construirVectoresPredefinidos(words, temas_y_keywords_procesados)
    print("5.4.2")
    predefined_doc_relevance = np.dot(X.toarray(), predefined_vectors.T)
    print("5.5")
    # Escalar temas predefinidos al rango 0-1
    predefined_scaler = MinMaxScaler()
    predefined_doc_relevance = predefined_scaler.fit_transform(predefined_doc_relevance)
    print("5.6")
    # Combinar las matrices escaladas
    doc_topic_matrix = np.hstack((predefined_doc_relevance, doc_topic_matrixp))
    print("5.7")
    # Crear DataFrame
    columnas_temas = [f'Topic {i}' for i in range(doc_topic_matrix.shape[1])]
    doc_topic_matrix = pd.DataFrame(doc_topic_matrix, columns=columnas_temas)
    print("5.8") 
    temas_previos = []

    print("6")
    # Asigna etiquetas a los temas utilizando un modelo GPT
    def etiquetar_temas_con_gpt(model, vectorizer, n_top_words, temas_previos, search_query):
        words = vectorizer.get_feature_names_out()
        etiquetas_temas = []
        temasNuevos = ["fundamental", "evaluation", "trends"]
        
        for topic_idx in range(len(temasNuevos) + num_topics):  # 3 temas predefinidos + 4 temas de LDA = 7
            if topic_idx < len(temasNuevos):  # Si es uno de los temas predefinidos
                etiqueta = f"{temasNuevos[topic_idx]} of {search_query}"
                real_topic_idx = topic_idx  # Asignamos un índice válido
                top_words = [words[i] for i in model.components_[real_topic_idx].argsort()[:-n_top_words - 1:-1]]
                palabras_y_probabilidades = {words[i]: term_topic_probabilities[real_topic_idx][i] for i in range(len(words))}
            else:  # Si es un tema generado por LDA
                real_topic_idx = topic_idx - len(temasNuevos)  # ✅ Ahora siempre se define antes de usarlo
                print("Palabras claves: ",n_top_words)
                top_words = [words[i] for i in model.components_[real_topic_idx].argsort()[:-n_top_words - 1:-1]]
                etiqueta = etiquetar_con_gpt(" ".join(top_words), temas_previos, search_query)
                palabras_y_probabilidades = {words[i]: term_topic_probabilities[real_topic_idx][i] for i in range(len(words))}
        
            temas_previos.append(etiqueta)
        
            etiquetas_temas.append({
                "Etiqueta": etiqueta,
                "Palabras_Clave": palabras_y_probabilidades
            })

    
        return etiquetas_temas


    # Genera una etiqueta para un tema específico utilizando GPT
    def etiquetar_con_gpt(texto, temas_previos, search_query):
        prompt = (
            f"genera una nueva etiqueta en inglés de {num_palabras} palabras, que esté muy relacionada con el texto proporcionado. "
            f"Texto en el que te debes basar por completo para el etiquetado: '{texto}'"
            f" Respondeme unicamente la etiqueta sin caracteres especiales ni nada por el estilo"
        )
        print("--------------------------------------------------------------------------------------------")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            n=1,
            stop=None,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    # Generar etiquetas de temas utilizando la función de GPT
    global etiquetas_temas
    etiquetas_temas = etiquetar_temas_con_gpt(lda_model, vectorizer, n_palabras_topic, temas_previos, search_query)

    print("7")

    # Imprimir las etiquetas generadas después del procesamiento con GPT
    print("Etiquetas generadas después de GPT:")
    for i, et in enumerate(etiquetas_temas):
        print(f"Tópico {i}: {et['Etiqueta']}")

    print("8")

    # Obtener los documentos más relevantes para cada tema basado en la matriz documento-tema
    def obtener_documentos_importantes(doc_topic_matrix, etiquetas_modificadas, datos_cargados_df, n):
        print("Columnas de doc_topic_matrix:", doc_topic_matrix.columns)
        print("Forma de doc_topic_matrix:", doc_topic_matrix.shape)
        print("datos_cargados_df:", datos_cargados_df.columns)

        resultado = {}
        for idx, etiqueta in enumerate(etiquetas_modificadas):
            top_docs = doc_topic_matrix[f'Topic {idx}'].nlargest(n).index
            documentos = []
            for doc_index in top_docs:
                if doc_index in datos_cargados_df.index:
                    titulo = datos_cargados_df.loc[doc_index, 'titulo']
                    autor = datos_cargados_df.loc[doc_index, 'autor']
                    link = datos_cargados_df.loc[doc_index, 'link']
                    ano = datos_cargados_df.loc[doc_index, 'ano']
                    abstract = datos_cargados_df.loc[doc_index, 'abstract']
                    cita = datos_cargados_df.loc[doc_index, 'cita']
                    codigo = f"{autor.split()[0]}_{ano}"
                    documentos.append({
                        "Title": titulo,
                        "Author": autor,
                        "Link": link,
                        "Year": int(ano),
                        "Text": abstract,
                        "Citation": cita,
                        "Codigo": codigo
                    })
            resultado[etiqueta["Etiqueta"]] = documentos[:n]  # Solo guardar los primeros n documentos relevantes
        return resultado

    # Obtener documentos relevantes para cada tema
    documentos_importantes = obtener_documentos_importantes(doc_topic_matrix, etiquetas_temas, datos_cargados_df, n_docs)
    print("9")

    # Estructura del resultado sin etiquetas de temas
    resultado_completo = {
        "General_Title": search_query,
        "Tema": documentos_importantes
    }


    # Convertir los resultados a JSON
    resultado_json = json.dumps(resultado_completo, ensure_ascii=False, indent=4, default=convertir_a_serializable)
    etiquetas_json = json.dumps(etiquetas_temas, ensure_ascii=False, indent=4, default=convertir_a_serializable)

    print("10")

    return resultado_json, etiquetas_json
