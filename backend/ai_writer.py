from google import genai
import os
import time
import requests

def generate_blog_post(original_title, original_content):
    """Uses Gemini API to write a blog post based on the news."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY no encontrada. Ejecutando en modo MOCK (Simulación).")
        return None
    
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
        Eres un periodista experto en videojuegos. Reescribe la noticia para un blog fan de Xbox Series X con tono entusiasta y amigable.
        Usa un tono informativo, profesional pero fácil de entender.
        Usa formato Markdown. IMPORTANTE: Escribe siempre en Español Latinoamericano de Argentina (es-AR), usando el voseo ("tenés", "jugá", "mirá"). NUNCA uses la palabra "che". NUNCA escribas en español de España (es-es) ni uses "vosotros". IMPORTANTE: Si mencionas precios, úsalos SIEMPRE en Dólares (USD) o Pesos Argentinos (ARS), NUNCA en Euros.
        
        Título original: {original_title}
        
        Contenido original o extracto:
        {original_content[:3000]}
        
        Devuelve EXACTAMENTE el siguiente formato y NADA MÁS:
        
        [TITULO]
        (Título atractivo)
        [DESCRIPCION]
        (Descripción breve)
        [PROMPT_IMAGEN]
        (Oración en inglés para IA)
        [AFFILIATE_LINK]
        (Genera un link de búsqueda de Amazon para el juego y la consola Xbox Series X. IMPORTANTE: El link DEBE terminar con &tag=blogseradero-20 para que sea válido)
        [CONTENIDO]
        (Cuerpo del artículo en Markdown)
        """
        
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = response.text
            
            # Parsing
            title = text.split("[TITULO]")[1].split("[DESCRIPCION]")[0].strip()
            description = text.split("[DESCRIPCION]")[1].split("[PROMPT_IMAGEN]")[0].strip()
            image_prompt = text.split("[PROMPT_IMAGEN]")[1].split("[AFFILIATE_LINK]")[0].strip()
            affiliateLink = text.split("[AFFILIATE_LINK]")[1].split("[CONTENIDO]")[0].strip()
            body_content = text.split("[CONTENIDO]")[1].strip()
            
            return {
                "title": title,
                "description": description,
                "image_prompt": image_prompt,
                "affiliateLink": affiliateLink,
                "content": body_content
            }
            
        except Exception as e:
            print(f"Error con la API de Gemini: {e}")
            time.sleep(10)
    return None
def verify_image_relevance(image_url, post_title, post_description=""):
    """Usa Gemini Vision para verificar que el contenido visual de la imagen sea relevante al post."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return True

    client = genai.Client(api_key=api_key)

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        img_response = requests.get(image_url, timeout=10, headers=headers)
        if img_response.status_code != 200:
            return False

        mime_type = img_response.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        if not mime_type.startswith("image/"):
            mime_type = "image/jpeg"

        from google.genai import types
        desc_line = f"Descripción: {post_description}" if post_description else ""
        check_prompt = f"""Analizá visualmente esta imagen y determiná si tiene relación con el siguiente artículo de blog:

Título: {post_title}
{desc_line}

La imagen ES relevante si muestra elementos relacionados con el tema (consolas, videojuegos, tecnología, IA, personajes, logos, escenas del juego, etc.).
La imagen NO es relevante si muestra: documentos de texto, facturas, gráficos de ventas genéricos, vehículos sin contexto gamer, logos de empresas ajenas, trabajos escolares, o cualquier cosa completamente fuera de tema.

Respondé solo: SÍ o NO."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=img_response.content, mime_type=mime_type),
                check_prompt,
            ],
        )
        is_relevant = "SÍ" in response.text.strip().upper() or response.text.strip().upper().startswith("SI")
        if not is_relevant:
            print(f"  Imagen rechazada por Gemini Vision: no es relevante para '{post_title[:60]}'")
        return is_relevant
    except Exception as e:
        print(f"Error verificando imagen con Gemini Vision: {e}")
        return True
