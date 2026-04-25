import json
import os
import re
import urllib.parse
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv() # Load variables from .env file

from scraper import fetch_latest_news, extract_article_data
from ai_writer import generate_blog_post

HISTORY_FILE = "history.json"
BLOG_POSTS_DIR = "../frontend/src/content/blog"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
        return [item if isinstance(item, dict) else {"link": item, "title": ""} for item in data]
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def is_duplicate(title, history):
    title_words = set(re.findall(r"\w+", title.lower()))
    if len(title_words) < 4: return False
    # Ignorar palabras comunes
    stop_words = {'de', 'la', 'en', 'el', 'un', 'una', 'con', 'por', 'para', 'que', 'y', 'los', 'las'}
    title_words = {w for w in title_words if w not in stop_words}
    
    for item in history:
        if isinstance(item, dict) and item.get("title"):
            h_words = set(re.findall(r"\w+", item["title"].lower()))
            h_words = {w for w in h_words if w not in stop_words}
            if not h_words: continue
            intersection = title_words.intersection(h_words)
            overlap = len(intersection) / min(len(title_words), len(h_words))
            if overlap > 0.6: # 60% de coincidencia en palabras clave
                return True
    return False

def main():
    print("Iniciando proceso automático de blog...")
    history = load_history()
    
    articles = fetch_latest_news()
    
    if not articles:
        print("No se encontraron artículos en el RSS.")
        return
        
    for article in articles:
        if any(isinstance(h, dict) and h.get("link") == article["link"] for h in history) or is_duplicate(article["title"], history):
            print(f"Saltando artículo ya procesado: {article['title']}")
            continue
            
        print(f"Procesando nuevo artículo: {article['title']}")
        
        # 1. Extraer contenido e imagen de la URL
        content, real_image_url = extract_article_data(article["link"])
        if not content:
            print("Advertencia: No se pudo extraer contenido. Usando solo el título.")
            content = "Contenido no disponible para extracción automática."
            
        # 2. Usar IA para generar el post
        generated_data = generate_blog_post(article["title"], content)
        if not generated_data:
            print("Fallo la generación de IA. Saltando...")
            continue
            
        # 3. Determinar imagen (1. Real de la noticia, 2. Internet, 3. IA)
        slug = slugify(generated_data["title"])
        image_path = f"/images/{slug}.jpg"
        full_image_path = os.path.join("../frontend/public", f"images/{slug}.jpg")
        
        try:
            os.makedirs(os.path.dirname(full_image_path), exist_ok=True)
            
            # Capa 1: Imagen real de la noticia
            final_image_url = real_image_url
            
            # Capa 2: Buscar en internet si la capa 1 falló
            if not final_image_url:
                from scraper import search_internet_image
                # Intento 1: Título original
                final_image_url = search_internet_image(article["title"])
                
                # Intento 2: Con términos de calidad si falló el 1
                if not final_image_url:
                    final_image_url = search_internet_image(article["title"], "official wallpaper high res")
            
            # Capa 2.5: Imagen Genérica de Calidad (No IA)
            if not final_image_url:
                print("No se encontró imagen específica. Usando imagen genérica oficial.")
                import random; final_image_url = random.choice(['https://images.unsplash.com/photo-1621259182978-fbf9ad132d88?q=80&w=1024', 'https://images.unsplash.com/photo-1605906302474-3c738c2a97e6?q=80&w=1024', 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?q=80&w=1024', 'https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=1024'])
                
            # Capa 3: Generar con IA si las anteriores fallaron
            if not final_image_url:
                print(f"No se encontró imagen real. Generando imagen con IA para: {slug}")
                image_prompt = urllib.parse.quote(generated_data["image_prompt"] + ", xbox style, high quality, 4k")
                final_image_url = f"https://image.pollinations.ai/prompt/{image_prompt}?model=flux&nologo=true&width=1024&height=576"
            
            print(f"Descargando imagen final: {final_image_url}")
            # Headers to avoid blocks
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            img_response = requests.get(final_image_url, timeout=30, headers=headers)
            
            if img_response.status_code == 200:
                with open(full_image_path, "wb") as f:
                    f.write(img_response.content)
            else:
                print(f"Fallo descarga. Usando placeholder.")
                image_path = "https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?q=80&w=1024"
        except Exception as e:
            print(f"Error gestionando imagen: {e}")
            image_path = ""
            
        # 4. Guardar en el frontend (Astro format)
        today = datetime.now().strftime("%b %d %Y")
        
        markdown_content = f"""---
title: '{generated_data["title"].replace("'", "''")}'
description: '{generated_data["description"].replace("'", "''")}'
pubDate: '{today}'
heroImage: '{image_path}'
---

{generated_data["content"]}
"""
        
        # Make sure directory exists
        os.makedirs(BLOG_POSTS_DIR, exist_ok=True)
        file_path = os.path.join(BLOG_POSTS_DIR, f"{slug}.md")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        print(f"Guardado exitosamente: {file_path}")
        
        # 4. Actualizar historial
        history.append({"link": article["link"], "title": article["title"]})
        save_history(history)
        

    print("Proceso finalizado.")

if __name__ == "__main__":
    main()
