import urllib.parse
import json
import feedparser
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta, timezone

RSS_URL = "https://news.google.com/rss/search?q=xbox+game+pass+microsoft+xbox+series&hl=en&gl=US&ceid=US:en"

MAX_AGE_DAYS = 7

def fetch_latest_news():
    """Fetches the latest news from the RSS feed, skipping articles older than MAX_AGE_DAYS."""
    print("Buscando noticias en Google News...")
    feed = feedparser.parse(RSS_URL)
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)

    articles = []
    for entry in feed.entries[:5]:
        try:
            pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if pub < cutoff:
                print(f"Saltando noticia vieja ({pub.date()}): {entry.title[:60]}")
                continue
        except Exception:
            pass
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
    """Searches for an image on DuckDuckGo."""
    try:
        import re
        search_query = f"{query} official art".strip()
        print(f"Buscando imagen en internet para: {search_query}")
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"}

        r = requests.get(f"https://duckduckgo.com/?q={urllib.parse.quote(search_query)}", headers=headers, timeout=10)
        vqd_match = re.search(r'vqd=([\d-]+)', r.text)
        if not vqd_match:
            return ""
        vqd = vqd_match.group(1)

        img_api = f"https://duckduckgo.com/i.js?l=us-en&o=json&q={urllib.parse.quote(search_query)}&vqd={vqd}&f=,,,,,&p=1"
        r2 = requests.get(img_api, headers=headers, timeout=10)
        for result in r2.json().get("results", []):
            img_url = result.get("image", "")
            if img_url and img_url.startswith("http") and is_valid_image(img_url):
                return img_url
        return ""
    except Exception as e:
        print(f"Error buscando imagen en internet: {e}")
        return ""
