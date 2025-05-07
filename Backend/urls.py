from django.contrib import admin
from django.urls import path
from Recoleccion_datos.views import buscar_articulos_view
from preprocesamiento.views import realizar_analisis_view
from Machine_learning.views import realizar_lda_view
from probar_api.views import verificar_conexion
from diagrama.views import generar_diagrama_view, obtener_imagen, obtenerGrafoLDA

# Nueva ruta importada para manejar el archivo .txt
from creacion_pdf.views import generar_articulo_txt_view
from Recoleccion_datos.views import upload_files
from Recoleccion_datos.views import delete_all_files
from Recoleccion_datos.views import listar_documentos

urlpatterns = [
    path("admin/", admin.site.urls),
    path('buscar-articulos/', buscar_articulos_view, name='buscar_articulos'),
    path('preprocesamiento/', realizar_analisis_view, name='preprocesamiento'),
    path('generar_txt/', generar_articulo_txt_view, name='generar_txt'),  # Nueva ruta para .txt
    path('encontrar-temas/', realizar_lda_view, name='encontrar_temas'),
    path('generar-diagrama/', generar_diagrama_view, name='generar_diagrama'),
    path('verificar-conexion/', verificar_conexion, name='verificar_conexion'),
    path('upload/', upload_files, name='upload-files'),
    path('delete-all-files/', delete_all_files, name='delete_all_files'),
    path('listar-documentos/', listar_documentos, name='listar_documentos'),
    path('api/imagen/', obtener_imagen, name='obtener_imagen'),
    path('api/grafo/', obtenerGrafoLDA, name='obtener_grafo'),
]
