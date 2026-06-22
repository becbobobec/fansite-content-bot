
import os
import re
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests
import feedparser
from bs4 import BeautifulSoup


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ARTISTS_FILE = Path("artists.txt")
SEEN_FILE = Path("seen.json")
SETTINGS_FILE = Path("settings.json")
CURRENT_YEAR = datetime.utcnow().year

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FanSiteContentBot/1.0)",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
}

EVENT_KEYWORDS = [
    "attends", "arrives", "arrival", "premiere", "screening", "red carpet",
    "film festival", "festival", "gala", "awards", "award", "fashion week",
    "front row", "after party", "after-party", "dinner", "launch",
    "presentation", "photocall", "press conference", "portrait session",
    "party", "show", "ceremony"
]

SIGHTING_KEYWORDS = [
    "celebrity sightings", "celebrity sighting", "sightings in", "seen at",
    "seen arriving", "seen leaving", "seen outside", "spotted", "out and about",
    "leaves", "outside", "arriving at", "departing", "airport", "hotel",
    "restaurant", "studio"
]

PROJECT_KEYWORDS = [
    "joins cast", "join cast", "cast in", "to star", "set to star", "will star",
    "starring", "new movie", "new film", "new series", "new show",
    "upcoming film", "upcoming movie", "upcoming series", "upcoming project",
    "announced", "in development", "greenlit", "renewed", "cancelled",
    "production begins", "begins filming", "starts filming", "filming",
    "wraps filming", "wrapped filming", "on set", "behind the scenes",
    "release date"
]

VIDEO_KEYWORDS = [
    "trailer", "teaser", "official trailer", "first look", "clip", "video",
    "youtube", "netflix released", "hbo released", "prime video released",
    "hulu released", "apple tv"
]

MAGAZINE_KEYWORDS = [
    "cover story", "magazine cover", "covers", "vogue", "elle",
    "harper's bazaar", "vanity fair", "marie claire", "glamour",
    "cosmopolitan", "interview magazine", "photoshoot", "editorial"
]

INTERVIEW_KEYWORDS = [
    "interview", "talks", "opens up", "discusses", "reveals", "conversation",
    "podcast", "late night", "tonight show", "jimmy fallon", "jimmy kimmel",
    "wired", "vanity fair"
]

SOCIAL_KEYWORDS = [
    "instagram", "shared", "posted", "x/twitter", "twitter", "tiktok",
    "social media", "new post"
]

IGNORE_KEYWORDS = [
    "birthday", "biography", "wiki", "net worth", "height", "age",
    "fan account", "best movies", "ranking", "where to watch", "quiz",
    "horoscope", "lookalike", "plastic surgery"
]


def read_json(path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_settings():
    return read_json(SETTINGS_FILE, {
        "send_portuguese_tweet": True,
        "send_english_tweet": True,
        "send_wordpress_suggestion": True,
        "max_alerts_per_artist_per_run": 10,
        "ignore_first_run_old_items": True
    })


def load_artists():
    artists = []
    for line in ARTISTS_FILE.read_text(encoding="utf-8").splitlines():
        name = line.strip()
        if name and not name.startswith("#"):
            artists.append(name)
    return artists


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_title(title):
    title = clean_text(title)
    title = re.sub(r"\s+-\s+[^-]+$", "", title)
    return title


def contains_any(text, keywords):
    lower = text.lower()
    return any(k in lower for k in keywords)


def classify(title):
    text = title.lower()
    if contains_any(text, IGNORE_KEYWORDS):
        return None
    if contains_any(text, EVENT_KEYWORDS):
        return "EVENTO/APARIÇÃO"
    if contains_any(text, SIGHTING_KEYWORDS):
        return "SIGHTING/CANDID"
    if contains_any(text, PROJECT_KEYWORDS):
        return "NOVO PROJETO"
    if contains_any(text, VIDEO_KEYWORDS):
        return "VÍDEO/TRAILER"
    if contains_any(text, MAGAZINE_KEYWORDS):
        return "CAPA/EDITORIAL"
    if contains_any(text, INTERVIEW_KEYWORDS):
        return "ENTREVISTA"
    if contains_any(text, SOCIAL_KEYWORDS):
        return "SOCIAL UPDATE"
    return None


def telegram_send(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Faltam TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID nos Secrets.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    }, timeout=30)
    if not r.ok:
        print("Erro Telegram:", r.status_code, r.text)


