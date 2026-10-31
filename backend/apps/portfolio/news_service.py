import os
import re
import json
import requests
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from django.conf import settings
from .models import StockHolding, StockNewsArticle
from .services import normalize_ticker
from .identity import asset_identity, news_query, classify_news, canonical_url, revalidate_stored_news
from apps.bot.leases import leased


def clean_ticker_for_search(ticker: str) -> str:
    """ Ticker   PTT.BK -> PTT, BTC-USD -> Bitcoin"""
    clean = ticker.strip().upper()
    if clean.endswith('.BK'):
        return clean[:-3]
    if clean.endswith('-USD'):
        base = clean[:-4]
        if base == 'BTC':
            return 'Bitcoin'
        elif base == 'ETH':
            return 'Ethereum'
        elif base == 'SOL':
            return 'Solana'
        return base
    return clean


def resolve_news_url(url: str) -> str:
    """ URL  Google News RSS  Destination URL """
    if not url:
        return ''
    if 'news.google.com' in url:
        try:
            from googlenewsdecoder import gnewsdecoder
            res = gnewsdecoder(url)
            if res.get('status') or res.get('success'):
                decoded = res.get('decoded_url')
                if decoded and decoded.startswith('http'):
                    return decoded
        except Exception:
            pass
    return url


def scrape_article_content(url: str, timeout: int = 8) -> Dict[str, str]:
    """
    Scrapes news article body and lead paragraph from original source URL.
    Returns: {'lead': '...', 'full_text': '...', 'resolved_url': '...'}
    """
    resolved_url = resolve_news_url(url)
    lead = ''
    full_text = ''

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
    }

    try:
        from curl_cffi import requests as cffi_requests
        resp = cffi_requests.get(resolved_url, impersonate='chrome120', headers=headers, timeout=timeout)
        status_code = resp.status_code
        html = resp.text
    except Exception:
        try:
            import requests as py_requests
            resp = py_requests.get(resolved_url, headers=headers, timeout=timeout, allow_redirects=True)
            status_code = resp.status_code
            html = resp.text
        except Exception as e:
            return {'lead': lead, 'full_text': full_text, 'resolved_url': resolved_url}

    if status_code != 200 or not html:
        return {'lead': lead, 'full_text': full_text, 'resolved_url': resolved_url}

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # 0. Extract JSON-LD metadata and articleBody BEFORE removing <script> tags
        json_ld_body = ''
        json_ld_lead = ''
        for script in soup.find_all('script', attrs={'type': 'application/ld+json'}):
            try:
                raw_json = script.string or script.get_text()
                if not raw_json:
                    continue
                data = json.loads(raw_json.strip())
                items = data if isinstance(data, list) else [data]
                expanded_items = []
                for it in items:
                    if isinstance(it, dict) and '@graph' in it and isinstance(it['@graph'], list):
                        expanded_items.extend(it['@graph'])
                    else:
                        expanded_items.append(it)

                for item in expanded_items:
                    if not isinstance(item, dict):
                        continue
                    schema_type = str(item.get('@type', '')).lower()
                    if any(t in schema_type for t in ['article', 'newsarticle', 'report', 'blogposting']):
                        body = item.get('articleBody') or item.get('text')
                        if body and len(body.strip()) > len(json_ld_body):
                            json_ld_body = body.strip()
                        desc = item.get('description')
                        if desc and not json_ld_lead:
                            json_ld_lead = desc.strip()
            except Exception:
                continue

        # Remove non-content HTML tags
        for tag in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav', 'aside', 'form', 'svg']):
            tag.decompose()

        # 1. Extract Meta Description (lead summary)
        desc_tag = (
            soup.find('meta', attrs={'name': 'description'})
            or soup.find('meta', attrs={'property': 'og:description'})
            or soup.find('meta', attrs={'name': 'twitter:description'})
        )
        if desc_tag and desc_tag.get('content'):
            lead = desc_tag['content'].strip()
        elif json_ld_lead:
            lead = json_ld_lead

        # 2. Locate main article body (select best container by content volume, not just first <article>)
        skip_phrases = [
            'all rights reserved', 'cookie policy', 'privacy policy',
            'terms of service', 'terms of use', 'sign up for', 'subscribe to',
            'read more:', 'click here', 'advertisement', 'photo by',
            'getty images', 'follow us on'
        ]
        noise_prefixes = re.compile(
            r'^(share|tweet|email|print|save|subscribe|sign up|advertisement|sponsored|click here|all rights reserved|photo by|photo:|image credit:)\b',
            re.I
        )

        def is_meaningful_paragraph(text: str) -> bool:
            clean = text.strip()
            if not clean:
                return False
            lower = clean.lower()
            if any(phrase in lower for phrase in skip_phrases):
                return False
            if noise_prefixes.search(lower):
                return False
            words = clean.split()
            if len(words) >= 2:
                return True
            if len(words) == 1 and bool(re.search(r'[\d%$\u0e00-\u0e7f]', clean)) and len(clean) >= 3:
                return True
            return False

        def extract_paragraphs(element):
            paras = []
            if not element:
                return paras
            for p in element.find_all('p'):
                text = p.get_text().strip()
                if is_meaningful_paragraph(text):
                    paras.append(text)
            return paras

        candidates = []
        for art in soup.find_all('article'):
            candidates.append(art)
        for cdiv in soup.find_all('div', class_=re.compile(r'caas-body|article-body|story-body|entry-content|wysiwyg|post-content', re.I)):
            candidates.append(cdiv)
        main_tag = soup.find('main') or soup.find(attrs={'role': 'main'})
        if main_tag:
            candidates.append(main_tag)

        best_paragraphs = []
        for cand in candidates:
            cand_paras = extract_paragraphs(cand)
            if sum(len(p) for p in cand_paras) > sum(len(p) for p in best_paragraphs):
                best_paragraphs = cand_paras

        # If candidates returned insufficient text, fallback to entire body
        if sum(len(p) for p in best_paragraphs) < 100 and soup.body:
            body_paras = extract_paragraphs(soup.body)
            if sum(len(p) for p in body_paras) > sum(len(p) for p in best_paragraphs):
                best_paragraphs = body_paras

        full_text = '\n\n'.join(best_paragraphs)

        # Prefer JSON-LD articleBody if HTML paragraph extraction yielded less content
        if json_ld_body and len(json_ld_body) > len(full_text):
            full_text = json_ld_body

        if not lead and best_paragraphs:
            lead = best_paragraphs[0]
        elif not lead and json_ld_body:
            lead = json_ld_body[:300]
    except Exception as e:
        print(f"Notice: Parsing failed for {resolved_url}: {e}")

    return {
        'lead': lead.strip(),
        'full_text': full_text.strip(),
        'resolved_url': resolved_url
    }


