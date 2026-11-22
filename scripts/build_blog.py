#!/usr/bin/env python3
"""Builds the bilingual ArchDioramas blog as plain static HTML.

Articles: content/posts/en/*.md and content/posts/es/*.md
(YAML front matter + Markdown). The same `key` links an article with
its translation. Run:  python3 scripts/build_blog.py

Outputs: blog/ (English), es/blog/ (Spanish), feeds, sitemap.xml,
robots.txt, llms.txt. Pages are fully readable without JavaScript,
so Google and AI assistants (ChatGPT, Claude, Perplexity, Gemini)
can read every word.
"""
import datetime as dt
import html
import json
import pathlib
import re

import markdown
import yaml

# ====== EDIT HERE when the custom domain is ready (no trailing slash) ======
SITE_URL = "https://archdioramas.vercel.app"
# ============================================================================
SITE_NAME = "ArchDioramas"
YOUTUBE = "https://www.youtube.com/@dioramas-asmr"
SUBSCRIBE = YOUTUBE + "?sub_confirmation=1"

ROOT = pathlib.Path(__file__).resolve().parent.parent
LANGS = ["en", "es"]
BASE = {"en": "/blog/", "es": "/es/blog/"}
LOCALE = {"en": "en_US", "es": "es_MX"}
MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]

T = {
    "en": {
        "plans": "Free plans", "guides": "Guides", "subscribe": "Subscribe",
        "home": "Home", "by": "By ArchDioramas", "updated": "Updated", "read": "min read",
        "takeaways": "KEY TAKEAWAYS", "faq": "Frequently asked questions", "keep": "Keep reading",
        "more": "Read the guide ›",
        "cta1h": "Watch the builds", "cta1p": "Relaxing, voice-free diorama builds from start to finish.",
        "cta1b": "Subscribe on YouTube",
        "cta2h": "Get the free plans", "cta2p": "Printable templates, laser-cut files and STL models that match the videos.",
        "cta2b": "Download free plans",
        "inline": 'Want to see this done? <a href="{sub}">Subscribe to ArchDioramas on YouTube</a> and grab the <a href="/#plans">free plans</a> for each build.',
        "idx_title": "Diorama & Miniature Guides | ArchDioramas",
        "idx_tag": "GUIDES · SCALES · TECHNIQUES", "idx_h1": "Diorama and miniature guides",
        "idx_p": "Clear, practical guides for building dioramas and architectural models, written alongside the builds on our YouTube channel.",
        "idx_desc": "Step-by-step diorama and miniature guides: scales, materials, laser-cut and 3D-printed parts, and techniques from the ArchDioramas YouTube channel.",
        "foot": "Miniatures &amp; Dioramas", "blogname": "ArchDioramas Guides",
        "switch": "Cambiar a español",
        "ih": "What should we build next?",
        "ip": "Tell us what you'd like to see in the next video or guide. We read every idea.",
        "ikind": "It's an idea for", "kv": "A video", "kb": "A blog guide", "kboth": "Both",
        "iidea": "Your idea", "iph": "e.g. a 1:24 coffee shop with working lights",
        "iname": "Your name (optional)", "isend": "Send my idea",
        "iok": "Thanks! Your idea arrived. Subscribe so you don't miss it if we build it.",
        "ierr": "Sorry, it didn't send. Please try again in a moment.",
        "ishort": "Please write a few words about your idea.", "isending": "Sending…",
    },
    "es": {
        "plans": "Planos gratis", "guides": "Guías", "subscribe": "Suscríbete",
        "home": "Inicio", "by": "Por ArchDioramas", "updated": "Actualizado", "read": "min de lectura",
        "takeaways": "PUNTOS CLAVE", "faq": "Preguntas frecuentes", "keep": "Sigue leyendo",
        "more": "Leer la guía ›",
        "cta1h": "Mira las construcciones", "cta1p": "Construcciones de dioramas relajantes y sin voz, de principio a fin.",
        "cta1b": "Suscríbete en YouTube",
        "cta2h": "Descarga los planos gratis", "cta2p": "Plantillas para imprimir, archivos para corte láser y modelos STL de cada video.",
        "cta2b": "Descargar planos gratis",
        "inline": '¿Quieres verlo paso a paso? <a href="{sub}">Suscríbete a ArchDioramas en YouTube</a> y descarga los <a href="/#plans">planos gratis</a> de cada construcción.',
        "idx_title": "Guías de dioramas y miniaturas | ArchDioramas",
        "idx_tag": "GUÍAS · ESCALAS · TÉCNICAS", "idx_h1": "Guías de dioramas y miniaturas",
        "idx_p": "Guías claras y prácticas para construir dioramas y maquetas arquitectónicas, escritas junto con las construcciones de nuestro canal de YouTube.",
        "idx_desc": "Guías paso a paso de dioramas y miniaturas: escalas, materiales, piezas en corte láser e impresión 3D, y técnicas del canal de YouTube de ArchDioramas.",
        "foot": "Miniaturas y dioramas", "blogname": "Guías de ArchDioramas",
        "switch": "Switch to English",
        "ih": "¿Qué construimos después?",
        "ip": "Cuéntanos qué te gustaría ver en el próximo video o guía. Leemos todas las ideas.",
        "ikind": "Es una idea para", "kv": "Un video", "kb": "Una guía del blog", "kboth": "Ambos",
        "iidea": "Tu idea", "iph": "p. ej. una cafetería a 1:24 con luces que encienden",
        "iname": "Tu nombre (opcional)", "isend": "Enviar mi idea",
        "iok": "¡Gracias! Tu idea llegó. Suscríbete para no perdértela si la construimos.",
        "ierr": "Lo sentimos, no se pudo enviar. Inténtalo de nuevo en un momento.",
        "ishort": "Escribe unas palabras sobre tu idea.", "isending": "Enviando…",
    },
}

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800'
         '&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">')

