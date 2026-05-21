#!/usr/bin/env python3
"""
fix_images_ci.py — GitHub Actions image fixer for Eradero game blogs.
Finds today's post, downloads a missing/invalid image, updates frontmatter.
Commit/push is handled by the calling workflow.

Env vars:
  SEARCH_SUFFIX — appended to post title for image search (e.g. "PS5 official art")
  BRAND_QUERY   — fallback search for speculative posts
"""

import hashlib
import os
import re
import struct
import subprocess
import tempfile
import urllib.parse
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("ERROR: falta 'requests'. pip install requests")
    raise

BLOG_DIR = "frontend/src/content/blog"
IMAGES_DIR = "frontend/public/images"

SEARCH_SUFFIX = os.environ.get("SEARCH_SUFFIX", "official art")
BRAND_QUERY = os.environ.get("BRAND_QUERY", "")

TODAY = datetime.now(timezone.utc).strftime("%b %d %Y")

HEADERS_WEB = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
HEADERS_DDG = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"}
BAD_WORDS = ["logo", "avatar", "icon", "profile", "placeholder", "blank", "newsletter", "button", "chart", "infographic", "googleusercontent", "gstatic"]
SPECULATIVE_PHRASES = [
    "todavía no tenemos los nombres", "sin confirmar", "por confirmar",
    "podemos especular", "títulos misteriosos", "juegos misteriosos",
    "no se han revelado los títulos", "aún no se conocen",
    "todavía no se sabe", "no se han confirmado",
    "títulos aún no anunciados", "juegos aún no anunciados",
]


def find_today_post():
    if not os.path.exists(BLOG_DIR):
        return None, None
    for fname in os.listdir(BLOG_DIR):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(BLOG_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                head = f.read(600)
            if f"pubDate: '{TODAY}'" in head:
                return fpath, fname
        except Exception:
            pass
    return None, None


def get_hero_image(fpath):
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"heroImage:\s*'([^']*)'", content)
    return m.group(1) if m else ""


def get_post_title(fpath):
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"title:\s*'([^']*)'", content)
    return m.group(1) if m else ""


def is_valid_image_bytes(content):
    return len(content) > 5000 and (content[:2] == b"\xff\xd8" or content[:4] == b"\x89PNG")


def check_image_landscape(content):
    if content[:4] == b"\x89PNG":
        try:
            w = struct.unpack(">I", content[16:20])[0]
            h = struct.unpack(">I", content[20:24])[0]
            if h > w:
                return False
        except Exception:
            pass
    return True


def get_existing_hashes():
    hashes = set()
    if not os.path.exists(IMAGES_DIR):
        return hashes
    for fname in os.listdir(IMAGES_DIR):
        if fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            fpath = os.path.join(IMAGES_DIR, fname)
            try:
                with open(fpath, "rb") as f:
                    hashes.add(hashlib.md5(f.read()).hexdigest())
            except Exception:
                pass
    return hashes


def is_url_ok(url):
    return not any(w in url.lower() for w in BAD_WORDS)


def bing_search(query):
    """Search Bing Images — works from cloud IPs (Azure). Primary search."""
    try:
        r = requests.get(
            f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1",
            headers=HEADERS_WEB, timeout=15
        )
        # Bing embeds direct image URLs in murl fields within the page HTML
        urls = re.findall(r'"murl":"(https?://[^"]+)"', r.text)
        return [u for u in urls[:10] if not any(bad in u.lower() for bad in BAD_WORDS)]
    except Exception as e:
        print(f"  Bing error: {e}")
        return []


def ddg_search(query):
    """Search DuckDuckGo Images — fallback (sometimes blocked from cloud IPs)."""
    try:
        r = requests.get(
            f"https://duckduckgo.com/?q={urllib.parse.quote(query)}",
            headers=HEADERS_DDG, timeout=15
        )
        m = re.search(r"vqd=([\d-]+)", r.text)
        if not m:
            return []
        vqd = m.group(1)
        r2 = requests.get(
            f"https://duckduckgo.com/i.js?l=us-en&o=json&q={urllib.parse.quote(query)}&vqd={vqd}&f=,,,,,&p=1",
            headers=HEADERS_DDG, timeout=15
        )
        return [res.get("image", "") for res in r2.json().get("results", [])[:8] if res.get("image")]
    except Exception as e:
        print(f"  DDG error: {e}")
        return []


