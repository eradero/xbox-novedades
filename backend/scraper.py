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
            image_url = og_image.get("content", "")
        
        return content, image_url
    except Exception as e:
        print(f"Error extrayendo {url}: {e}")
        return "", ""