ORG = {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL + "/", "sameAs": [YOUTUBE],
       "description": "ArchDioramas makes miniature dioramas and architectural models and shares "
                      "printable plans, laser-cut files and STL models."}

e = lambda s: html.escape(str(s), quote=True)
# remembers the choice so the home page opens in the same language
SAVE_LANG = "<script>document.querySelectorAll('[data-setlang]').forEach(a=>a.addEventListener('click',()=>{try{localStorage.setItem('ad-lang',a.dataset.setlang)}catch(e){}}))</script>"


def nice_date(s, lang):
    d = dt.date.fromisoformat(s)
    return f"{d.day} de {MONTHS_ES[d.month - 1]} de {d.year}" if lang == "es" else d.strftime("%B %-d, %Y")


def header(lang, other_url):
    t = T[lang]
    other = "es" if lang == "en" else "en"
    on = lambda l: ' class="on"' if l == lang else ""
    return f'''<header class="top"><div class="wrap">
<a class="logo" href="/" data-setlang="{lang}" aria-label="ArchDioramas"><span class="a">arch</span><span class="b">DIORAMAS</span></a>
<nav class="links" aria-label="Main">
<a href="/#plans" data-setlang="{lang}">{t["plans"]}</a>
<a href="{BASE[lang]}" aria-current="page">{t["guides"]}</a>
<a href="{YOUTUBE}">YouTube</a>
<a class="lang" href="{other_url}" hreflang="{other}" data-setlang="{other}" aria-label="{t["switch"]}"><span{on("en")}>EN</span><span{on("es")}>ES</span></a>
<a class="sub" href="{SUBSCRIBE}">{t["subscribe"]}</a>
</nav></div></header>'''


def footer(lang):
    t = T[lang]
    return f'''<footer><div class="wrap">
<span>© {dt.date.today().year} ArchDioramas · {t["foot"]}</span>
<span><a href="{BASE[lang]}">{t["guides"]}</a> · <a href="/#plans" data-setlang="{lang}">{t["plans"]}</a> · <a href="{YOUTUBE}">YouTube</a> · <a href="{BASE[lang]}feed.xml">RSS</a></span>
</div></footer>{SAVE_LANG}{IDEAS_JS}'''


def cta(lang):
    t = T[lang]
    return f'''<aside class="cta">
<div><h3>{t["cta1h"]}</h3><p>{t["cta1p"]}</p><a class="btn" href="{SUBSCRIBE}">{t["cta1b"]}</a></div>
<div><h3>{t["cta2h"]}</h3><p>{t["cta2p"]}</p><a class="btn wood" href="/#plans" data-setlang="{lang}">{t["cta2b"]}</a></div>
</aside>'''