def make_id(item):
    raw = f"{item['source']}|{item['artist']}|{item['title']}|{item['link']}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def year_category(category):
    mapping = {
        "EVENTO/APARIÇÃO": "Events",
        "SIGHTING/CANDID": "Candids",
        "NOVO PROJETO": "Projects",
        "VÍDEO/TRAILER": "Videos",
        "CAPA/EDITORIAL": "Magazines & Photoshoots",
        "ENTREVISTA": "Interviews",
        "SOCIAL UPDATE": "Social Media",
    }
    return f"{mapping.get(category, 'News')} > {CURRENT_YEAR}"


def pt_tweet(artist, title, category):
    title = normalize_title(title)
    if category == "EVENTO/APARIÇÃO":
        return f"📸 {artist} compareceu a um novo evento: {title}."
    if category == "SIGHTING/CANDID":
        return f"📸 {artist} foi vista recentemente. Confira: {title}."
    if category == "NOVO PROJETO":
        return f"🎬 Novo projeto! {title}."
    if category == "VÍDEO/TRAILER":
        return f"🎥 Saiu novidade em vídeo envolvendo {artist}: {title}."
    if category == "CAPA/EDITORIAL":
        return f"📖 Novo editorial/capa com {artist}: {title}."
    if category == "ENTREVISTA":
        return f"🎤 Nova entrevista com {artist}: {title}."
    if category == "SOCIAL UPDATE":
        return f"📱 Nova atualização envolvendo {artist}: {title}."
    return f"🔔 Nova atualização sobre {artist}: {title}."


def en_tweet(artist, title, category):
    title = normalize_title(title)
    if category == "EVENTO/APARIÇÃO":
        return f"📸 {artist} attends a new public event: {title}."
    if category == "SIGHTING/CANDID":
        return f"📸 {artist} was recently spotted. More: {title}."
    if category == "NOVO PROJETO":
        return f"🎬 New project! {title}."
    if category == "VÍDEO/TRAILER":
        return f"🎥 New video/trailer update featuring {artist}: {title}."
    if category == "CAPA/EDITORIAL":
        return f"📖 New cover/editorial featuring {artist}: {title}."
    if category == "ENTREVISTA":
        return f"🎤 New interview with {artist}: {title}."
    if category == "SOCIAL UPDATE":
        return f"📱 New social update from/about {artist}: {title}."
    return f"🔔 New update about {artist}: {title}."


def wordpress_title(artist, title):
    title = normalize_title(title)
    if title.lower().startswith(artist.lower()):
        return title
    return f"{artist}: {title}"


def format_alert(item, settings):
    emoji = {
        "EVENTO/APARIÇÃO": "🚨",
        "SIGHTING/CANDID": "📸",
        "NOVO PROJETO": "🎬",
        "VÍDEO/TRAILER": "🎥",
        "CAPA/EDITORIAL": "📖",
        "ENTREVISTA": "🎤",
        "SOCIAL UPDATE": "📱",
    }.get(item["category"], "🔔")

    parts = [
        f"{emoji} {item['category']}",
        "",
        f"Artista: {item['artist']}",
        f"Fonte: {item['source']}",
        "",
        item["title"],
        "",
        item["link"],
    ]

    if settings.get("send_portuguese_tweet", True):
        parts += ["", "Tweet PT:", pt_tweet(item["artist"], item["title"], item["category"])]

    if settings.get("send_english_tweet", True):
        parts += ["", "Tweet EN:", en_tweet(item["artist"], item["title"], item["category"])]

    if settings.get("send_wordpress_suggestion", True):
        parts += ["", "WordPress:", f"Título: {wordpress_title(item['artist'], item['title'])}", f"Categoria: {year_category(item['category'])}"]

    return "\n".join(parts)


