import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
from sklearn.feature_extraction.text import CountVectorizer
import pandas as pd

nltk.download('stopwords')
nltk.download('wordnet')

search_query = "recommendation systems"

def get_lemma(word):
    lemmatizer = WordNetLemmatizer()
    lemma = lemmatizer.lemmatize(word, pos=wordnet.VERB)
    return lemma if lemma != word else lemmatizer.lemmatize(word, pos=wordnet.NOUN)

def preprocess_text(text):
    text = re.sub(r'https?\S+', ' ', text)
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.lower()

    stop_words = set(stopwords.words('english'))
    tokens = [get_lemma(word) for word in text.split() if word not in stop_words and len(word) > 4]
    tokens = ['recommend' if word in ['recommendation', 'recommender'] else word for word in tokens]

    forced_keywords = search_query.split()
    for keyword in forced_keywords:
        tokens.extend([keyword] * 5)

    return ' '.join(tokens)

def custom_tokenizer(text):
    vectorizer = CountVectorizer(ngram_range=(1, 3), token_pattern=r'\b\w+\b')
    analyzer = vectorizer.build_analyzer()
    tokens = analyzer(text)
    tokens = ['_'.join(token.split()) if ' ' in token else token for token in tokens]
    return tokens

def analyze_and_preprocess(datos_cargados_df, contenidoBusqueda):
    if datos_cargados_df.empty:
        print("The DataFrame is empty.")
        return None

    # Utilizar la columna 'abstract' para análisis
    datos_cargados_df['Processed_Text'] = datos_cargados_df[contenidoBusqueda].apply(preprocess_text)
    datos_cargados_df['Tokenized_Text'] = datos_cargados_df['Processed_Text'].apply(lambda x: ' '.join(custom_tokenizer(x)))

    return datos_cargados_df[['titulo', 'Tokenized_Text', contenidoBusqueda]]

def extract_top_ngrams(texts, ngram_range=(1, 1), top_n=100):
    vec = CountVectorizer(tokenizer=custom_tokenizer, ngram_range=ngram_range, token_pattern=r'\b\w+\b')
    matrix = vec.fit_transform(texts)
    sum_words = matrix.sum(axis=0)
    words_freq = [(word, sum_words[0, idx]) for word, idx in vec.vocabulary_.items()]
    sorted_words_freq = sorted(words_freq, key=lambda x: x[1], reverse=True)[:top_n]
    return sorted_words_freq
