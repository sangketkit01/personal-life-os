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


def clean_ticker_for_search(ticker: str) -> str:
    """แปลง Ticker เป็นคำค้นหาที่แม่นยำ เช่น PTT.BK -> PTT, BTC-USD -> Bitcoin"""
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
    """ถอดรหัส URL ของ Google News RSS ให้เป็น Destination URL ดั้งเดิม"""
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
    ดึงเนื้อหาข่าวและ Lead Paragraph จาก URL ของบทความต้นฉบับ
    คืนค่า: {'lead': '...', 'full_text': '...', 'resolved_url': '...'}
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

        # กำจัด Tag ที่ไม่เกี่ยวข้องกับเนื้อหา
        for tag in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav', 'aside', 'form', 'svg']):
            tag.decompose()

        # 1. ดึง Meta Description (Lead summary)
        desc_tag = (
            soup.find('meta', attrs={'name': 'description'})
            or soup.find('meta', attrs={'property': 'og:description'})
            or soup.find('meta', attrs={'name': 'twitter:description'})
        )
        if desc_tag and desc_tag.get('content'):
            lead = desc_tag['content'].strip()

        # 2. ค้นหาเนื้อหาหลัก (Article body)
        container = (
            soup.find('article')
            or soup.find('div', class_=re.compile(r'caas-body|article-body|story-body|entry-content|wysiwyg|post-content', re.I))
            or soup.find('main')
            or soup.body
        )

        paragraphs = []
        skip_phrases = [
            'all rights reserved', 'cookie policy', 'privacy policy',
            'terms of service', 'sign up', 'subscribe to', 'read more:',
            'click here', 'advertisement', 'photo by', 'getty images'
        ]

        if container:
            for p in container.find_all('p'):
                text = p.get_text().strip()
                if len(text) > 35:
                    lower = text.lower()
                    if not any(phrase in lower for phrase in skip_phrases):
                        paragraphs.append(text)

        full_text = '\n\n'.join(paragraphs)
        if not lead and paragraphs:
            lead = paragraphs[0]
    except Exception as e:
        print(f"Notice: Parsing failed for {resolved_url}: {e}")

    return {
        'lead': lead.strip(),
        'full_text': full_text.strip(),
        'resolved_url': resolved_url
    }


def fetch_from_yahoo_finance(ticker: str, limit: int = 3) -> List[Dict[str, Any]]:
    """ดึงข่าวจาก Yahoo Finance Search API พร้อม Scrape เนื้อหา"""
    articles = []
    clean_search = clean_ticker_for_search(ticker)
    try:
        import yfinance as yf
        search_target = clean_search if (ticker.endswith('.BK') or ticker.endswith('-USD')) else ticker
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
                'summary': ''
            })
    except Exception as e:
        print(f"Warning: Failed to fetch Yahoo Finance news for {ticker}: {e}")

    return articles


def fetch_from_google_news(ticker: str, limit: int = 3) -> List[Dict[str, Any]]:
    """ดึงข่าวจาก Google News Financial RSS (ครอบคลุมทั้งข่าวไทยและสากล)"""
    articles = []
    clean_search = clean_ticker_for_search(ticker)

    if ticker.endswith('.BK'):
        query = f"{clean_search} หุ้น when:3d"
        hl, gl, ceid = "th", "TH", "TH:th"
    elif ticker.endswith('-USD'):
        query = f"{clean_search} crypto when:3d"
        hl, gl, ceid = "en-US", "US", "US:en"
    else:
        query = f"{ticker} stock when:3d"
        hl, gl, ceid = "en-US", "US", "US:en"

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
    แปลชุดข้อความหรือย่อหน้าพร้อมกันด้วย Microsoft Edge AI Translation Endpoint
    คืนค่า list ของข้อความที่แปลเป็นภาษาไทย หรือ None สำหรับรายการที่ล้มเหลว
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