def download_image(url, existing_hashes):
    try:
        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as tmp:
            tmp_path = tmp.name
        subprocess.run(
            ["curl", "-s", "-L", "--max-time", "25", "-A", HEADERS_WEB["User-Agent"], url, "-o", tmp_path],
            capture_output=True
        )
        with open(tmp_path, "rb") as f:
            content = f.read()
        os.unlink(tmp_path)
        if not is_valid_image_bytes(content):
            return None
        if not check_image_landscape(content):
            print(f"  Descartada (retrato): {url[:70]}")
            return None
        h = hashlib.md5(content).hexdigest()
        if h in existing_hashes:
            print(f"  Duplicada (hash {h[:8]}…): {url[:70]}")
            return None
        return content
    except Exception as e:
        print(f"  Error descargando {url[:60]}: {e}")
        return None


def find_and_download_image(title, existing_hashes):
    queries = [
        f"{title} {SEARCH_SUFFIX}",
        f"{title} official screenshot",
        title,
    ]
    if BRAND_QUERY:
        queries.append(BRAND_QUERY)
    for query in queries:
        print(f"  Buscando (Bing): {query[:75]}")
        for url in bing_search(query):
            if not is_url_ok(url):
                continue
            content = download_image(url, existing_hashes)
            if content:
                print(f"  Imagen encontrada (Bing): {url[:80]}")
                return content
        # Fallback a DDG si Bing no dio resultados
        for url in ddg_search(query):
            if not is_url_ok(url):
                continue
            content = download_image(url, existing_hashes)
            if content:
                print(f"  Imagen encontrada (DDG): {url[:80]}")
                return content
    return None


def update_hero_image(fpath, image_path):
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(r"heroImage:\s*'[^']*'", f"heroImage: '{image_path}'", content, count=1)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_content)


def is_speculative_post(fpath):
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read().lower()
    body_start = content.find("---", 3)
    body = content[body_start:] if body_start > 0 else content
    return any(phrase in body for phrase in SPECULATIVE_PHRASES)


def main():
    print(f"Fix Images CI — {TODAY} UTC")

    fpath, fname = find_today_post()
    if not fpath:
        print(f"Sin post de hoy ({TODAY}). Nada que hacer.")
        return

    print(f"Post: {fname}")
    hero = get_hero_image(fpath)
    slug = fname.replace(".md", "")
    print(f"heroImage: '{hero}'")

    needs_fix = False
    if not hero:
        print("heroImage vacío → necesita imagen")
        needs_fix = True
    elif not hero.startswith("/images/"):
        print("heroImage es URL externa → necesita imagen local")
        needs_fix = True
    else:
        local_path = os.path.join(IMAGES_DIR, os.path.basename(hero))
        if not os.path.exists(local_path):
            print("Archivo no existe en disco → necesita imagen")
            needs_fix = True
        else:
            with open(local_path, "rb") as f:
                existing = f.read()
            if not is_valid_image_bytes(existing):
                print("Archivo inválido → necesita imagen")
                needs_fix = True
            elif not check_image_landscape(existing):
                print("Imagen retrato → necesita reemplazo landscape")
                needs_fix = True
            else:
                print(f"Imagen OK ({len(existing) // 1024}KB) — sin cambios")
                return

    title = get_post_title(fpath)
    print(f"Título: {title[:80]}")
    existing_hashes = get_existing_hashes()

    if is_speculative_post(fpath) and BRAND_QUERY:
        print("Post especulativo → usando imagen de marca")
        img_bytes = find_and_download_image(BRAND_QUERY, existing_hashes)
    else:
        img_bytes = find_and_download_image(title, existing_hashes)

    if not img_bytes:
        print("No se encontró imagen válida. Post queda sin imagen.")
        return

    os.makedirs(IMAGES_DIR, exist_ok=True)
    dest = os.path.join(IMAGES_DIR, f"{slug}.jpg")
    with open(dest, "wb") as f:
        f.write(img_bytes)
    print(f"Imagen guardada: {dest} ({len(img_bytes) // 1024}KB)")

    update_hero_image(fpath, f"/images/{slug}.jpg")
    print(f"heroImage actualizado: /images/{slug}.jpg")
    print("Listo — el workflow hace el commit.")


if __name__ == "__main__":
    main()