def fetch_from_yahoo_finance(ticker: str, limit: int = 3) -> List[Dict[str, Any]]:
    """ Yahoo Finance Search API  Scrape """
    articles = []
    clean_search = clean_ticker_for_search(ticker)
    try:
        import yfinance as yf
        search_target = asset_identity(ticker)['name']
        search_res = yf.Search(search_target, news_count=limit)
        news_items = getattr(search_res, 'news', []) or []

        for item in news_items:
            url = item.get('link')
            title = item.get('title')
            if not url or not title:
                continue

            pub_ts = item.get('providerPublishTime')
            pub_date = (
                datetime.fromtimestamp(pub_ts, tz=timezone.utc)
                if pub_ts
                else datetime.now(timezone.utc)
            )

            thumb_url = ''
            thumb = item.get('thumbnail')
            if thumb and isinstance(thumb, dict) and 'resolutions' in thumb:
                res_list = thumb.get('resolutions', [])
                if res_list:
                    thumb_url = res_list[0].get('url', '')

            articles.append({
                'ticker': ticker,
                'title': title.strip(),
                'source': item.get('publisher', 'Yahoo Finance'),
                'url': url.strip(),
                'published_at': pub_date,
                'thumbnail_url': thumb_url,
                'summary': '',
                'related_tickers': item.get('relatedTickers', [])
            })
    except Exception as e:
        print(f"Warning: Failed to fetch Yahoo Finance news for {ticker}: {e}")

    return articles


