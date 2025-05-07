import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import openai

@csrf_exempt
@require_POST
def verificar_conexion(request):
    try:
        print("Solicitud recibida en 'verificar_conexion'")
        
        # Imprimir el cuerpo crudo de la solicitud
        print("Cuerpo crudo de la solicitud:", request.body)

        # Parsear el cuerpo de la solicitud
        try:
            body = json.loads(request.body)
            print("Cuerpo de la solicitud parseado:", body)
        except json.JSONDecodeError as json_error:
            print(f"Error de JSON: {json_error}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format'}, status=400)

        # Obtiene la nueva clave de la API del cuerpo de la solicitud
        new_api_key = body.get("apiKey")
        if not new_api_key:
            print("No se proporcionó una API key.")
            return JsonResponse({'status': 'error', 'message': 'API key is required'}, status=400)

        print("Nueva API key recibida:", new_api_key)

        # Configura la API key de OpenAI
        openai.api_key = new_api_key
        print("API key configurada correctamente en OpenAI")

        # Preparar el prompt para la prueba de conexión
        prompt = "Say hello"

        # Realiza una consulta de prueba a la API de OpenAI usando la misma estructura que mencionaste
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",  # Usar un modelo compatible
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=5,
                temperature=0.7
            )

            # Obtener el contenido de la respuesta
            respuesta = response.choices[0].message.content.strip()
            print("Respuesta de OpenAI:", respuesta)

        except Exception as api_error:
            print(f"Error al conectar con OpenAI: {api_error}")
            return JsonResponse({'status': 'error', 'message': f'Error in API call: {api_error}'}, status=500)

        # Si la respuesta es exitosa, devuelve un estado OK
        if respuesta:
            os.environ["OPENAI_API_KEY"] = new_api_key
            print("Conexión exitosa, clave actualizada en las variables de entorno")

            saved_api_key = os.getenv("OPENAI_API_KEY")
            print("Clave de API guardada en variable de entorno:", saved_api_key)
            return JsonResponse({'status': 'ok', 'message': 'Connection successful!'})
        


        print("No se recibió respuesta del modelo de OpenAI.")
        return JsonResponse({'status': 'error', 'message': 'No response from API'}, status=500)

    except Exception as e:
        print(f"Error en 'verificar_conexion': {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)