def google_news_query(artist):
    query = (
        f'"{artist}" ('
        '"attends" OR "premiere" OR "red carpet" OR "screening" OR "film festival" OR '
        '"celebrity sightings" OR "spotted" OR "seen arriving" OR "seen leaving" OR '
        '"joins cast" OR "set to star" OR "new film" OR "new series" OR "trailer" OR '
        '"first look" OR "release date" OR "begins filming" OR "on set" OR "cover story" OR '
        '"interview" OR "Vogue" OR "Elle" OR "Vanity Fair" OR "magazine cover"'
        ')'
    )
    return quote_plus(query)


def fetch_google_news(artist):
    url = f"https://news.google.com/rss/search?q={google_news_query(artist)}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    results = []

    for entry in feed.entries[:30]:
        title = normalize_title(entry.get("title", ""))
        link = entry.get("link", "")
        if not title or not link:
            continue
        if artist.lower() not in title.lower():
            continue
        category = classify(title)
        if not category:
            continue
        results.append({"artist": artist, "source": "Google News", "title": title, "link": link, "category": category})

    return results


def get_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code >= 400:
            print(f"Status {r.status_code}: {url}")
            return None
        return r.text
    except Exception as exc:
        print(f"Erro ao acessar {url}: {exc}")
        return None


def public_page_links(artist, source, url):
    html = get_page(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []

    if soup.title:
        title = normalize_title(soup.title.get_text(" "))
        category = classify(title)
        if category and artist.lower() in title.lower():
            results.append({"artist": artist, "source": source, "title": title, "link": url, "category": category})

    for a in soup.find_all("a", href=True):
        label = clean_text(a.get("title", "")) or clean_text(a.get("aria-label", "")) or clean_text(a.get_text(" "))
        href = a["href"]

        if not label or artist.lower() not in label.lower():
            continue

        category = classify(label)
        if not category:
            continue

        if href.startswith("http"):
            link = href
        elif href.startswith("/"):
            if "gettyimages" in url:
                link = "https://www.gettyimages.com" + href
            elif "wireimage" in url:
                link = "https://www.wireimage.com" + href
            elif "shutterstock" in url:
                link = "https://www.shutterstock.com" + href
            else:
                link = url
        else:
            link = url

        results.append({"artist": artist, "source": source, "title": normalize_title(label), "link": link, "category": category})

    unique = {}
    for item in results:
        unique[(item["title"], item["link"])] = item
    return list(unique.values())[:10]


def fetch_photo_sites(artist):
    slug = artist.lower().replace(" ", "-")
    query = quote_plus(artist)
    urls = [
        ("Getty Images", f"https://www.gettyimages.com/photos/{slug}?sort=newest"),
        ("WireImage", f"https://www.wireimage.com/search?phrase={query}&sort=newest"),
        ("Shutterstock Editorial", f"https://www.shutterstock.com/editorial/search/{query}?sort=newest"),
    ]

    results = []
    for source, url in urls:
        results.extend(public_page_links(artist, source, url))
        time.sleep(2)
    return results


def dedupe_items(items):
    unique = {}
    for item in items:
        key = (item["artist"], item["category"], item["title"])
        unique[key] = item
    return list(unique.values())


def main():
    settings = load_settings()
    artists = load_artists()
    seen = read_json(SEEN_FILE, {})

    max_per_artist = int(settings.get("max_alerts_per_artist_per_run", 10))
    ignore_first = bool(settings.get("ignore_first_run_old_items", True))
    total_sent = 0

    for artist in artists:
        print(f"Verificando {artist}")

        items = []
        items.extend(fetch_google_news(artist))
        time.sleep(2)
        items.extend(fetch_photo_sites(artist))
        time.sleep(2)

        items = dedupe_items(items)[:max_per_artist]
        init_key = f"initialized::{artist}"

        if ignore_first and init_key not in seen:
            print(f"Primeira execução de {artist}: salvando itens sem enviar.")
            for item in items:
                seen[make_id(item)] = {**item, "first_seen": int(time.time())}
            seen[init_key] = True
            write_json(SEEN_FILE, seen)
            continue

        for item in items:
            uid = make_id(item)
            if uid in seen:
                continue
            seen[uid] = {**item, "first_seen": int(time.time())}
            telegram_send(format_alert(item, settings))
            total_sent += 1
            time.sleep(1)

        write_json(SEEN_FILE, seen)
        time.sleep(2)

    print(f"Concluído. Alertas enviados: {total_sent}")


if __name__ == "__main__":
    main()
