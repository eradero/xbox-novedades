import urllib.parse
import json
import feedparser
from bs4 import BeautifulSoup
import requests

RSS_URL = "https://news.google.com/rss/search?q=xbox+news,+xbox+series+x+news,+xbox+series+s+news,+xbox+game+pass+news,+new+xbox+games,+microsoft+gaming+news&hl=es-419&gl=AR&ceid=AR:es-419"

def fetch_latest_news():
    """Fetches the latest news from the RSS feed."""
    print("Buscando noticias en Google News...")
    feed = feedparser.parse(RSS_URL)
    
    articles = []
    for entry in feed.entries[:5]: # Get top 5 recent
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
        })
    return articles

def extract_article_data(url):
    """Attempts to extract the main text content and lead image from a URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text
        paragraphs = soup.find_all('p')
        content = "\n".join([p.get_text() for p in paragraphs if len(p.get_text()) > 20])
        
        # Extract image (Open Graph image is usually the best lead image)
        image_url = ""
        og_image = soup.find("meta", property="og:image")
        if og_image:
            candidate = og_image.get("content", "")
            if candidate and "googleusercontent.com" not in candidate and "gstatic.com" not in candidate:
                image_url = candidate
        
        return content, image_url
    except Exception as e:
        print(f"Error extrayendo {url}: {e}")
        return "", ""


def is_valid_image(url):
    if not url: return False
    url_lower = url.lower()
    
    # Ignorar imágenes de Google News (miniaturas de baja calidad)
    if "googleusercontent.com" in url_lower or "gstatic.com" in url_lower:
        return False
        
    # Ignorar imágenes que parecen ser miniaturas por su URL (ej: s150, w300)
    import re
    if re.search(r'[=s](1|2|3)00', url_lower): # s100, s200, s300 etc
        return False

    bad_words = ['logo', 'avatar', 'icon', 'profile', 'default', 'placeholder', 'blank', 'header-bg', 'newsletter', 'button']
    return not any(word in url_lower for word in bad_words)

def search_internet_image(query, extra_term=""):
    """Searches for an image on the internet (Bing) as a fallback."""
    try:
        search_query = f"{query} {extra_term}".strip()
        print(f"Buscando imagen en internet para: {search_query}")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        url = f"https://www.bing.com/images/search?q={urllib.parse.quote(search_query)}"
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Bing images are in <a> tags with class "iusc"
        import json
        for a in soup.find_all("a", class_="iusc"):
            m = a.get("m")
            if m:
                data = json.loads(m)
                img_url = data.get("murl")
                if img_url and img_url.startswith("http") and is_valid_image(img_url):
                    import re
                    clean_url = re.sub(r'^https?://', '', img_url)
                    return f"https://wsrv.nl/?url={clean_url}"
        return ""
    except Exception as e:
        print(f"Error buscando imagen en internet: {e}")
        return ""
