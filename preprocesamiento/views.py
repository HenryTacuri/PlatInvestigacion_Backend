from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .logic import analyze_and_preprocess, extract_top_ngrams
import pandas as pd
from Recoleccion_datos.models import Recoleccion_datos
from .models import Preprocesamiento
import json

@csrf_exempt
@require_POST
def realizar_analisis_view(request):
    try:
        # Parsear el cuerpo de la solicitud como JSON
        data = json.loads(request.body)
        search_query = data.get('search_query', '')
        contenidoBusqueda= data.get('contenidoBusqueda', '')
        print(contenidoBusqueda)

        if not search_query:
            return JsonResponse({"error": "El parámetro 'search_query' es requerido."}, status=400)

        # Obtener los datos desde la base de datos usando el modelo Recoleccion_datos
        datos_cargados = Recoleccion_datos.objects.filter(busqueda__icontains=search_query)


        if not datos_cargados.exists():
            return JsonResponse({"error": "No se encontraron datos para la búsqueda especificada."}, status=404)

        # Convertir los datos a un DataFrame de pandas
        datos_cargados_df = pd.DataFrame(list(datos_cargados.values('titulo', contenidoBusqueda)))

        # Realizar análisis y preprocesamiento
        processed_data = analyze_and_preprocess(datos_cargados_df, contenidoBusqueda)

        print(processed_data)

        if processed_data is not None:
            ngram_freq = extract_top_ngrams(processed_data['Tokenized_Text'])

            # Convertir ngram_freq a tipos serializables por JSON
            ngram_freq = [(word, int(freq)) for word, freq in ngram_freq]

            Preprocesamiento.objects.filter(busqueda=search_query).delete()

            # Guardar resultados procesados en la base de datos
            for _, row in processed_data.iterrows():
                Preprocesamiento.objects.create(
                    titulo=row['titulo'],
                    tokenized_text=row['Tokenized_Text'],
                    busqueda=search_query,
                    abstract=row[contenidoBusqueda]
                )

            return JsonResponse({
                "mensaje": "Análisis realizado y datos guardados exitosamente.",
                "ngrams": ngram_freq
            })

        else:
            return JsonResponse({"error": "No se pudieron procesar los datos."}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Solicitud JSON inválida."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
