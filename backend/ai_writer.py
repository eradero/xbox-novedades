from google import genai
import os
import time

def generate_blog_post(original_title, original_content):
    """Uses Gemini API to write a blog post based on the news."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY no encontrada. Ejecutando en modo MOCK (Simulación).")
        return None
    
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
        Genera una entrada de blog sobre las últimas novedades del universo Xbox. El estilo debe ser moderno, dinámico y entusiasta, similar al tono de comunicación oficial de Xbox. Incluye información sobre lanzamientos de juegos recientes o futuros, actualizaciones de Game Pass, anuncios de hardware o eventos importantes de la comunidad Xbox.
        Reescribe y expande la siguiente noticia para un blog especializado.
        Usa un tono informativo, profesional pero fácil de entender.
        Usa formato Markdown. IMPORTANTE: Si mencionas precios, úsalos SIEMPRE en Dólares (USD) o Pesos Argentinos (ARS), NUNCA en Euros.
        
        Título original: {original_title}
        
        Contenido original o extracto:
        {original_content[:3000]}
        
        Devuelve EXACTAMENTE el siguiente formato y NADA MÁS:
        
        [TITULO]
        (Aquí el nuevo título atractivo)
        [DESCRIPCION]
        (Una breve descripción de 1 línea para SEO)
        [PROMPT_IMAGEN]
        (Escribe UNA SOLA oración en INGLÉS describiendo la escena principal para generarla en IA. Debe ser estilo cartoon. Imágenes de consolas Xbox Series X y S, logotipos de Xbox y Game Pass, capturas de pantalla de juegos exclusivos de Xbox, o elementos visuales que representen la cultura gamer de Xbox.)
        [CONTENIDO]
        (Aquí el cuerpo completo del artículo en Markdown. Usa párrafos, negritas y subtítulos si es necesario).
        """
        
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            text = response.text
            
            # Parse the custom format
            title = text.split('[TITULO]')[1].split('[DESCRIPCION]')[0].strip()
            description = text.split('[DESCRIPCION]')[1].split('[PROMPT_IMAGEN]')[0].strip()
            image_prompt = text.split('[PROMPT_IMAGEN]')[1].split('[CONTENIDO]')[0].strip()
            content = text.split('[CONTENIDO]')[1].strip()
            
            return {
                "title": title,
                "description": description,
                "image_prompt": image_prompt,
                "content": content
            }
            
        except Exception as e:
            print(f"Error con la API de Gemini (intento {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Esperando 30 segundos antes de reintentar...")
                time.sleep(30)
            else:
                print("Se superó el límite de reintentos.")
                return None
