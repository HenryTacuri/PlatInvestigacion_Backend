from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from Machine_learning.models import LDAModel
from .logic import crear_grafica_lda
import json
import os
from django.conf import settings

nameFile = ''

@csrf_exempt
@require_POST
def generar_diagrama_view(request):
    global nameFile
    
    print("1")
    try:
        data = json.loads(request.body)
        search_query = data.get('search_query', '')
        nameFile = search_query

        print("2")
        if not search_query:
            return JsonResponse({"error": "El parámetro 'search_query' es requerido."}, status=400)
        print("3")
        # Cargar los resultados desde la base de datos
        resultados = LDAModel.objects.filter(busqueda=search_query)
        print("4")
        if not resultados.exists():
            return JsonResponse({"error": "No se encontraron resultados para la búsqueda especificada."}, status=404)
        print("5")
        # Procesar el primer resultado (o puedes modificar esto para manejar múltiples resultados)
        resultado = resultados.first()
        resultado_etiquetas = json.loads(resultado.etiquetas_temas_json)
        print("6")
        # Crear la gráfica y guardar el HTML
        output_html = crear_grafica_lda(resultado_etiquetas, keyword=search_query, peso_umbral=0.6, num_palabras=100)
        print("7")
        # Leer el archivo HTML utilizando la codificación UTF-8 y devolverlo en la respuesta
        with open(output_html, 'r', encoding='utf-8') as html_file:
            response = HttpResponse(html_file.read(), content_type='text/html')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(output_html)}"'
            return response
    except json.JSONDecodeError:
        return JsonResponse({"error": "Solicitud JSON inválida."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def obtener_imagen(request):
    print("a")
    """Devuelve la imagen ubicada en la raíz del proyecto Django"""
    imagen_path = os.path.join(settings.BASE_DIR, 'lda_topic_graph_simplified.png')  # Ruta absoluta
    if os.path.exists(imagen_path):
        return FileResponse(open(imagen_path, "rb"), content_type="image/png")
    else:
        raise Http404("Imagen no encontrada")
    
def obtenerGrafoLDA(request):
    global nameFile
    print('nombre archivo: ' + nameFile)
    grafo_path = os.path.join(settings.BASE_DIR, 'lda_graph_' + nameFile + '.html')  # Ruta absoluta
    if os.path.exists(grafo_path):
        return FileResponse(open(grafo_path, "rb"), content_type="text/html")
    else:
        raise Http404("Archivo HTML no encontrado")
