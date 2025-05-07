from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .logic import realizar_lda
from Recoleccion_datos.models import Recoleccion_datos
from preprocesamiento.models import Preprocesamiento
from Machine_learning.models import LDAModel
import pandas as pd
import json
import os

@csrf_exempt
@require_POST
def realizar_lda_view(request):
    try:
        data = json.loads(request.body)
        search_query = data.get('search_query', '')
        num_topics = data.get('num_topics', 5)
        alpha = data.get('alpha', 0.1)
        beta = data.get('beta', 0.01)
        max_iter = data.get('max_iter', 10)
        num_palabras = data.get('num_palabras', 5)
        n_docs = data.get('n_docs', 5) 
        n_palabras_topic = data.get('n_palabras', 3)
        apikey = data.get('apiKey', 'mm')

        if not search_query:
            return JsonResponse({"error": "El parámetro 'search_query' es requerido."}, status=400)

        # Obtener los datos de la base de datos
        recoleccion_datos_df = pd.DataFrame(list(Recoleccion_datos.objects.filter(busqueda__icontains=search_query).values()))
        preprocesamiento_df = pd.DataFrame(list(Preprocesamiento.objects.filter(busqueda=search_query).values()))
        columnas = preprocesamiento_df.columns.tolist()
        print(columnas)
        columnas = recoleccion_datos_df.columns.tolist()
        print(columnas)

        if recoleccion_datos_df.empty or preprocesamiento_df.empty:
            return JsonResponse({"error": "No se encontraron datos para la búsqueda especificada."}, status=404)

        # Llamar a la función para realizar LDA con los DataFrames
        n_palabras_topic = data.get('n_palabras', 5) 
        resultado_json, etiquetas_json = realizar_lda(preprocesamiento_df, recoleccion_datos_df, search_query, num_topics, alpha, beta, max_iter, num_palabras, n_docs, apikey,n_palabras_topic)
        print("resultado_json")
        print(resultado_json)
        if resultado_json is None or etiquetas_json is None:
            return JsonResponse({"error": "No se pudieron generar los resultados."}, status=500)

        LDAModel.objects.all().delete()

        # Guardar los JSON en la base de datos
        LDAModel.objects.create(
            busqueda=search_query,
            doc_topic_matrix_json=resultado_json,
            etiquetas_temas_json=etiquetas_json
        )

        return JsonResponse({
            "mensaje": "Análisis LDA realizado y resultados guardados exitosamente.",
            "resultado": json.loads(resultado_json),
            "etiquetas_temas": json.loads(etiquetas_json)
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Solicitud JSON inválida."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
