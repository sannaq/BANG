"""news.py — 뉴스 수집 (한국 RSS + 미국 Finnhub, 한글 번역)

- 한국: 국내 경제/증시 뉴스 RSS (이미 한글, 번역 불필요)
- 미국: Finnhub 시장 뉴스 → deep-translator 로 한글 번역
- 종목별: Finnhub company-news (미국 종목) → 한글 번역

모든 함수는 실패해도 빈 리스트를 반환해 빌드를 멈추지 않습니다.
"""
from __future__ import annotations
import re
import json
import html
import urllib.request
import datetime as dt


def _get(url: str, timeout: int = 12) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 quant-scanner"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _clean(s: str) -> str:
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s or "", flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


# ---------------------------------------------------------------- 한국 RSS
KR_FEEDS = [
    ("연합뉴스", "https://www.yna.co.kr/rss/economy.xml"),
    ("한국경제", "https://www.hankyung.com/feed/finance"),
    ("매일경제", "https://www.mk.co.kr/rss/30100041/"),
]


def korea_news(limit: int = 18) -> list[dict]:
    items: list[dict] = []
    for src, url in KR_FEEDS:
        try:
            xml = _get(url).decode("utf-8", "ignore")
            for m in re.finditer(r"<item>(.*?)</item>", xml, re.S):
                blk = m.group(1)
                t = re.search(r"<title>(.*?)</title>", blk, re.S)
                l = re.search(r"<link>(.*?)</link>", blk, re.S)
                d = re.search(r"<pubDate>(.*?)</pubDate>", blk, re.S)
                title = _clean(t.group(1)) if t else ""
                if not title:
                    continue
                items.append({
                    "title": title,
                    "link": _clean(l.group(1)) if l else "",
                    "date": _clean(d.group(1)) if d else "",
                    "source": src,
                })
        except Exception as e:
            print(f"  [뉴스/KR] {src} 실패: {repr(e)[:60]}")
    return items[:limit]


# ---------------------------------------------------------------- 번역
def _translate(texts: list[str]) -> list[str]:
    try:
        from deep_translator import GoogleTranslator
        tr = GoogleTranslator(source="en", target="ko")
        out = []
        for t in texts:
            try:
                out.append(tr.translate((t or "")[:480]) or t)
            except Exception:
                out.append(t)
        return out
    except Exception as e:
        print(f"  [뉴스] 번역기 사용 불가(원문 표시): {repr(e)[:60]}")
        return texts


# ---------------------------------------------------------------- 미국 Finnhub
def us_news(api_key: str, limit: int = 12) -> list[dict]:
    if not api_key:
        return []
    try:
        url = f"https://finnhub.io/api/v1/news?category=general&token={api_key}"
        data = json.loads(_get(url).decode("utf-8", "ignore"))
        items = data[:limit] if isinstance(data, list) else []
        ko = _translate([i.get("headline", "") for i in items])
        return [{
            "title": k,
            "title_en": i.get("headline", ""),
            "link": i.get("url", ""),
            "source": i.get("source", ""),
        } for i, k in zip(items, ko)]
    except Exception as e:
        print(f"  [뉴스/US] 실패: {repr(e)[:60]}")
        return []


def company_news(api_key: str, symbol: str, limit: int = 3) -> list[dict]:
    if not api_key:
        return []
    try:
        to = dt.date.today()
        frm = to - dt.timedelta(days=7)
        url = (f"https://finnhub.io/api/v1/company-news?symbol={symbol}"
               f"&from={frm}&to={to}&token={api_key}")
        data = json.loads(_get(url).decode("utf-8", "ignore"))
        items = data[:limit] if isinstance(data, list) else []
        ko = _translate([i.get("headline", "") for i in items])
        return [{"title": k, "title_en": i.get("headline", ""),
                 "link": i.get("url", "")} for i, k in zip(items, ko)]
    except Exception as e:
        print(f"  [뉴스/{symbol}] 실패: {repr(e)[:50]}")
        return []