def ideas(lang, page):
    t = T[lang]
    radio = lambda v, label, chk="": f'<label><input type="radio" name="kind" value="{v}"{chk}> {label}</label>'
    return f'''<section class="ideas" id="ideas" aria-labelledby="ideas-h">
<h2 id="ideas-h">{t["ih"]}</h2><p>{t["ip"]}</p>
<form method="post" action="/api/suggest" data-ok="{e(t["iok"])}" data-err="{e(t["ierr"])}" data-short="{e(t["ishort"])}" data-sending="{e(t["isending"])}">
<input type="hidden" name="lang" value="{lang}"><input type="hidden" name="page" value="{e(page)}">
<div class="hp" aria-hidden="true"><label>Website <input name="website" tabindex="-1" autocomplete="off"></label></div>
<fieldset><legend>{t["ikind"]}</legend>{radio("video", t["kv"])}{radio("blog", t["kb"])}{radio("both", t["kboth"], " checked")}</fieldset>
<label class="f">{t["iidea"]}<textarea name="idea" rows="3" maxlength="600" required placeholder="{e(t["iph"])}"></textarea></label>
<div class="row"><label class="f">{t["iname"]}<input name="name" maxlength="60" autocomplete="given-name"></label>
<button class="btn wood" type="submit">{t["isend"]}</button></div>
<p class="msg" role="status" aria-live="polite"></p>
</form></section>'''


IDEAS_JS = """<script>(()=>{const f=document.querySelector('#ideas form');if(!f)return;const m=f.querySelector('.msg'),b=f.querySelector('button');
if(location.hash==='#ideas-ok')m.textContent=f.dataset.ok;if(location.hash==='#ideas-error')m.textContent=f.dataset.err;
f.addEventListener('submit',async ev=>{ev.preventDefault();if(f.idea.value.trim().length<3){m.textContent=f.dataset.short;f.idea.focus();return}
b.disabled=true;m.textContent=f.dataset.sending;try{const r=await fetch(f.action,{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},
body:JSON.stringify(Object.fromEntries(new FormData(f)))});const j=await r.json().catch(()=>({}));if(r.ok&&j.ok){m.textContent=f.dataset.ok;f.idea.value='';f.name.value=''}else m.textContent=f.dataset.err}
catch(e){m.textContent=f.dataset.err}b.disabled=false})})()</script>"""


def head(lang, title, desc, url, alternates, extra=""):
    alt = "".join(f'<link rel="alternate" hreflang="{l}" href="{u}">' for l, u in alternates.items())
    if "en" in alternates:
        alt += f'<link rel="alternate" hreflang="x-default" href="{alternates["en"]}">'
    og_alt = "".join(f'<meta property="og:locale:alternate" content="{LOCALE[l]}">' for l in alternates if l != lang)
    return f'''<!DOCTYPE html>
<html lang="{lang}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">{alt}
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<meta property="og:site_name" content="{SITE_NAME}"><meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(url)}">
<meta property="og:locale" content="{LOCALE[lang]}">{og_alt}
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/rss+xml" title="{T[lang]["blogname"]}" href="{SITE_URL}{BASE[lang]}feed.xml">
{FONTS}
<link rel="stylesheet" href="/blog/blog.css">
{extra}
</head><body>'''


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + "</script>"


def load_posts():
    posts = {l: [] for l in LANGS}
    for lang in LANGS:
        for f in sorted((ROOT / "content" / "posts" / lang).glob("*.md")):
            m = re.match(r"^---\n(.*?)\n---\n(.*)$", f.read_text(encoding="utf-8"), re.S)
            meta, body = yaml.safe_load(m.group(1)), m.group(2)
            if meta.get("draft"):
                continue
            meta.update(lang=lang, slug=meta.get("slug") or f.stem, body_md=body,
                        date=str(meta["date"]), updated=str(meta.get("updated", meta["date"])))
            meta["path"] = f"{BASE[lang]}{meta['slug']}/"
            meta["url"] = SITE_URL + meta["path"]
            posts[lang].append(meta)
        posts[lang].sort(key=lambda p: p["date"], reverse=True)
    by_key = {}
    for lang in LANGS:
        for p in posts[lang]:
            by_key.setdefault(p["key"], {})[lang] = p
    return posts, by_key