def fetch_from_google_news(ticker: str, limit: int = 3) -> List[Dict[str, Any]]:
    """ Google News Financial RSS ()"""
    articles = []
    clean_search = clean_ticker_for_search(ticker)

    if ticker.endswith('.BK'):
        query = f"{clean_search} stock when:3d"
        hl, gl, ceid = "th", "TH", "TH:th"
    elif ticker.endswith('-USD'):
        query = f"{clean_search} crypto when:3d"
        hl, gl, ceid = "en-US", "US", "US:en"
    else:
        query = f"{ticker} stock when:3d"
        hl, gl, ceid = "en-US", "US", "US:en"

    query = news_query(ticker)
    encoded_q = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl={hl}&gl={gl}&ceid={ceid}"

    try:
        req = urllib.request.Request(
            rss_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            root = ET.fromstring(res.read())
            items = root.findall('.//item')[:limit]

            for item in items:
                title_elem = item.find('title')
                link_elem = item.find('link')
                source_elem = item.find('source')
                pub_elem = item.find('pubDate')

                if title_elem is None or not title_elem.text:
                    continue

                title = title_elem.text.strip()
                url = link_elem.text.strip() if link_elem is not None and link_elem.text else ''
                source = source_elem.text.strip() if source_elem is not None and source_elem.text else 'Google News'

                if ' - ' in title:
                    title = title.rsplit(' - ', 1)[0].strip()

                pub_date = datetime.now(timezone.utc)
                if pub_elem is not None and pub_elem.text:
                    try:
                        from email.utils import parsedate_to_datetime
                        pub_date = parsedate_to_datetime(pub_elem.text)
                    except Exception:
                        pass

                if url:
                    articles.append({
                        'ticker': ticker,
                        'title': title,
                        'source': source,
                        'url': url,
                        'published_at': pub_date,
                        'thumbnail_url': '',
                        'summary': ''
                    })
    except Exception as e:
        print(f"Warning: Failed to fetch Google News RSS for {ticker}: {e}")

    return articles


def translate_edge_batch(texts: List[str]) -> List[Optional[str]]:
    """
    Microsoft Edge AI Translation Endpoint.
    Returns list of translated strings or None for failed items.
    """
    if not texts:
        return []

    url = "https://edge.microsoft.com/translate/translatetext"
    params = {"from": "", "to": "th", "isEnterpriseClient": "false"}
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
    }

    results = []
    chunk_size = 12
    for i in range(0, len(texts), chunk_size):
        sub_list = texts[i:i+chunk_size]
        try:
            r = requests.post(url, params=params, headers=headers, json=sub_list, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for item in data:
                    t_text = item.get('translations', [{}])[0].get('text', '')
                    if t_text:
                        results.append(t_text)
                    else:
                        results.append(None)
            else:
                results.extend([None] * len(sub_list))
        except Exception as e:
            results.extend([None] * len(sub_list))

    return results


def _translate_single_rpc_chunk(chunk: str) -> str:
    """Helper to translate a single text chunk (<= 2800 chars) through the 4-tier engine."""
    clean_text = chunk.strip()
    if not clean_text:
        return ''
    if bool(re.search(r'[\u0e00-\u0e7f]', clean_text)):
        return clean_text

    # 1. Tier 1: Microsoft Edge AI Translator (fast, accurate, no rate limit)
    try:
        edge_res = translate_edge_batch([clean_text])
        if edge_res and edge_res[0]:
            if bool(re.search(r'[\u0e00-\u0e7f]', edge_res[0])) or not bool(re.search(r'[a-zA-Z]', clean_text)):
                return edge_res[0]
    except Exception:
        pass

    # 2. Tier 2: Google Translate RPC with client rotation
    clients = ['it', 'at', 'dict-chrome-ex']
    try:
        from curl_cffi import requests as cffi_requests
        for client in clients:
            try:
                url = f"https://translate.googleapis.com/translate_a/single?client={client}&sl=auto&tl=th&dt=t"
                r = cffi_requests.post(url, data={'q': clean_text[:2800]}, impersonate='chrome124', timeout=5)
                if r.status_code == 200:
                    res_data = r.json()
                    if res_data and res_data[0]:
                        translated = ''.join([part[0] for part in res_data[0] if part and part[0]]).strip()
                        if bool(re.search(r'[\u0e00-\u0e7f]', translated)):
                            return translated
            except Exception:
                continue
    except ImportError:
        pass

    # 3. Tier 3: Google Translate via urllib
    for client in clients:
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client={client}&sl=auto&tl=th&dt=t"
            data = urllib.parse.urlencode({'q': clean_text[:2500]}).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, timeout=5) as res:
                res_data = json.loads(res.read().decode('utf-8'))
                if res_data and res_data[0]:
                    translated = ''.join([part[0] for part in res_data[0] if part and part[0]]).strip()
                    if bool(re.search(r'[\u0e00-\u0e7f]', translated)):
                        return translated
        except Exception:
            continue

    # 4. Tier 4: MyMemory API Fallback
    try:
        sub_chunks = [clean_text[i:i+450] for i in range(0, min(len(clean_text), 1500), 450)]
        trans_parts = []
        for chunk in sub_chunks:
            mm_url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(chunk)}&langpair=en|th"
            req = urllib.request.Request(mm_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=5) as res:
                mm_data = json.loads(res.read().decode('utf-8'))
                part = mm_data.get('responseData', {}).get('translatedText', '')
                if part and bool(re.search(r'[\u0e00-\u0e7f]', part)):
                    trans_parts.append(part)
        if trans_parts:
            return ' '.join(trans_parts)
    except Exception:
        pass

    return clean_text


