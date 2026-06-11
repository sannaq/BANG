"""history.py — 신호 성적표(매수/매도 신호를 누적 기록 → 결과로 승률 집계)

매 실행마다:
  1) 오늘의 매수/매도 신호를 history.json 에 기록 (종목당 하루 1건)
  2) 과거 기록을 현재가로 평가 (1일 후 r1, 5영업일 후 r5 수익률)
  3) 등급별 승률·평균수익 집계해서 반환

history.json 은 GitHub Actions 워크플로가 매번 저장소에 다시 커밋해 누적됩니다.
데이터가 며칠 쌓여야 의미 있는 승률이 나옵니다. 실패해도 빈 결과를 반환해 빌드를 막지 않습니다.
"""
from __future__ import annotations
import os
import json
import datetime as dt

PATH = os.path.join(os.path.dirname(__file__), "history.json")


def load() -> dict:
    try:
        return json.load(open(PATH, encoding="utf-8"))
    except Exception:
        return {"records": []}


def update(markets: dict) -> dict:
    try:
        h = load()
        recs = h.get("records", [])
        today = dt.date.today()
        tstr = today.strftime("%Y-%m-%d")
        seen_today = {(r.get("date"), r.get("ticker")) for r in recs if r.get("date") == tstr}

        cur_price = {}
        for mk, info in markets.items():
            for a in info.get("all", []):
                cur_price[a["ticker"]] = a.get("close")
            uniq = {}
            for key in ("recommend", "imminent", "gainers", "losers", "vol_surge", "volatile"):
                for r in info.get("ranked", {}).get(key, []):
                    uniq.setdefault(r["ticker"], r)
            for tk, r in uniq.items():
                if r.get("signal") in ("BUY", "SELL") and (tstr, tk) not in seen_today:
                    recs.append({"date": tstr, "market": mk, "ticker": tk,
                                 "signal": r["signal"], "grade": r.get("grade", ""),
                                 "score": r.get("score100"), "close": r.get("close"),
                                 "r1": None, "r5": None})
                    seen_today.add((tstr, tk))

        # 과거 기록 평가 (현재가 대비)
        for rec in recs:
            cp = cur_price.get(rec["ticker"])
            base = rec.get("close")
            if not cp or not base:
                continue
            try:
                el = (today - dt.date.fromisoformat(rec["date"])).days
            except Exception:
                continue
            ret = (cp / base - 1) * 100
            if rec.get("r1") is None and el >= 1:
                rec["r1"] = round(ret, 2)
            if rec.get("r5") is None and el >= 7:
                rec["r5"] = round(ret, 2)

        # 70일 이전 기록 정리
        cut = (today - dt.timedelta(days=70)).strftime("%Y-%m-%d")
        recs = [r for r in recs if r.get("date", "") >= cut]
        h["records"] = recs
        h["updated"] = tstr
        try:
            json.dump(h, open(PATH, "w", encoding="utf-8"), ensure_ascii=False)
        except Exception as e:
            print(f"  [성적표] 저장 실패: {repr(e)[:60]}")
        sb = scoreboard(recs)
        print(f"  [성적표] 기록 {len(recs)}건 누적")
        return sb
    except Exception as e:
        print(f"  [성적표] 오류: {repr(e)[:80]}")
        return {}


def scoreboard(recs: list) -> dict:
    def agg(filt, key):
        vals = [r[key] for r in recs if filt(r) and r.get(key) is not None]
        if not vals:
            return None
        win = round(100 * sum(1 for v in vals if v > 0) / len(vals))
        avg = round(sum(vals) / len(vals), 2)
        return {"n": len(vals), "win": win, "avg": avg}

    out = {}
    groups = [("강한 매수", ("강한 매수",)), ("매수 우위", ("매수 우위",)),
              ("매수신호 전체", None)]
    for label, grades in groups:
        f = (lambda r, g=grades: r.get("signal") == "BUY"
             and (g is None or r.get("grade") in g))
        out[label] = {"d1": agg(f, "r1"), "d5": agg(f, "r5")}
    return out