def render_post(p, posts, by_key):
    lang, t = p["lang"], T[p["lang"]]
    body = markdown.markdown(p["body_md"], extensions=["tables", "toc", "sane_lists"])
    body = body.replace("<p>{{CTA}}</p>", f'<p class="inline-cta">{t["inline"].format(sub=SUBSCRIBE)}</p>')
    words = len(re.findall(r"\w+", p["body_md"]))
    mins = max(1, round(words / 220))
    versions = by_key[p["key"]]
    alternates = {l: v["url"] for l, v in versions.items()}
    other = "es" if lang == "en" else "en"
    other_url = versions[other]["path"] if other in versions else BASE[other]

    take = "".join(f"<li>{markdown.markdown(x)[3:-4]}</li>" for x in p.get("takeaways", []))
    faq = p.get("faq", [])
    faq_html = ('<section class="faq"><h2>' + t["faq"] + "</h2>" + "".join(
        f"<details open><summary>{e(q['q'])}</summary><p>{e(q['a'])}</p></details>" for q in faq) + "</section>") if faq else ""
    video = ""
    if p.get("video_id"):
        video = (f'<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{e(p["video_id"])}" '
                 f'title="{e(p["title"])}" loading="lazy" allowfullscreen></iframe></div>')
    rel = [x for x in posts[lang] if x["slug"] != p["slug"]][:3]
    related = (f'<section class="related"><h2>{t["keep"]}</h2><ul>' +
               "".join(f'<li><a href="{x["path"]}">{e(x["title"])}</a></li>' for x in rel) +
               "</ul></section>") if rel else ""

    article = {"@type": "BlogPosting", "headline": p["title"], "description": p["description"],
               "datePublished": p["date"], "dateModified": p["updated"], "mainEntityOfPage": p["url"],
               "url": p["url"], "inLanguage": lang, "wordCount": words, "keywords": ", ".join(p.get("tags", [])),
               "author": ORG, "publisher": ORG}
    if other in versions:
        article["workTranslation" if lang == "en" else "translationOfWork"] = {"@id": versions[other]["url"]}
    graph = [article,
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": t["home"], "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": t["guides"], "item": SITE_URL + BASE[lang]},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": p["url"]}]}]
    if faq:
        graph.append({"@type": "FAQPage", "inLanguage": lang, "mainEntity": [
            {"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in faq]})
    if p.get("video_id"):
        graph.append({"@type": "VideoObject", "name": p["title"], "description": p["description"],
                      "uploadDate": p["date"], "thumbnailUrl": f"https://i.ytimg.com/vi/{p['video_id']}/hqdefault.jpg",
                      "embedUrl": f"https://www.youtube.com/embed/{p['video_id']}"})

    out = head(lang, p.get("seo_title", p["title"] + " | ArchDioramas"), p["description"], p["url"], alternates,
               ld({"@context": "https://schema.org", "@graph": graph}) + '<meta property="og:type" content="article">')
    out += header(lang, other_url)
    out += f'''<main><article class="post">
<nav class="crumbs" aria-label="Breadcrumb"><a href="/" data-setlang="{lang}">{t["home"]}</a> / <a href="{BASE[lang]}">{t["guides"]}</a> / {e(p["title"])}</nav>
<div class="sheet">
<span class="tag">{e(" · ".join(x.upper() for x in p.get("tags", [])[:3]))}</span>
<h1>{e(p["title"])}</h1>
<p class="dek">{e(p["description"])}</p>
<p class="meta">{t["by"]} · {t["updated"]} <time datetime="{p["updated"]}">{nice_date(p["updated"], lang)}</time> · {mins} {t["read"]}</p>
{video}
<section class="takeaways"><h2>{t["takeaways"]}</h2><ul>{take}</ul></section>
<div class="content">{body}</div>
{faq_html}
{ideas(lang, p["path"])}
{cta(lang)}
{related}
</div></article></main>{footer(lang)}</body></html>'''
    d = ROOT / p["path"].strip("/")
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(out, encoding="utf-8")


def render_index(lang, posts):
    t = T[lang]
    url = SITE_URL + BASE[lang]
    alternates = {l: SITE_URL + BASE[l] for l in LANGS}
    other = "es" if lang == "en" else "en"
    graph = {"@context": "https://schema.org", "@type": "Blog", "name": t["blogname"], "url": url,
             "description": t["idx_desc"], "publisher": ORG, "inLanguage": lang,
             "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": p["url"],
                           "datePublished": p["date"]} for p in posts]}
    cards = "".join(f'''<a class="post-card" href="{p["path"]}">
<span class="meta">{nice_date(p["updated"], lang)}</span><h2>{e(p["title"])}</h2><p>{e(p["description"])}</p>
<span class="more">{t["more"]}</span></a>''' for p in posts)
    out = head(lang, t["idx_title"], t["idx_desc"], url, alternates, ld(graph)) + header(lang, BASE[other])
    out += f'''<main><div class="wrap">
<section class="intro"><span class="tag">{t["idx_tag"]}</span>
<h1>{t["idx_h1"]}</h1>
<p>{t["idx_p"]}</p></section>
<div class="posts">{cards}</div>
<div class="sheet">{ideas(lang, BASE[lang])}</div>
{cta(lang)}
</div></main>{footer(lang)}</body></html>'''
    d = ROOT / BASE[lang].strip("/")
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(out, encoding="utf-8")


def render_feed(lang, posts):
    items = "".join(f'''<item><title>{e(p["title"])}</title><link>{p["url"]}</link><guid>{p["url"]}</guid>
<pubDate>{dt.datetime.fromisoformat(p["date"]).strftime("%a, %d %b %Y 12:00:00 +0000")}</pubDate>
<description>{e(p["description"])}</description></item>''' for p in posts)
    (ROOT / BASE[lang].strip("/") / "feed.xml").write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>{T[lang]["blogname"]}</title><link>{SITE_URL}{BASE[lang]}</link>
<description>{e(T[lang]["idx_desc"])}</description><language>{lang}</language>{items}</channel></rss>''',
        encoding="utf-8")


def render_seo_files(posts, by_key):
    today = dt.date.today().isoformat()

    def entry(loc, lastmod, alts):
        links = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{u}"/>' for l, u in alts.items())
        return f"<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod>{links}</url>"

    idx_alts = {l: SITE_URL + BASE[l] for l in LANGS}
    rows = [f"<url><loc>{SITE_URL}/</loc><lastmod>{today}</lastmod></url>"]
    for l in LANGS:
        rows.append(entry(SITE_URL + BASE[l], posts[l][0]["updated"] if posts[l] else today, idx_alts))
        for p in posts[l]:
            rows.append(entry(p["url"], p["updated"], {k: v["url"] for k, v in by_key[p["key"]].items()}))
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">' +
        "".join(rows) + "</urlset>\n", encoding="utf-8")

    bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
            "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "Bingbot", "Googlebot"]
    robots = "# Search engines and AI assistants are welcome to read and cite this site.\n"
    robots += "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots)
    robots += f"User-agent: *\nAllow: /\nDisallow: /sugerencias/\nDisallow: /api/\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    (ROOT / "robots.txt").write_text(robots, encoding="utf-8")

    llms = f"""# ArchDioramas

> ArchDioramas builds miniature dioramas and architectural models and shares free printable plans, laser-cut files (SVG/DXF) and 3D-printable STL models. Videos are relaxing, voice-free ASMR builds on YouTube: {YOUTUBE}. Guides are available in English and Spanish.

## Guides (English)
""" + "".join(f"- [{p['title']}]({p['url']}): {p['description']}\n" for p in posts["en"]) + """
## Guías (español)
""" + "".join(f"- [{p['title']}]({p['url']}): {p['description']}\n" for p in posts["es"]) + f"""
## Site
- [Free plans]({SITE_URL}/#plans): free downloadable plans that match each video
- [YouTube channel]({YOUTUBE}): full diorama builds
"""
    (ROOT / "llms.txt").write_text(llms, encoding="utf-8")


if __name__ == "__main__":
    posts, by_key = load_posts()
    for lang in LANGS:
        for p in posts[lang]:
            render_post(p, posts, by_key)
        render_index(lang, posts[lang])
        render_feed(lang, posts[lang])
    render_seo_files(posts, by_key)
    print({l: len(posts[l]) for l in LANGS})