def _chunk_text_safely(text: str, max_chars: int = 2400) -> List[str]:
    """
    Safely divides text into chunks of at most `max_chars` without cutting off trailing content.
    Splits along natural boundaries (paragraphs -> sentences -> words -> characters).
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    units = []
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if len(line) <= max_chars:
            units.append(line)
        else:
            sentences = re.split(r'(?<=[.!?])\s+', line)
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                if len(s) <= max_chars:
                    units.append(s)
                else:
                    words = s.split(' ')
                    curr_word_chunk = []
                    curr_word_len = 0
                    for w in words:
                        if not w:
                            continue
                        if len(w) > max_chars:
                            if curr_word_chunk:
                                units.append(' '.join(curr_word_chunk))
                                curr_word_chunk = []
                                curr_word_len = 0
                            for i in range(0, len(w), max_chars):
                                units.append(w[i:i+max_chars])
                        elif curr_word_len + len(w) + (1 if curr_word_chunk else 0) > max_chars:
                            units.append(' '.join(curr_word_chunk))
                            curr_word_chunk = [w]
                            curr_word_len = len(w)
                        else:
                            curr_word_chunk.append(w)
                            curr_word_len += len(w) + (1 if len(curr_word_chunk) > 1 else 0)
                    if curr_word_chunk:
                        units.append(' '.join(curr_word_chunk))

    chunks = []
    current_chunk = []
    current_len = 0
    for u in units:
        added_len = len(u) + (1 if current_chunk else 0)
        if current_len + added_len > max_chars and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [u]
            current_len = len(u)
        else:
            current_chunk.append(u)
            current_len += added_len
    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks


def translate_rpc(text: str) -> str:
    """
    Translates arbitrary length text into Thai without truncating trailing paragraphs.
    Splits long inputs into natural sentence/paragraph/word chunks <= 2400 chars.
    """
    if not text or not text.strip():
        return ''

    clean_text = text.strip()
    if bool(re.search(r'[\u0e00-\u0e7f]', clean_text)):
        return clean_text

    chunks = _chunk_text_safely(clean_text, max_chars=2400)
    if not chunks:
        return clean_text

    results = []
    for c in chunks:
        results.append(_translate_single_rpc_chunk(c))
    return ' '.join(results)


def translate_full_text(text: str) -> str:
    """
    Translates full article content across all paragraphs.
    Uses Edge Batch Translation with paragraph fallback.
    """
    if not text or not text.strip():
        return ''

    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        return ''

    # 1. Translate all paragraphs via Microsoft Edge Batch Translator
    edge_results = translate_edge_batch(paragraphs)

    final_paras = []
    for idx, orig_p in enumerate(paragraphs):
        translated = edge_results[idx] if idx < len(edge_results) else None
        if translated and (bool(re.search(r'[\u0e00-\u0e7f]', translated)) or not bool(re.search(r'[a-zA-Z]', orig_p))):
            final_paras.append(translated)
        else:
            fallback_res = translate_rpc(orig_p)
            final_paras.append(fallback_res if fallback_res else orig_p)

    return '\n\n'.join(final_paras)


def translate_with_gemini(
    title: str,
    ticker: str,
    lead: str,
    content: str,
    api_key: str
) -> Optional[Dict[str, str]]:
    """
    Translates and generates Executive Summary plus full content via Google Gemini AI.
    Returns JSON: {"title_th": "...", "summary_th": "...", "content_th": "...", "sentiment": "..."}
    If content exceeds the ceiling (30,000 chars), Gemini generates the title, executive summary,
    and sentiment within its scope, while the full body is translated via the chunked pipeline (translate_full_text).
    """
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    MAX_GEMINI_CONTENT = 30000
    is_over_limit = bool(content and len(content) > MAX_GEMINI_CONTENT)
    article_sample = (content[:MAX_GEMINI_CONTENT] if content else lead[:2000]) or title

    if is_over_limit:
        prompt = f"""You are a professional equity research analyst and financial journalist.