def translate_rpc(text: str) -> str:
    """แปลข้อความหรือพาดหัวข่าวผ่าน Microsoft Edge Translation Engine (Tier 1) พร้อม Google & MyMemory Fallback"""
    if not text or not text.strip():
        return ''

    clean_text = text.strip()
    # หากเป็นภาษาไทยอยู่แล้ว คืนค่าเดิมได้ทันที
    if bool(re.search(r'[\u0e00-\u0e7f]', clean_text)):
        return clean_text

    # 1. Tier 1: Microsoft Edge AI Translator (เร็ว แม่นยำสูง ไร้ปัญหา Rate Limit)
    try:
        edge_res = translate_edge_batch([clean_text[:3000]])
        if edge_res and edge_res[0]:
            if bool(re.search(r'[\u0e00-\u0e7f]', edge_res[0])) or not bool(re.search(r'[a-zA-Z]', clean_text)):
                return edge_res[0]
    except Exception:
        pass

    # 2. Tier 2: Google Translate RPC (curl_cffi พร้อม client rotation)
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

    # 3. Tier 3: Google Translate ผ่าน urllib
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


def translate_full_text(text: str) -> str:
    """
    แปลเนื้อหาข่าวฉบับเต็ม 100% ทุกย่อหน้าแบบไม่ตัดทอน
    ใช้ Edge Batch Translation แปลทั้งบทความพร้อมกันอย่างรวดเร็ว พร้อม Fallback ย่อหน้าต่อย่อหน้า
    """
    if not text or not text.strip():
        return ''

    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        return ''

    # 1. แปลชุดย่อหน้าทั้งหมดด้วย Microsoft Edge Batch Translator
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
    แปลและสร้าง Executive Summary + เนื้อหาฉบับเต็มภาษาไทยด้วย Google Gemini AI
    คืนค่า JSON: {"title_th": "...", "summary_th": "...", "content_th": "...", "sentiment": "BULLISH|BEARISH|NEUTRAL"}
    """
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    article_sample = (content[:12000] if content else lead[:1000]) or title

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
  "title_th": "พาดหัวข่าวภาษาไทย",
  "summary_th": "- สาระสำคัญ: ...\\n- ผลกระทบต่อหุ้น: ...\\n- มุมมองกลยุทธ์: ...",
  "content_th": "เนื้อหาข่าวภาษาไทยฉบับเต็มครบทุกย่อหน้า...",
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
                return {
                    'title_th': parsed.get('title_th', '').strip(),
                    'summary_th': parsed.get('summary_th', '').strip(),
                    'content_th': parsed.get('content_th', '').strip(),
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
    Fallback Engine อัจฉริยะ:
    - แปลพาดหัวข่าว
    - แปลและสรุปสาระสำคัญ 3 หัวข้อ (Executive Summary)
    - แปลเนื้อหาหลักเป็นย่อหน้าภาษาไทย (Full Content Reader)
    - วิเคราะห์ Sentiment จากเนื้อหาและพาดหัวข่าว
    """
    # 1. พาดหัวข่าว
    has_thai_title = bool(re.search(r'[\u0e00-\u0e7f]', title or ''))
    title_th = title if has_thai_title else translate_rpc(title)

    # 2. วิเคราะห์ Sentiment
    combined_text = f"{title} {lead} {content[:500]}".lower()
    bullish_words = [
        'surge', 'jump', 'gain', 'beat', 'growth', 'record', 'rally',
        'upgrade', 'high', 'profit', 'rise', 'soar', 'outperform', 'ซื้อ', 'เติบโต', 'กำไรพุ่ง', 'เป้าหมาย'
    ]
    bearish_words = [
        'drop', 'fall', 'plunge', 'miss', 'loss', 'slump', 'cut',
        'downgrade', 'low', 'warn', 'crash', 'selloff', 'slashes', 'ดิ่ง', 'ขาดทุน', 'ลดลง', 'เตือน'
    ]

    sentiment = 'NEUTRAL'
    if any(w in combined_text for w in bullish_words):
        sentiment = 'BULLISH'
    elif any(w in combined_text for w in bearish_words):
        sentiment = 'BEARISH'

    # 3. สร้าง Executive Summary ในรูปแบบข้อ 3-4 ประเด็น
    lead_source = lead or (content.split('\n\n')[0] if content else title)
    has_thai_lead = bool(re.search(r'[\u0e00-\u0e7f]', lead_source or ''))
    translated_lead = lead_source if has_thai_lead else translate_rpc(lead_source)

    if sentiment == 'BULLISH':
        sentiment_summary = f"สัญญาณเชิงบวก: มีปัจจัยหนุนที่อาจส่งผลดีต่อแนวโน้มราคาและโมเมนตัมของหุ้น {ticker}"
    elif sentiment == 'BEARISH':
        sentiment_summary = f"สัญญาณความเสี่ยง: มีแรงกดดันหรือความท้าทายที่ควรติดตามอย่างใกล้ชิดสำหรับ {ticker}"
    else:
        sentiment_summary = f"มุมมองเป็นกลาง: ความเคลื่อนไหวด้านข่าวสารและข้อมูลพื้นฐานของ {ticker} ในกรอบปัจจุบัน"

    summary_bullets = [
        f"• ประเด็นสำคัญ: {translated_lead}",
        f"• ผลกระทบต่อหุ้น: {sentiment_summary}",
        f"• แหล่งข้อมูล & การติดตาม: ติดตามรายละเอียดเพิ่มเติมจากรายงานฉบับเต็มของตลาดการเงิน"
    ]
    summary_th = '\n'.join(summary_bullets)

    # 4. แปลเนื้อหาฉบับเต็มเป็นย่อหน้าภาษาไทยครบ 100% ทุกย่อหน้า
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
    """ฟังก์ชันกลางเลือกตัวแปล: Gemini (ถ้ามี Key) -> Fallback อัตโนมัติ"""
    gemini_key = os.getenv('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)
    if gemini_key:
        ai_res = translate_with_gemini(title, ticker, lead, content, gemini_key)
        if ai_res and ai_res.get('title_th'):
            return ai_res

    return translate_with_fallback(title, ticker, lead, content)


def ingest_news_for_ticker(ticker: str, limit_per_source: int = 3) -> int:
    """ดึงข่าวจากหลายแหล่งสำหรับ 1 Ticker พร้อม Scrape เนื้อหาเต็มและแปลผล"""
    clean_tick = normalize_ticker(ticker)

    # 1. รวบรวมข่าวจากทั้ง Yahoo Finance และ Google News
    yahoo_articles = fetch_from_yahoo_finance(clean_tick, limit=limit_per_source)
    google_articles = fetch_from_google_news(clean_tick, limit=limit_per_source)
    combined = yahoo_articles + google_articles

    # 2. คัดกรองข่าวซ้ำซ้อนตาม URL
    seen_urls = set()
    new_articles_count = 0

    for item in combined:
        url = item['url']
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # ตรวจสอบว่าเคยมีใน Database หรือยัง
        existing_this = StockNewsArticle.objects.filter(ticker=clean_tick, url=url).first()
        if existing_this:
            # ถ้ามีอยู่แล้วสำหรับหุ้นตัวนี้แต่ยังไม่มีเนื้อหา ให้เติมข้อมูล (Backfill)
            if not existing_this.content or not existing_this.content_th:
                enrich_article_if_empty(existing_this)
            continue

        # ตรวจสอบว่าเคยมีบทความนี้ถูกดึงไว้แล้วสำหรับหุ้นตัวอื่นหรือไม่ (Reuse Scraped & Translated Content)
        existing_other = StockNewsArticle.objects.filter(url=url).first()
        if existing_other:
            try:
                StockNewsArticle.objects.create(
                    ticker=clean_tick,
                    title=existing_other.title,
                    title_th=existing_other.title_th,
                    summary=existing_other.summary,
                    summary_th=existing_other.summary_th,
                    content=existing_other.content,
                    content_th=existing_other.content_th,
                    source=existing_other.source,
                    url=url,
                    published_at=existing_other.published_at,
                    sentiment=existing_other.sentiment,
                    thumbnail_url=existing_other.thumbnail_url
                )
                new_articles_count += 1
                continue
            except Exception as e:
                print(f"Warning: Failed to duplicate existing article for {clean_tick}: {e}")
                continue

        # 3. Scrape เนื้อหาข่าวฉบับเต็ม
        scraped = scrape_article_content(url, timeout=8)
        resolved_url = scraped.get('resolved_url') or url
        raw_lead = scraped.get('lead', '')
        raw_content = scraped.get('full_text', '')

        # 4. แปลภาษาและสร้าง Executive Summary + Sentiment
        trans_data = translate_and_enrich_article(
            title=item['title'],
            ticker=clean_tick,
            lead=raw_lead,
            content=raw_content
        )

        # 5. บันทึกลง Database ทันที
        try:
            StockNewsArticle.objects.create(
                ticker=clean_tick,
                title=item['title'],
                title_th=trans_data['title_th'],
                summary=raw_lead or item.get('summary', ''),
                summary_th=trans_data['summary_th'],
                content=raw_content,
                content_th=trans_data['content_th'],
                source=item['source'],
                url=url,
                published_at=item['published_at'],
                sentiment=trans_data['sentiment'],
                thumbnail_url=item.get('thumbnail_url', '')
            )
            new_articles_count += 1
        except Exception as e:
            print(f"Warning: Failed to save news article {url}: {e}")

    return new_articles_count


def enrich_article_if_empty(article: StockNewsArticle, force: bool = False) -> StockNewsArticle:
    """
    เติมเต็มเนื้อหาข่าวและบทสรุปไทยให้ข่าวที่มีอยู่แล้วหากยังว่างเปล่า หรือยังแปลไม่ครบทั้งบทความ
    """
    has_thai_title = bool(re.search(r'[\u0e00-\u0e7f]', article.title_th or ''))
    has_thai_summary = bool(re.search(r'[\u0e00-\u0e7f]', article.summary_th or ''))
    has_thai_content = bool(re.search(r'[\u0e00-\u0e7f]', article.content_th or ''))

    eng_paras = [p.strip() for p in (article.content or '').split('\n\n') if p.strip()]
    th_paras = [p.strip() for p in (article.content_th or '').split('\n\n') if p.strip()]

    # ถ้ามีเนื้อหาครบทั้งสองภาษาและแปลเป็นภาษาไทยอย่างสมบูรณ์แล้ว ไม่ต้องแปลซ้ำ (เว้นแต่ force=True)
    if not force and article.content and has_thai_content and has_thai_title and has_thai_summary and len(article.summary_th) > 30:
        if len(eng_paras) <= len(th_paras) + 1:
            return article

    # หากไม่มีเนื้อหาภาษาอังกฤษ หรือถูกบังคับ ให้ดึงจากเว็บต้นฉบับก่อน
    content = article.content
    lead = article.summary
    if not content or force or not has_thai_content:
        scraped = scrape_article_content(article.url, timeout=8)
        scraped_content = scraped.get('full_text', '')
        if scraped_content:
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


def sync_all_portfolio_news(user=None) -> Dict[str, Any]:
    """กวาดดึงข่าวและแปลภาษาอัตโนมัติสำหรับหุ้นทุกตัวในพอร์ตและ Watchlist โดยใช้ Worker Pool"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from .models import StockWatchlist
    holding_qs = StockHolding.objects.all()
    watch_qs = StockWatchlist.objects.all()
    if user:
        holding_qs = holding_qs.filter(user=user)
        watch_qs = watch_qs.filter(user=user)

    holding_tickers = set(holding_qs.values_list('ticker', flat=True).distinct())
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
