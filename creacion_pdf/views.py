from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from Machine_learning.models import LDAModel
from Recoleccion_datos.models import Recoleccion_datos
from preprocesamiento.models import Preprocesamiento
from diagrama.models import GraphLink
import json
import os
import re

from .logic import generar_articulo_texto

@csrf_exempt
@require_POST
def generar_articulo_txt_view(request):
    print("Iniciando la vista para generar .txt")
    try:
        print("Cargando datos del request...")
        # Cargar el cuerpo de la solicitud JSON
        data = json.loads(request.body)
        busqueda = data.get('search_query', '')
        lineas_investigacion = data.get('lineas_investigacion', '')
        areas_interes = data.get('areas_interes', '')
        max_words = data.get('max_words', 250)
        max_keywords = data.get('max_keywords', 5)
        apikey = data.get('apiKey', 'mm')
        
        print(f"Datos recibidos: busqueda={busqueda}, max_words={max_words}, max_keywords={max_keywords}")

        print("1a")
        
        if not busqueda:
            return JsonResponse({"error": "El parámetro 'busqueda' es requerido."}, status=400)

        print("2a")

        # Cargar el último resultado desde la base de datos
        try:
            resultado = LDAModel.objects.filter(busqueda=busqueda).order_by('-id').first()
            if not resultado:
                return JsonResponse({"error": "No se encontraron resultados para la búsqueda especificada."}, status=404)
            json_data = json.loads(resultado.doc_topic_matrix_json)
            print("Datos de la base de datos cargados correctamente.")
        except LDAModel.DoesNotExist:
            return JsonResponse({"error": "No se encontraron resultados para la búsqueda especificada."}, status=404)

        # Variables de contribuciones y metodología
        metodologia = 'Our methodology is designed to ensure a comprehensive and systematic analysis of scientific literature. It begins with the meticulous preparation of text data, applying advanced natural language processing (NLP) techniques to clean and refine the information. This step is crucial for ensuring that the data is of high quality and ready for detailed analysis. A detailed breakdown of the methodology can be found in the figure at the end of this document. Once the data is prepared, we employ machine learning models, specifically Latent Dirichlet Allocation (LDA), to identify and categorize the underlying topics within the text. This process involves configuring the model to fit the preprocessed data, allowing us to uncover the hidden thematic structures. With the topics identified, we then develop a recommendation system. This system uses the topic-document matrix generated by the LDA model to suggest the most relevant articles, enhancing the relevance and coherence of the survey. Following this, we focus on creating various knowledge representations. This includes generating textual summaries, visualizing relationships between topics and documents, and using the GPT API to generate explanatory text. These representations help in synthesizing the main findings and presenting them in an accessible format. Finally, we integrate all these representations into a comprehensive report. This report is structured to be user-friendly and accessible, combining text and figures to provide a complete overview of the analysis. The final product is a survey with calculated and fixed sections, offering a robust and automated approach for creating survey articles.'
        principales_contribuciones ="Revisión Exhaustiva del Estado del Arte: Análisis detallado y síntesis de las contribuciones más relevantes y recientes en la literatura existente. Metodología Estructurada Basada en CRISP-DM: Aplicación de una metodología estándar para guiar el proceso de minería de datos, incluyendo fases desde la comprensión del problema hasta la generación de representaciones de conocimiento. Modelos de Machine Learning Avanzados: Uso de Latent Dirichlet Allocation (LDA) para identificar y categorizar tópicos latentes y desarrollo de un sistema de recomendación basado en la matriz de documentos y tópicos, con el fin de identificar los temas más relevantes y los documentos más importantes asociados. Generación de Conocimiento Sintetizado: Creación de resúmenes textuales y visualización de relaciones entre tópicos y documentos para mejorar la comprensión. Informes Comprensivos y Comprensibles: Integración de representaciones en informes detallados que combinan texto y figuras para ofrecer una visión clara y completa del análisis."


        print("3a")
        
        # Generar el archivo .txt
        try:
            print("Generando el archivo .tex...")
            ruta_txt = generar_articulo_texto(
                apikey,
                general_title=busqueda,
                json_data=json_data,
                lineas_investigacion=lineas_investigacion,
                areas_interes=areas_interes,
                principales_contribuciones=principales_contribuciones,
                metodologia=metodologia,
                max_words=max_words,
                num_keywords=max_keywords,
            )
        except Exception as e:
            return JsonResponse({"error": f"Error al generar el archivo de texto: {str(e)}"}, status=500)

        if not ruta_txt or not os.path.exists(ruta_txt):
            return JsonResponse({"error": "Error al generar o encontrar el archivo .tex."}, status=500)

        # Preparar el archivo .txt para descargar
        try:
            with open(ruta_txt, 'rb') as txt_file:
                response = HttpResponse(txt_file.read(), content_type='application/x-tex')
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(ruta_txt)}"'
            return response
        except Exception as e:
            return JsonResponse({"error": f"Error al leer el archivo de texto: {str(e)}"}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Solicitud JSON inválida."}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Error interno del servidor: {str(e)}"}, status=500)

def limpiar_base_de_datos():
    LDAModel.objects.all().delete()
    Recoleccion_datos.objects.all().delete()
    Preprocesamiento.objects.all().delete()
    GraphLink.objects.all().delete()