Analyze the following financial news article about stock/asset {ticker}.

Tasks:
1. Translate the headline to natural, high-level Thai financial journalism language ("title_th").
2. Write a structured Thai Executive Summary ("summary_th") formatted with 3 bullet points (- ...) covering:
   - Core news event and key financial metrics/figures (percentages, revenue, product launches, etc.)
   - Direct impact, potential risks or growth drivers for {ticker}
   - Key strategic takeaway for an active investor
3. Classify the market sentiment strictly as: BULLISH, BEARISH, or NEUTRAL.

Headline: "{title}"
Article Content (Excerpt):
{article_sample}

Respond ONLY with a valid JSON object matching this schema:
{{
  "title_th": "Translated News Headline",
  "summary_th": "- Key Takeaway: ...\\n- Market Impact: ...\\n- Strategic View: ...",
  "sentiment": "BULLISH"
}}"""
    else:
        prompt = f"""You are a professional equity research analyst and financial journalist.
Analyze the following financial news article about stock/asset {ticker}.

Tasks:
1. Translate the headline to natural, high-level Thai financial journalism language ("title_th").
2. Write a structured Thai Executive Summary ("summary_th") formatted with 3 bullet points (- ...) covering:
   - Core news event and key financial metrics/figures (percentages, revenue, product launches, etc.)
   - Direct impact, potential risks or growth drivers for {ticker}
   - Key strategic takeaway for an active investor
3. Translate the ENTIRE article body into natural, engaging Thai narrative preserving all paragraphs completely ("content_th"). Do not abbreviate or omit any paragraph.
4. Classify the market sentiment strictly as: BULLISH, BEARISH, or NEUTRAL.

Headline: "{title}"
Article Content:
{article_sample}

