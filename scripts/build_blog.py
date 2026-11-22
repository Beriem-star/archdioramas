#!/usr/bin/env python3
"""Builds the ArchDioramas blog as plain static HTML.

Articles live in content/posts/*.md (YAML front matter + Markdown).
Run:  python3 scripts/build_blog.py
Outputs: blog/index.html, blog/<slug>/index.html, blog/feed.xml,
         sitemap.xml, robots.txt, llms.txt
Pages are fully readable without JavaScript, so Google and AI crawlers
(ChatGPT, Claude, Perplexity, Gemini) can read every word.
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
POSTS_DIR = ROOT / "content" / "posts"
BLOG_DIR = ROOT / "blog"

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800'
         '&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">')

ORG = {
    "@type": "Organization",
    "name": SITE_NAME,
    "url": SITE_URL + "/",
    "sameAs": [YOUTUBE],
    "description": "ArchDioramas makes miniature dioramas and architectural models and shares "
                   "printable plans, laser-cut files and STL models.",
}

e = lambda s: html.escape(str(s), quote=True)


def header(active=""):
    cur = ' aria-current="page"'
    return f'''<header class="top"><div class="wrap">
<a class="logo" href="/" aria-label="ArchDioramas home"><span class="a">arch</span><span class="b">DIORAMAS</span></a>
<nav class="links" aria-label="Main">
<a href="/#plans">Free plans</a>
<a href="/blog/"{cur if active == "blog" else ""}>Guides</a>
<a href="{YOUTUBE}">YouTube</a>
<a class="sub" href="{SUBSCRIBE}">Subscribe</a>
</nav></div></header>'''


FOOTER = f'''<footer><div class="wrap">
<span>© {dt.date.today().year} ArchDioramas · Miniatures &amp; Dioramas</span>
<span><a href="/blog/">Guides</a> · <a href="/#plans">Free plans</a> · <a href="{YOUTUBE}">YouTube</a> · <a href="/blog/feed.xml">RSS</a></span>
</div></footer>'''

CTA = f'''<aside class="cta" aria-label="Keep building with ArchDioramas">
<div><h3>Watch the builds</h3><p>Relaxing, voice-free diorama builds from start to finish.</p>
<a class="btn" href="{SUBSCRIBE}">Subscribe on YouTube</a></div>
<div><h3>Get the free plans</h3><p>Printable templates, laser-cut files and STL models that match the videos.</p>
<a class="btn wood" href="/#plans">Download free plans</a></div>
</aside>'''


def head(title, desc, url, extra=""):
    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<meta property="og:site_name" content="{SITE_NAME}"><meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(url)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/rss+xml" title="ArchDioramas Guides" href="{SITE_URL}/blog/feed.xml">
{FONTS}
<link rel="stylesheet" href="/blog/blog.css">
{extra}
</head><body>'''


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + "</script>"


def load_posts():
    posts = []
    for f in sorted(POSTS_DIR.glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
        meta, body = yaml.safe_load(m.group(1)), m.group(2)
        if meta.get("draft"):
            continue
        meta["slug"] = meta.get("slug") or f.stem
        meta["date"] = str(meta["date"])
        meta["updated"] = str(meta.get("updated", meta["date"]))
        meta["url"] = f"{SITE_URL}/blog/{meta['slug']}/"
        meta["body_md"] = body
        posts.append(meta)
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def nice_date(s):
    return dt.date.fromisoformat(s).strftime("%B %-d, %Y")


def render_post(p, posts):
    body = markdown.markdown(p["body_md"], extensions=["tables", "toc", "sane_lists"])
    body = body.replace("<p>{{CTA}}</p>",
        f'<p class="inline-cta">Want to see this done? <a href="{SUBSCRIBE}">Subscribe to ArchDioramas on YouTube</a> '
        f'and grab the <a href="/#plans">free plans</a> for each build.</p>')
    words = len(re.findall(r"\w+", p["body_md"]))
    mins = max(1, round(words / 220))

    take = "".join(f"<li>{markdown.markdown(t)[3:-4]}</li>" for t in p.get("takeaways", []))
    faq = p.get("faq", [])
    faq_html = ""
    if faq:
        faq_html = '<section class="faq"><h2>Frequently asked questions</h2>' + "".join(
            f"<details open><summary>{e(q['q'])}</summary><p>{e(q['a'])}</p></details>" for q in faq) + "</section>"
    video = ""
    if p.get("video_id"):
        video = (f'<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{e(p["video_id"])}" '
                 f'title="{e(p["title"])}" loading="lazy" allowfullscreen></iframe></div>')
    rel = [x for x in posts if x["slug"] != p["slug"]][:3]
    related = ('<section class="related"><h2>Keep reading</h2><ul>' +
               "".join(f'<li><a href="/blog/{x["slug"]}/">{e(x["title"])}</a></li>' for x in rel) +
               "</ul></section>") if rel else ""

    graph = [
        {"@type": "BlogPosting", "headline": p["title"], "description": p["description"],
         "datePublished": p["date"], "dateModified": p["updated"], "mainEntityOfPage": p["url"],
         "url": p["url"], "inLanguage": "en", "wordCount": words, "keywords": ", ".join(p.get("tags", [])),
         "author": ORG, "publisher": ORG},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "Guides", "item": SITE_URL + "/blog/"},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": p["url"]}]},
    ]
    if faq:
        graph.append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in faq]})
    if p.get("video_id"):
        graph.append({"@type": "VideoObject", "name": p["title"], "description": p["description"],
                      "uploadDate": p["date"], "thumbnailUrl": f"https://i.ytimg.com/vi/{p['video_id']}/hqdefault.jpg",
                      "embedUrl": f"https://www.youtube.com/embed/{p['video_id']}"})

    out = head(p.get("seo_title", p["title"] + " | ArchDioramas"), p["description"], p["url"],
               ld({"@context": "https://schema.org", "@graph": graph}) +
               '<meta property="og:type" content="article">')
    out += header("blog")
    out += f'''<main><article class="post">
<nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a> / <a href="/blog/">Guides</a> / {e(p["title"])}</nav>
<div class="sheet">
<span class="tag">{e(" · ".join(t.upper() for t in p.get("tags", [])[:3]))}</span>
<h1>{e(p["title"])}</h1>
<p class="dek">{e(p["description"])}</p>
<p class="meta">By ArchDioramas · Updated <time datetime="{p["updated"]}">{nice_date(p["updated"])}</time> · {mins} min read</p>
{video}
<section class="takeaways"><h2>KEY TAKEAWAYS</h2><ul>{take}</ul></section>
<div class="content">{body}</div>
{faq_html}
{CTA}
{related}
</div></article></main>{FOOTER}</body></html>'''
    d = BLOG_DIR / p["slug"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(out, encoding="utf-8")


def render_index(posts):
    url = SITE_URL + "/blog/"
    desc = ("Step-by-step diorama and miniature guides: scales, materials, laser-cut and 3D-printed parts, "
            "and techniques from the ArchDioramas YouTube channel.")
    graph = {"@context": "https://schema.org", "@type": "Blog", "name": "ArchDioramas Guides", "url": url,
             "description": desc, "publisher": ORG, "inLanguage": "en",
             "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": p["url"],
                           "datePublished": p["date"]} for p in posts]}
    cards = "".join(f'''<a class="post-card" href="/blog/{p["slug"]}/">
<span class="meta">{nice_date(p["updated"])}</span><h2>{e(p["title"])}</h2><p>{e(p["description"])}</p>
<span class="more">Read the guide ›</span></a>''' for p in posts)
    out = head("Diorama & Miniature Guides | ArchDioramas", desc, url, ld(graph)) + header("blog")
    out += f'''<main><div class="wrap">
<section class="intro"><span class="tag">GUIDES · SCALES · TECHNIQUES</span>
<h1>Diorama and miniature guides</h1>
<p>Clear, practical guides for building dioramas and architectural models, written alongside the builds on our YouTube channel.</p></section>
<div class="posts">{cards}</div>
{CTA}
</div></main>{FOOTER}</body></html>'''
    (BLOG_DIR / "index.html").write_text(out, encoding="utf-8")


def render_feed(posts):
    items = "".join(f'''<item><title>{e(p["title"])}</title><link>{p["url"]}</link><guid>{p["url"]}</guid>
<pubDate>{dt.datetime.fromisoformat(p["date"]).strftime("%a, %d %b %Y 12:00:00 +0000")}</pubDate>
<description>{e(p["description"])}</description></item>''' for p in posts)
    (BLOG_DIR / "feed.xml").write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>ArchDioramas Guides</title><link>{SITE_URL}/blog/</link>
<description>Diorama and miniature guides from ArchDioramas</description><language>en</language>{items}</channel></rss>''',
        encoding="utf-8")


def render_seo_files(posts):
    today = dt.date.today().isoformat()
    urls = [(SITE_URL + "/", today), (SITE_URL + "/blog/", posts[0]["updated"] if posts else today)]
    urls += [(p["url"], p["updated"]) for p in posts]
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
        "".join(f"<url><loc>{u}</loc><lastmod>{d}</lastmod></url>" for u, d in urls) + "</urlset>\n", encoding="utf-8")

    bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
            "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "Bingbot", "Googlebot"]
    robots = "# Search engines and AI assistants are welcome to read and cite this site.\n"
    robots += "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots)
    robots += f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    (ROOT / "robots.txt").write_text(robots, encoding="utf-8")

    llms = f"""# ArchDioramas

> ArchDioramas builds miniature dioramas and architectural models and shares free printable plans, laser-cut files (SVG/DXF) and 3D-printable STL models. Videos are relaxing, voice-free ASMR builds on YouTube: {YOUTUBE}

## Guides
""" + "".join(f"- [{p['title']}]({p['url']}): {p['description']}\n" for p in posts) + f"""
## Site
- [Free plans]({SITE_URL}/#plans): free downloadable plans that match each video
- [YouTube channel]({YOUTUBE}): full diorama builds
"""
    (ROOT / "llms.txt").write_text(llms, encoding="utf-8")


if __name__ == "__main__":
    posts = load_posts()
    for p in posts:
        render_post(p, posts)
    render_index(posts)
    render_feed(posts)
    render_seo_files(posts)
    print(f"Built {len(posts)} posts")
