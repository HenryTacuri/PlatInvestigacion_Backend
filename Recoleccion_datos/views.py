from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from .logic import buscar_articulos_con_variaciones
from .models import Recoleccion_datos
import json
import unicodedata
import re
import shutil
import os

# Funcionalidad para subir doc a la carpeta local 
UPLOAD_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Repositorio local')

if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

@csrf_exempt
@require_POST
def upload_files(request):
    if request.method == 'POST' and request.FILES.getlist('files'):
        files = request.FILES.getlist('files')
        fs = FileSystemStorage(location=UPLOAD_DIRECTORY)

        file_urls = []
        already_exists = []

        for file in files:
            file_path = os.path.join(UPLOAD_DIRECTORY, file.name)

            # Verificar si el archivo ya existe
            if os.path.exists(file_path):
                already_exists.append(file.name)
            else:
                filename = fs.save(file.name, file)
                file_urls.append(fs.url(filename))

        # Si algunos archivos ya existían, devolver error parcial
        if already_exists:
            return JsonResponse({
                "message": "Algunos archivos ya existen y no se subieron.",
                "existing_files": already_exists
            }, status=400)

        return JsonResponse({"message": "archivos subidos exitosamente!", "file_urls": file_urls}, status=200)

    return JsonResponse({"message": "no se subieron los documentos."}, status=400)

# Eliminar todos los documentos dentro de la carpeta repositorio local

@csrf_exempt
@require_POST
def delete_all_files(request):
    try:
        if os.path.exists(UPLOAD_DIRECTORY):
            # Eliminar todos los archivos y carpetas dentro del directorio
            for filename in os.listdir(UPLOAD_DIRECTORY):
                file_path = os.path.join(UPLOAD_DIRECTORY, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Eliminar archivo o enlace simbólico
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Eliminar carpeta y su contenido

            return JsonResponse({"message": "All files deleted successfully!"}, status=200)
        else:
            return JsonResponse({"message": "Upload directory does not exist."}, status=404)
    except Exception as e:
        return JsonResponse({"message": f"Error deleting files: {str(e)}"}, status=500)





def eliminar_tildes(texto):
    if texto:
        texto_normalizado = unicodedata.normalize('NFD', texto)
        texto_sin_tildes = re.sub(r'[\u0300-\u036f]', '', texto_normalizado)
        return texto_sin_tildes
    return texto

@csrf_exempt
@require_POST
def buscar_articulos_view(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    
    search_query = body.get('search_query', '')
    cantidad = int(body.get('cantidad', 1000))
    repositorios = body.get('repositorios', [])
    #directorio = body.get('directorio', None)

    directorio = os.path.abspath(os.path.join('Recoleccion_datos','Repositorio local'))
    print(directorio)

    if not search_query:
        return JsonResponse({"error": "El parámetro 'search_query' es requerido."}, status=400)

    print(repositorios)

    Recoleccion_datos.objects.all().delete()

    resultados = buscar_articulos_con_variaciones(nombre_articulo=search_query, cantidad=cantidad, repositorios=repositorios, directorio_local=directorio)
    
    if resultados is not None:

        data = resultados.to_dict(orient='records')
        
        # Guardar resultados en la base de datos con tildes eliminadas
        for item in data:
            Recoleccion_datos.objects.create(
                titulo=item.get('titulo', ''),
                autor=item.get('autor', ''),
                link=item.get('link', ''),
                ano=item.get('ano', ''),
                texto=item.get('Texto', ''),
                abstract=item.get('abstract', ''),
                busqueda=search_query,
                cita=item.get('cita', '')
            )
        
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({"mensaje": "No se encontraron artículos."}, status=404)


@csrf_exempt
@require_GET
def listar_documentos(request):
    try:
        # Verificar si la carpeta existe
        if not os.path.exists(UPLOAD_DIRECTORY):
            return JsonResponse({"message": "El directorio no existe."}, status=404)

        # Obtener la lista de archivos PDF y .bib
        archivos = [f for f in os.listdir(UPLOAD_DIRECTORY) if f.endswith(('.pdf', '.bib'))]

        return JsonResponse({"titulos": archivos}, status=200, safe=False)

    except Exception as e:
        return JsonResponse({"error": f"Error al listar documentos: {str(e)}"}, status=500)