import ipaddress
import re
import socket
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS


def public_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        return False
    try:
        if parsed.port not in (None, 80, 443):
            return False
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
        return bool(addresses) and all(ipaddress.ip_address(item[4][0]).is_global for item in addresses)
    except (ValueError, OSError):
        return False


def article_date(value):
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        return None


def search_news(queries):
    articles = []
    seen = set()
    warnings = []
    today = datetime.now(timezone.utc)
    cutoff = today - timedelta(days=7)
    for query in queries:
        try:
            results = DDGS(timeout=20).news(query, timelimit='w', max_results=12)
        except Exception:
            warnings.append(f'Search was unavailable for: {query}')
            continue
        for result in results:
            date = article_date(result.get('date'))
            url = result.get('url', '')
            title = result.get('title', '').strip()
            parsed = urlsplit(url)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname:
                continue
            clean_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ''))
            title_key = re.sub(r'\W+', '', title.lower())
            if not date or not cutoff <= date <= today or clean_url in seen or title_key in seen or not title:
                continue
            seen.update((clean_url, title_key))
            articles.append({
                'id': len(articles) + 1,
                'title': title,
                'url': clean_url,
                'publisher': result.get('source') or parsed.hostname,
                'published_at': date.isoformat(),
                'excerpt': result.get('body', '')[:1500],
                'content': '',
                'evidence': 'Search excerpt'
            })
    return articles[:24], warnings


def read_article(url):
    try:
        for attempt in range(4):
            if not public_url(url):
                return ''
            with requests.get(
                url,
                headers={'User-Agent': 'NewsletterAssignment/1.0'},
                timeout=(5, 10),
                allow_redirects=False,
                stream=True
            ) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get('Location', ''))
                    continue
                if response.status_code != 200 or 'text/html' not in response.headers.get('Content-Type', ''):
                    return ''
                data = bytearray()
                for chunk in response.iter_content(16384):
                    data.extend(chunk)
                    if len(data) > 1500000:
                        return ''
                soup = BeautifulSoup(bytes(data), 'html.parser')
                for item in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form']):
                    item.decompose()
                body = soup.find('article') or soup.find('main') or soup
                paragraphs = [p.get_text(' ', strip=True) for p in body.find_all('p')]
                text = '\n'.join(p for p in paragraphs if len(p) > 70)
                return text[:9000]
    except (requests.RequestException, ValueError, OSError):
        return ''
    return ''


def validate_sources(newsletter, sources):
    ids = [story['source_id'] for story in newsletter['stories']]
    valid = {source['id'] for source in sources}
    if len(ids) != len(set(ids)):
        raise ValueError('The draft repeats the same article.')
    if any(source_id not in valid for source_id in ids):
        raise ValueError('The draft includes an unknown source.')


def render_newsletter(newsletter, sources, date):
    validate_sources(newsletter, sources)
    source_map = {source['id']: source for source in sources}
    sections = []
    for index, story in enumerate(newsletter['stories'], 1):
        source = source_map[story['source_id']]
        url = source['url']
        if urlsplit(url).scheme not in ('http', 'https'):
            raise ValueError('The newsletter contains an invalid source link.')
        sections.append(f'''
        <section>
          <div class="meta">{index:02d} / {escape(source['publisher'])} · {escape(source['published_at'][:10])}</div>
          <h2>{escape(story['headline'])}</h2>
          <p>{escape(story['summary'])}</p>
          <p class="why"><strong>Why it matters</strong><br>{escape(story['why_it_matters'])}</p>
          <a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">Read the source ↗</a>
          <span class="evidence">{escape(source['evidence'])}</span>
        </section>''')
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(newsletter['subject'])}</title>
<style>
body {{ margin:0; background:#f3f3ee; color:#242b27; font:16px/1.75 Arial,sans-serif; }}
main {{ max-width:680px; margin:32px auto; background:white; padding:44px; border:1px solid #e3e7df; }}
header {{ border-bottom:3px solid #315e42; padding-bottom:28px; }}
.label {{ color:#477453; font-size:12px; letter-spacing:2px; font-weight:bold; }}
h1 {{ font:36px/1.2 Georgia,serif; margin:20px 0; }}
h2 {{ font:25px/1.3 Georgia,serif; margin:10px 0; }}
section {{ padding:28px 0; border-bottom:1px solid #e3e7df; }}
.meta,.evidence,footer {{ font-size:12px; color:#67736b; }}
.why {{ padding:16px; background:#f3f6f0; font-size:14px; }}
a {{ color:#315e42; font-size:14px; font-weight:bold; }}
.evidence {{ display:block; margin-top:6px; }}
footer {{ padding-top:24px; }}
@media(max-width:600px) {{ main {{ margin:0; padding:24px; }} h1 {{ font-size:30px; }} }}
</style>
</head>
<body><main>
<header><div class="label">THE AGENT EDIT · {escape(date[:10])}</div>
<h1>{escape(newsletter['subject'])}</h1><p>{escape(newsletter['introduction'])}</p></header>
{''.join(sections)}
<footer><p>{escape(newsletter['closing'])}</p><p>Created with Newsletter Agent. Delivery is simulated; no email was sent. Check linked sources for complete reporting.</p></footer>
</main></body></html>'''


def render_markdown(newsletter, sources):
    source_map = {source['id']: source for source in sources}
    lines = [f"# {newsletter['subject']}", '', newsletter['introduction'], '']
    for story in newsletter['stories']:
        source = source_map[story['source_id']]
        lines.extend([
            f"## {story['headline']}", '', story['summary'], '',
            f"**Why it matters:** {story['why_it_matters']}", '',
            f"Source: {source['publisher']} | {source['published_at'][:10]} | {source['url']}",
            f"Evidence: {source['evidence']}", ''
        ])
    lines.extend([newsletter['closing'], '', 'Delivery simulated. No email was sent.'])
    return '\n'.join(lines)
