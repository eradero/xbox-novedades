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
def verify_image_relevance(image_url, post_title):
    """Uses Gemini to check if an image URL is relevant to the blog post title."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return True # Default to True if no API key
    
    client = genai.Client(api_key=api_key)
    
    prompt = f"Is this image relevant to a blog post titled '{post_title}'? Answer only YES or NO."
    
    try:
        # Fetch the image
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(image_url, timeout=10, headers=headers)
        if response.status_code != 200:
            return False
        
        # In a real scenario, we would pass the image bytes to Gemini.
        # For now, we will use a simpler check: ask Gemini based on the URL and Title
        # because passing bytes requires a different API call structure in genai.
        
        check_prompt = f"""
        Analiza si esta URL de imagen parece tener relación con el título del post.
        Título: {post_title}
        URL: {image_url}
        
        Responde 'SÍ' si la URL contiene palabras clave relacionadas o parece ser una imagen de prensa/juego válida.
        Responde 'NO' si parece ser un anuncio, un logo genérico de una web de noticias (como '3djuegos-logo'), o un avatar.
        Responde solo SÍ o NO.
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=check_prompt,
        )
        return "SÍ" in response.text.upper()
    except Exception as e:
        print(f"Error verificando imagen: {e}")
        return True # Fallback to True