Respond ONLY with a valid JSON object matching this schema:
{{
  "title_th": "Translated News Headline",
  "summary_th": "- Key Takeaway: ...\\n- Market Impact: ...\\n- Strategic View: ...",
  "content_th": "Full translated article content across all paragraphs...",
  "sentiment": "BULLISH"
}}"""

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }).encode('utf-8')

    try:
        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = json.loads(res.read().decode('utf-8'))
            candidates = res_data.get('candidates', [])
            if candidates:
                text_content = candidates[0]['content']['parts'][0]['text']
                parsed = json.loads(text_content.strip())
                sentiment = str(parsed.get('sentiment', 'NEUTRAL')).upper()
                if sentiment not in ['BULLISH', 'BEARISH', 'NEUTRAL']:
                    sentiment = 'NEUTRAL'

                if is_over_limit:
                    has_thai_content = bool(re.search(r'[\u0e00-\u0e7f]', content or ''))
                    content_th = content if has_thai_content else translate_full_text(content)
                else:
                    content_th = parsed.get('content_th', '').strip()
                    if content and not content_th:
                        content_th = translate_full_text(content)

                return {
                    'title_th': parsed.get('title_th', '').strip(),
                    'summary_th': parsed.get('summary_th', '').strip(),
                    'content_th': content_th,
                    'sentiment': sentiment
                }
    except Exception as e:
        print(f"Notice: Gemini translation call failed or timed out: {e}")

    return None


def translate_with_fallback(
    title: str,
    ticker: str,
    lead: str = '',
    content: str = ''
) -> Dict[str, str]:
    """
    Intelligent Fallback Translation Engine:
    - Translates news headline
    - Generates structured Executive Summary
    - Analyzes sentiment from news body
    """
    # 1. News headline
    has_thai_title = bool(re.search(r'[\u0e00-\u0e7f]', title or ''))
    title_th = title if has_thai_title else translate_rpc(title)

    # 2. Sentiment analysis
    combined_text = f"{title} {lead} {content[:500]}".lower()
    bullish_words = [
        'surge', 'jump', 'gain', 'beat', 'growth', 'record', 'rally',
        'upgrade', 'high', 'profit', 'rise', 'soar', 'outperform', 'bullish'
    ]
    bearish_words = [
        'drop', 'fall', 'plunge', 'miss', 'loss', 'slump', 'cut',
        'downgrade', 'low', 'warn', 'crash', 'selloff', 'slashes', 'bearish'
    ]

    sentiment = 'NEUTRAL'
    if any(w in combined_text for w in bullish_words):
        sentiment = 'BULLISH'
    elif any(w in combined_text for w in bearish_words):
        sentiment = 'BEARISH'

    # 3. Generate Executive Summary as 3 bullet points (all in Thai, no boilerplate English)
    lead_source = lead or (content.split('\n\n')[0] if content else title)
    has_thai_lead = bool(re.search(r'[\u0e00-\u0e7f]', lead_source or ''))
    translated_lead = lead_source if has_thai_lead else translate_rpc(lead_source)

    if sentiment == 'BULLISH':
        sentiment_th = f"สัญญาณบวก: พบปัจจัยเร่งเชิงบวกและโอกาสเติบโตสำหรับ {ticker}"
    elif sentiment == 'BEARISH':
        sentiment_th = f"สัญญาณความเสี่ยง: พบแรงกดดันเชิงลบหรือปัจจัยท้าทายสำหรับ {ticker}"
    else:
        sentiment_th = f"มุมมองเป็นกลาง: ติดตามความคืบหน้าและปฏิกิริยาของตลาดสำหรับ {ticker}"

    paras = [p.strip() for p in (content or '').split('\n\n') if p.strip()]

    # Bullet 2: Market impact - incorporate 2nd paragraph if available
    if len(paras) > 1 and len(paras[1]) > 20:
        impact_source = paras[1][:400]
        has_thai_impact = bool(re.search(r'[\u0e00-\u0e7f]', impact_source))
        translated_impact = impact_source if has_thai_impact else translate_rpc(impact_source)
        market_impact_bullet = f"• ผลกระทบต่อตลาด: {sentiment_th} — {translated_impact}"
    else:
        market_impact_bullet = f"• ผลกระทบต่อตลาด: {sentiment_th}"

    # Bullet 3: Strategic takeaway / follow-up - incorporate 3rd paragraph if available
    if len(paras) > 2 and len(paras[2]) > 20:
        follow_source = paras[2][:400]
        has_thai_follow = bool(re.search(r'[\u0e00-\u0e7f]', follow_source))
        translated_follow = follow_source if has_thai_follow else translate_rpc(follow_source)
        strategic_bullet = f"• ข้อสรุปเชิงกลยุทธ์: {translated_follow}"
    else:
        strategic_bullet = f"• ข้อสรุปเชิงกลยุทธ์: ติดตามรายงานทางการเงินและความเคลื่อนไหวของ {ticker} อย่างใกล้ชิด"

    summary_bullets = [
        f"• ประเด็นสำคัญ: {translated_lead}",
        market_impact_bullet,
        strategic_bullet,
    ]
    summary_th = '\n'.join(summary_bullets)

    # 4. Translate full article paragraphs
    has_thai_content = bool(re.search(r'[\u0e00-\u0e7f]', content or ''))
    if has_thai_content:
        content_th = content or lead
    else:
        if content:
            content_th = translate_full_text(content)
        else:
            content_th = translated_lead

    return {
        'title_th': title_th,
        'summary_th': summary_th,
        'content_th': content_th,
        'sentiment': sentiment
    }


def translate_and_enrich_article(
    title: str,
    ticker: str,
    lead: str = '',
    content: str = ''
) -> Dict[str, str]:
    """Primary translation router: Gemini (if API key available) -> Automatic fallback."""
    gemini_key = os.getenv('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)
    if gemini_key:
        ai_res = translate_with_gemini(title, ticker, lead, content, gemini_key)
        if ai_res and ai_res.get('title_th'):
            has_thai_title = bool(re.search(r'[\u0e00-\u0e7f]', ai_res['title_th']))
            has_thai_sum = bool(re.search(r'[\u0e00-\u0e7f]', ai_res.get('summary_th', '')))
            has_thai_cnt = bool(re.search(r'[\u0e00-\u0e7f]', ai_res.get('content_th', '')))
            # Only accept Gemini output if title is in Thai AND summary/content are non-empty with Thai text
            # If content was provided, content_th must be non-empty (never accept empty translation body)
            has_valid_content = bool(not content or (has_thai_cnt and len(ai_res.get('content_th', '')) > 30))
            if has_thai_title and (has_thai_sum or has_thai_cnt) and has_valid_content:
                return ai_res
            print("Notice: Gemini returned partial or empty translation body, falling back to multi-tier engine.")

    return translate_with_fallback(title, ticker, lead, content)


@leased(lambda ticker, *args, **kwargs: 'news:' + ticker.upper(), skipped=0)
def ingest_news_for_ticker(ticker: str, limit_per_source: int = 3) -> int:
    """Accept identity-verified articles before translating or publishing them."""
    clean_tick = normalize_ticker(ticker)
    combined = fetch_from_yahoo_finance(clean_tick, limit=limit_per_source) + fetch_from_google_news(clean_tick, limit=limit_per_source)
    seen = set()
    count = 0
    for item in combined:
        url = canonical_url(item['url'])
        if not url or url in seen:
            continue
        seen.add(url)
        existing = StockNewsArticle.objects.filter(ticker=clean_tick, canonical_url=url).first() or StockNewsArticle.objects.filter(ticker=clean_tick, url=item['url']).first()
        if existing and existing.relevance in ('ACCEPTED', 'REJECTED'):
            if existing.relevance == 'ACCEPTED' and not existing.title_th:
                enrich_article_if_empty(existing)
            continue
        shared = StockNewsArticle.objects.filter(canonical_url=url).exclude(content='').first()
        scraped = {'lead': shared.summary, 'full_text': shared.content} if shared else scrape_article_content(item['url'], timeout=8)
        resolved = canonical_url(scraped.get('resolved_url') or item['url'])
        if not resolved or (resolved != url and resolved in seen):
            continue
        duplicates = StockNewsArticle.objects.filter(ticker=clean_tick, canonical_url=resolved)
        if existing:
            duplicates = duplicates.exclude(pk=existing.pk)
        if duplicates.exists():
            continue
        seen.add(resolved)
        url = resolved
        lead, content = scraped.get('lead', ''), scraped.get('full_text', '')
        relevance, reason = classify_news(clean_tick, item['title'], lead + ' ' + content, item.get('related_tickers'))
        translated = translate_and_enrich_article(item['title'], clean_tick, lead, content) if relevance == 'ACCEPTED' else {}
        from django.utils import timezone as django_timezone
        values = {
            'title': item['title'], 'title_th': translated.get('title_th', ''),
            'summary': lead, 'summary_th': translated.get('summary_th', ''),
            'content': content, 'content_th': translated.get('content_th', ''),
            'source': item['source'], 'published_at': item['published_at'],
            'sentiment': translated.get('sentiment', 'NEUTRAL'),
            'thumbnail_url': item.get('thumbnail_url', ''),
            'relevance': relevance, 'relevance_reason': reason, 'canonical_url': url,
            'relevance_checked_at': django_timezone.now(),
        }
        if existing:
            for field, value in values.items():
                setattr(existing, field, value)
            existing.save(update_fields=list(values))
        else:
            StockNewsArticle.objects.create(ticker=clean_tick, url=item['url'], **values)
        count += int(relevance == 'ACCEPTED')
    return count


def is_article_incomplete(article: StockNewsArticle) -> bool:
    """
    Checks whether an existing article is incomplete, has legacy English boilerplate,
    or needs re-scraping and re-translation.
    """
    title_th = (article.title_th or '').strip()
    summary_th = (article.summary_th or '').strip()
    content = (article.content or '').strip()
    content_th = (article.content_th or '').strip()

    has_thai_title = bool(re.search(r'[\u0e00-\u0e7f]', title_th))
    has_thai_summary = bool(re.search(r'[\u0e00-\u0e7f]', summary_th))
    has_thai_content = bool(re.search(r'[\u0e00-\u0e7f]', content_th))

    # Must have Thai title and summary
    if not has_thai_title or not has_thai_summary:
        return True

    # Detect legacy English boilerplate in summary_th
    boilerplate_phrases = [
        'market impact: positive signal',
        'market impact: risk signal',
        'market impact: neutral outlook',
        'source & follow-up: refer to full financial market report',
        'refer to full financial market report',
        'positive signal: positive catalyst identified',
        'risk signal: downward pressure',
        'neutral outlook: monitoring market developments'
    ]
    sum_lower = summary_th.lower()
    if any(bp in sum_lower for bp in boilerplate_phrases):
        return True

    # If content exists, it must have translated Thai content and paragraph parity
    if content:
        if not content_th or not has_thai_content:
            return True
        eng_paras = [p.strip() for p in content.split('\n\n') if p.strip()]
        th_paras = [p.strip() for p in content_th.split('\n\n') if p.strip()]
        if len(eng_paras) > len(th_paras) + 1:
            return True

    # If content is empty or short teaser (< 180 chars)
    if not content or len(content) < 180:
        return True

    return False


def enrich_article_if_empty(article: StockNewsArticle, force: bool = False) -> StockNewsArticle:
    """
    Backfills news body and translated summary for existing incomplete articles.
    Automatically repairs legacy boilerplate or partial translations.
    """
    incomplete = is_article_incomplete(article)
    if not force and not incomplete:
        return article

    # Fetch from source if content is empty or short teaser or incomplete or force=True
    content = article.content or ''
    lead = article.summary or ''
    if not content or len(content) < 200 or force or incomplete:
        scraped = scrape_article_content(article.url, timeout=8)
        scraped_content = scraped.get('full_text', '')
        if scraped_content and len(scraped_content) > len(content):
            content = scraped_content
            lead = scraped.get('lead') or lead

    trans_data = translate_and_enrich_article(
        title=article.title,
        ticker=article.ticker,
        lead=lead,
        content=content
    )

    article.summary = lead
    article.content = content
    if trans_data.get('title_th'):
        article.title_th = trans_data['title_th']
    if trans_data.get('summary_th'):
        article.summary_th = trans_data['summary_th']
    if trans_data.get('content_th'):
        article.content_th = trans_data['content_th']
    if trans_data.get('sentiment'):
        article.sentiment = trans_data['sentiment']

    try:
        article.save(update_fields=['summary', 'content', 'title_th', 'summary_th', 'content_th', 'sentiment'])
    except Exception as e:
        print(f"Notice: Failed to update enriched article {article.id}: {e}")

    return article


@leased('portfolio-news', seconds=3500, skipped={'status': 'already_running'})
def sync_all_portfolio_news(user=None) -> Dict[str, Any]:
    """Crawls news and translates automatically for all portfolio & watchlist tickers via background worker."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from .models import StockWatchlist
    revalidate_stored_news(limit=1000)
    holding_qs = StockHolding.objects.all()
    watch_qs = StockWatchlist.objects.all()
    if user:
        holding_qs = holding_qs.filter(user=user)
        watch_qs = watch_qs.filter(user=user)

    from .identity import active_tickers
    holding_tickers = active_tickers(user)
    watch_tickers = set(watch_qs.values_list('ticker', flat=True).distinct())
    distinct_tickers = sorted(list(holding_tickers | watch_tickers))
    total_new = 0

    if not distinct_tickers:
        return {
            'tickers_synced': [],
            'new_articles_count': 0
        }

    def _sync_worker(t_symbol):
        from django.db import connection
        try:
            return ingest_news_for_ticker(t_symbol, limit_per_source=3)
        finally:
            connection.close()

    max_workers = min(3, len(distinct_tickers))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(_sync_worker, t): t
            for t in distinct_tickers
        }
        for future in as_completed(future_to_ticker):
            t = future_to_ticker[future]
            try:
                new_count = future.result()
                total_new += new_count
            except Exception as e:
                print(f"Error syncing news for {t}: {e}")

    return {
        'tickers_synced': distinct_tickers,
        'new_articles_count': total_new
    }
