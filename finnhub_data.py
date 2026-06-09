"""finnhub_data.py — Finnhub 실시간 현재가 조회 (미국 종목)

무료 키(https://finnhub.io)로 미국 종목의 현재가를 가져옵니다.
일봉/지표는 yfinance 그대로 쓰고, '현재가'만 실시간으로 보강하는 용도입니다.

키 설정:
  - 환경변수 FINNHUB_API_KEY 또는 scan_config.FINNHUB_API_KEY 에 키를 넣으면 자동 활성화.
  - GitHub Actions 에서는 Secrets 에 FINNHUB_API_KEY 등록 → 워크플로가 환경변수로 주입.

키가 없으면 enabled()=False 라 아무 일도 안 하고 yfinance 값만 사용합니다.
표준 라이브러리(urllib)만 사용.
"""
from __future__ import annotations
import os
import json
import urllib.request

try:
    import scan_config as C
except Exception:
    C = None


def _key() -> str:
    k = getattr(C, "FINNHUB_API_KEY", "") if C else ""
    return k or os.environ.get("FINNHUB_API_KEY", "")


def enabled() -> bool:
    return bool(_key())


def get_quote(symbol: str) -> dict | None:
    """현재가 조회. 반환: {'c': 현재가, 'pc': 전일종가, 'dp': 등락률%} 또는 None."""
    k = _key()
    if not k:
        return None
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={k}"
        req = urllib.request.Request(url, headers={"User-Agent": "quant-scanner"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode())
        if d and d.get("c"):
            return {"c": d.get("c"), "pc": d.get("pc"), "dp": d.get("dp")}
    except Exception as e:
        print(f"  [Finnhub] {symbol} 조회 실패: {repr(e)[:80]}")
    return None
