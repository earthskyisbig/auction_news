#!/usr/bin/env python3
"""주간 부동산 뉴스 후보 판독기 (TypeSafe Jev) — candidates.json → jev_news.{json,md}

WebSearch/WebFetch로 모은 기사 후보를 Jev(System One)에게 배치당 1회 호출로 판독시킨다.
기사마다 5문항: 카테고리 · 시장 영향도 · 가격 방향 · 수치·출처 명시 여부 · 확정/전망 여부.
출처 티어·날짜 범위·중복 묶기·우선순위 점수는 코드에서 결정적으로 계산한다(API 재호출 불필요).

사용:
  python3 news_jev.py candidates.json                     # → 같은 폴더에 jev_news.{json,md}
  python3 news_jev.py candidates.json --from 2026-09-21 --to 2026-09-27
  python3 news_jev.py candidates.json --batch 8 --concurrency 4
  python3 news_jev.py --resummarize jev_news.json --min-priority 45   # 재호출 없이 임계값만 변경

candidates.json 형식 (리스트 또는 {"articles": [...]}):
  [{"title": "...", "source": "한국경제", "url": "https://...", "date": "2026-09-22",
    "text": "기사 본문 또는 요약 3~5줄", "category_hint": "정책·규제"}]
  title 과 text 중 최소 하나는 필요. 나머지는 없으면 없는 대로 처리한다.

환경: TYPESAFE_API_KEY (~/doc-eval/.env 또는 ~/.env 에서 자동 로드)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

# ── 분류 체계 (SKILL.md 카테고리와 1:1) ──────────────────────────────────────
CATEGORY = {
    "policy": "정책·규제 — 정부·국회·지자체의 부동산 정책, 대출·세제·청약 제도, 규제지역 지정·해제.",
    "market": "시장 동향 — 매매가·전세가 변동률, 거래량, 전세가율, 미분양 등 시장 전체의 지표와 흐름.",
    "rate_macro": "금리·거시 — 기준금리, 주담대·전세대출 금리, 코픽스, 환율·물가 등 거시 변수.",
    "region": "지역 소식 — 특정 시·구·동네의 개발, 재건축·재개발, 교통망, 국지적 가격 움직임.",
    "supply": "분양·청약 — 분양 일정, 청약 경쟁률, 당첨 가점, 공급 물량 계획.",
    "other": "위 어디에도 해당하지 않음 — 기업 실적, 인테리어·리빙, 해외 부동산, 광고성 글.",
}
CAT_LABEL = {"policy": "정책·규제", "market": "시장 동향", "rate_macro": "금리·거시경제",
             "region": "지역별 소식", "supply": "분양·청약", "other": "기타"}
CAT_ORDER = ["policy", "market", "rate_macro", "region", "supply", "other"]

# Score criteria: "정도"가 아니라 "상황"을 묘사한다 (TypeSafe Score 문서 권고)
IMPACT = [
    {"what": "An individual building, one company, or a promotional piece. Nothing here changes what a buyer, "
             "seller, or borrower would do.",
     "examples": ["한 단지의 인테리어 리모델링 소개", "중개법인 마케팅 기사", "이미 여러 주 전에 알려진 내용의 반복"]},
    {"what": "A fact confined to one neighbourhood or one narrow segment. Only someone already watching that "
             "specific area would act on it.",
     "examples": ["특정 구 한 단지 신고가 거래", "한 지자체의 소규모 정비구역 지정"]},
    {"what": "A nationwide or metropolitan-area indicator, transaction volume, or supply figure that shows which "
             "way the market is moving, without itself changing any rule.",
     "examples": ["한국부동산원 주간 매매가 변동률 발표", "서울 아파트 거래량 집계", "전국 미분양 통계"]},
    {"what": "A measure that the government, the central bank, or the financial authority has actually adopted or "
             "announced, so that lending terms, taxes, or eligibility differ from before.",
     "examples": ["DSR 3단계 시행", "규제지역 신규 지정", "특례보금자리론 조건 변경", "취득세율 개정안 발표"]},
    {"what": "A change to the rules of the national housing market itself, or a policy-rate decision, that most "
             "market participants must respond to at once.",
     "examples": ["한국은행 기준금리 인상·인하", "가계대출 총량 규제 변경", "대규모 주택공급 대책 발표", "종부세·양도세 체계 개편"]},
]
DIRECTION = {
    "up": "Reads as upward pressure on prices or transactions: easier credit, rate cuts, tax relief, supply shortage, "
          "demand or price increases, deregulation.",
    "down": "Reads as downward pressure: tighter credit, rate hikes, heavier taxes, new restrictions, rising unsold "
            "stock, falling prices or volumes.",
    "neutral": "Mixed, purely descriptive, or a procedural/administrative item with no clear price implication.",
}

# 출처 티어 (SKILL.md 신뢰도 우선순위 코드화)
TIER1 = {"molit.go.kr", "moef.go.kr", "fsc.go.kr", "bok.or.kr", "reb.or.kr", "kostat.go.kr",
         "korea.kr", "seoul.go.kr", "land.seoul.go.kr", "kbland.kr", "hf.go.kr", "lh.or.kr",
         "applyhome.co.kr", "molit", "국토교통부", "기획재정부", "금융위원회", "한국은행",
         "한국부동산원", "통계청", "KB부동산", "서울시", "LH", "한국주택금융공사", "청약홈"}
TIER2 = {"chosun.com", "joongang.co.kr", "donga.com", "hankyung.com", "mk.co.kr", "sedaily.com",
         "yna.co.kr", "hani.co.kr", "khan.co.kr", "kmib.co.kr", "seoul.co.kr", "mt.co.kr",
         "edaily.co.kr", "fnnews.com", "asiae.co.kr", "news1.kr", "newsis.com", "ytn.co.kr",
         "kbs.co.kr", "mbc.co.kr", "sbs.co.kr", "biz.chosun.com", "hankookilbo.com", "etoday.co.kr",
         "조선일보", "중앙일보", "동아일보", "한국경제", "매일경제", "서울경제", "연합뉴스",
         "한겨레", "경향신문", "국민일보", "서울신문", "머니투데이", "이데일리", "파이낸셜뉴스",
         "아시아경제", "뉴스1", "뉴시스", "YTN", "KBS", "MBC", "SBS", "한국일보"}
TIER_BONUS = {1: 5.0, 2: 0.0, 3: -10.0}


def source_tier(source: str | None, url: str | None) -> int:
    host = ""
    if url:
        try:
            host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        except Exception:
            host = ""
    s = (source or "").strip()
    for key in TIER1:
        if (host and (host == key or host.endswith("." + key))) or (s and key in s):
            return 1
    for key in TIER2:
        if (host and (host == key or host.endswith("." + key))) or (s and key in s):
            return 2
    return 3


# ── 입출력 ────────────────────────────────────────────────────────────────
def load_env() -> None:
    for p in (Path.cwd() / ".env", Path.home() / "doc-eval" / ".env", Path.home() / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_candidates(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("articles") or data.get("candidates") or []
    out = []
    for i, a in enumerate(data):
        if not isinstance(a, dict):
            continue
        title = (a.get("title") or "").strip()
        text = (a.get("text") or a.get("summary") or a.get("snippet") or "").strip()
        if not (title or text):
            continue
        out.append({
            "i": len(out), "title": title, "text": text[:2000],
            "source": (a.get("source") or a.get("publisher") or "").strip() or None,
            "url": (a.get("url") or a.get("link") or "").strip() or None,
            "date": normalize_date(a.get("date") or a.get("published") or a.get("pubDate")),
            "category_hint": (a.get("category_hint") or a.get("category") or "").strip() or None,
        })
    if not out:
        sys.exit(f"판독할 기사가 없음: {path}")
    return out


_D = [("%Y-%m-%d", None), ("%Y.%m.%d", None), ("%Y/%m/%d", None), ("%Y년 %m월 %d일", None)]


def normalize_date(v) -> str | None:
    if not v:
        return None
    s = str(v).strip()
    m = re.search(r"(\d{4})[-.\/년]\s*(\d{1,2})[-.\/월]\s*(\d{1,2})", s)
    if m:
        y, mo, d = (int(x) for x in m.groups())
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            return None
    return None


def week_range(today: date) -> tuple[str, str]:
    mon = today - timedelta(days=today.weekday())
    return mon.isoformat(), (mon + timedelta(days=6)).isoformat()


# ── Jev 질문 ──────────────────────────────────────────────────────────────
def build_questions(n: int):
    from typesafe_sdk import Choice, Noul, Score
    q = {}
    for i in range(n):
        ref = f"`articles[{i}]` (its `title` and `text`)"
        q[f"cat_{i}"] = Choice(
            instructions=f"Which section of a weekly Korean real-estate briefing does {ref} belong in? "
                         f"`category_hint`, when present, is the collector's guess — override it if the text says otherwise.",
            criteria=CATEGORY)
        q[f"impact_{i}"] = Score(
            instructions=f"How far does what {ref} reports reach into the Korean housing market? "
                         f"Judge the reported fact itself, not how dramatic the headline sounds.",
            criteria=IMPACT)
        q[f"dir_{i}"] = Choice(
            instructions=f"Which way does the fact in {ref} push Korean apartment prices or transaction volume?",
            criteria=DIRECTION)
        q[f"sourced_{i}"] = Noul(
            instructions=f"Does {ref} state at least one concrete figure (a rate, a price, a percentage, a count) "
                         f"TOGETHER WITH the period or reference date it applies to and the body that produced it? "
                         f"Answer no if figures appear with no date or no issuing body, or if there are no figures at all.")
        q[f"spec_{i}"] = Noul(
            instructions=f"Is the core of {ref} something not yet settled — 전망, 예상, 추진, 검토, 목표, 방침, 논의, "
                         f"기대, 가능성, an unnamed-official claim, or an analyst's forecast? "
                         f"Answer no when it reports an action already taken, published, decided, or measured.")
    return q


def build_state(batch: list[dict], window: tuple[str, str]) -> dict:
    return {
        "briefing": {
            "purpose": "A weekly Korean real-estate news briefing for an investor who buys and analyses apartments.",
            "week_start": window[0], "week_end": window[1],
            "note": "Judge each article on its own. Source reliability, publication date and duplicate detection are "
                    "handled outside the model — do not factor them in.",
        },
        "articles": [
            {k: v for k, v in
             {"i": a["i"], "title": a["title"], "text": a["text"],
              "category_hint": a["category_hint"], "date": a["date"]}.items() if v is not None}
            for a in batch
        ],
    }


async def readout(arts: list[dict], window: tuple[str, str], batch_size: int,
                  concurrency: int, model: str | None) -> tuple[list[dict], dict]:
    from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy, TypeSafeError
    batches = [arts[i:i + batch_size] for i in range(0, len(arts), batch_size)]
    sem = asyncio.Semaphore(concurrency)
    usage = Counter()
    meta: dict = {}

    async def one(client, batch):
        state = build_state(batch, window)
        async with sem:
            try:
                r = await client.system_one(state, build_questions(len(batch)), model=model)
            except TypeSafeError as e:
                return [{**a, "error": f"{type(e).__name__}: {e}"} for a in batch]
            except Exception as e:  # noqa: BLE001
                return [{**a, "error": f"{type(e).__name__}: {e}"} for a in batch]
        meta.setdefault("model", r.model)
        meta.setdefault("request_id", getattr(r, "request_id", None))
        u = r.usage.model_dump() if hasattr(r.usage, "model_dump") else dict(r.usage or {})
        for k, v in u.items():
            if isinstance(v, int):
                usage[k] += v
        out = []
        for j, a in enumerate(batch):
            cat, imp, dr = r.answers[f"cat_{j}"], r.answers[f"impact_{j}"], r.answers[f"dir_{j}"]
            src, spc = r.answers[f"sourced_{j}"], r.answers[f"spec_{j}"]
            out.append({**a,
                        "category": cat.choice,
                        "p_category": round(cat.probabilities.get(cat.choice, 0.0), 2),
                        "impact": round(imp.score, 2), "impact_max": len(IMPACT) - 1,
                        "impact_confidence": round(imp.confidence, 2),
                        "impact_probs": {str(k): round(v, 3) for k, v in imp.probabilities.items()},
                        "direction": dr.choice,
                        "p_direction": round(dr.probabilities.get(dr.choice, 0.0), 2),
                        "p_sourced": round(src.noul, 2), "p_speculative": round(spc.noul, 2)})
        return out

    retry = RetryPolicy(max_retries=3, backoff_initial=1.0, backoff_max=10.0, timeout=90)
    results: list[dict] = []
    async with AsyncTypeSafeClient(retry=retry, timeout=90) as client:
        tasks = [one(client, b) for b in batches]
        for n, coro in enumerate(asyncio.as_completed(tasks), 1):
            results.extend(await coro)
            print(f"\r판독 {n}/{len(batches)} 배치", end="", file=sys.stderr)
    print(file=sys.stderr)
    results.sort(key=lambda x: x["i"])
    meta["usage"] = dict(usage)
    return results, meta


# ── 코드 후처리: 티어·날짜·중복·우선순위 (재호출 불필요) ──────────────────────
_STOP = re.compile(r"[\[\]()·,…\"'“”‘’\-–—:|/]")


def title_key(a: dict) -> tuple[set[str], set[str]]:
    """(제목 단어 집합, 숫자 집합). 같은 사건을 다룬 기사는 같은 수치를 반복한다.
    본문은 기사마다 문장이 달라 유사도를 희석시키므로 단어 비교는 제목으로만 한다."""
    title = a.get("title") or a.get("text", "")[:60]
    words = {w for w in _STOP.sub(" ", title).split() if len(w) >= 2}
    nums = {n.replace(",", "") for n in
            re.findall(r"\d[\d,]{2,}", _STOP.sub(" ", title + " " + a.get("text", "")[:300]))}
    return words, nums


def similar(x: tuple[set, set], y: tuple[set, set], threshold: float) -> bool:
    (wa, na), (wb, nb) = x, y
    if not (wa and wb):
        return False
    jac = len(wa & wb) / len(wa | wb)
    # 4591가구·3137가구처럼 사건 고유의 수치를 함께 쓰면 제목 표현이 달라도 같은 사건으로 본다
    # (같은 카테고리 안에서만 비교하므로 서로 다른 사건이 3자리 수 두 개를 공유할 일은 드물다).
    shared = len(na & nb)
    return jac >= threshold or shared >= 2 or (shared == 1 and jac >= threshold * 0.55)


def dedupe(rows: list[dict], threshold: float = 0.4) -> None:
    """같은 사건을 다룬 기사끼리 묶는다. 대표는 티어가 높고 우선순위가 높은 쪽."""
    keys = [title_key(r) for r in rows]
    group: dict[int, int] = {}
    for i in range(len(rows)):
        if i in group:
            continue
        group[i] = i
        for j in range(i + 1, len(rows)):
            if j in group or rows[i].get("category") != rows[j].get("category"):
                continue
            if similar(keys[i], keys[j], threshold):
                group[j] = i
    buckets: dict[int, list[int]] = defaultdict(list)
    for idx, root in group.items():
        buckets[root].append(idx)
    for root, members in buckets.items():
        best = max(members, key=lambda k: (-rows[k]["tier"], rows[k]["priority"]))
        for k in members:
            rows[k]["dup_of"] = None if k == best else rows[best]["i"]
            rows[k]["dup_count"] = len(members)


def summarize(rows: list[dict], window: tuple[str, str], min_priority: float,
              strict_dates: bool, per_category: int = 2) -> dict:
    ok = [r for r in rows if "error" not in r]
    for r in ok:
        r["tier"] = source_tier(r.get("source"), r.get("url"))
        r["in_window"] = bool(r.get("date")) and window[0] <= r["date"] <= window[1]
        base = 100.0 * r["impact"] / max(r["impact_max"], 1)
        p = base + TIER_BONUS[r["tier"]]
        if r["p_speculative"] >= 0.6:
            p -= 10.0
        if r["p_sourced"] < 0.4:
            p -= 5.0
        r["priority"] = round(max(0.0, min(100.0, p)), 1)
    ok.sort(key=lambda r: -r["priority"])
    dedupe(ok)
    for r in ok:
        reasons = []
        if r["dup_of"] is not None:
            reasons.append(f"중복(#{r['dup_of']})")
        if strict_dates and r.get("date") and not r["in_window"]:
            reasons.append("기간 외")
        if r["priority"] < min_priority:
            reasons.append(f"우선순위<{min_priority:g}")
        if r["category"] == "other":
            reasons.append("카테고리 기타")
        r["drop_reasons"] = reasons
        r["keep"] = not reasons
        r["kept_by_quota"] = False

    # 섹션이 통째로 비지 않도록: 중복·기간 외·기타가 아닌 후보 중 카테고리별 상위 per_category건은
    # 우선순위 미달이어도 살린다 (리포트에 "지역별 소식" 같은 고정 섹션이 있기 때문).
    if per_category > 0:
        for cat in CAT_ORDER:
            if cat == "other":
                continue
            pool = [r for r in ok if r["category"] == cat and r["dup_of"] is None
                    and not (strict_dates and r.get("date") and not r["in_window"])]
            for r in pool[:per_category]:
                if not r["keep"]:
                    r["keep"] = True
                    r["kept_by_quota"] = True
                    r["drop_reasons"] = []
    c = Counter()
    c["total"] = len(rows)
    c["errors"] = len(rows) - len(ok)
    c["keep"] = sum(1 for r in ok if r["keep"])
    c["by_quota"] = sum(1 for r in ok if r.get("kept_by_quota"))
    c["dup"] = sum(1 for r in ok if r["dup_of"] is not None)
    c["out_of_window"] = sum(1 for r in ok if r.get("date") and not r["in_window"])
    c["no_date"] = sum(1 for r in ok if not r.get("date"))
    c["speculative"] = sum(1 for r in ok if r["p_speculative"] >= 0.6)
    c["unsourced"] = sum(1 for r in ok if r["p_sourced"] < 0.4)
    kept = [r for r in ok if r["keep"]]
    dirs = Counter(r["direction"] for r in kept)
    tone = ("상승 우위" if dirs["up"] > dirs["down"] * 1.3 else
            "하락 우위" if dirs["down"] > dirs["up"] * 1.3 else "혼조·보합")
    return {"window": {"from": window[0], "to": window[1]},
            "counts": dict(c), "direction_mix": dict(dirs), "tone": tone,
            "by_category": {k: sum(1 for r in kept if r["category"] == k) for k in CAT_ORDER},
            "min_priority": min_priority, "strict_dates": strict_dates,
            "per_category": per_category,
            "rows": ok + [r for r in rows if "error" in r]}


def write_md(summary: dict, path: Path) -> None:
    rows = summary["rows"]
    kept = [r for r in rows if r.get("keep")]
    w = summary["window"]
    L = [f"# 주간 부동산 뉴스 — Jev 판독 결과",
         "",
         f"**기간** {w['from']} ~ {w['to']} · **판독** {summary['counts']['total']}건 → "
         f"**채택 {summary['counts']['keep']}건** · **시장 톤** {summary['tone']}"
         f" (상승 {summary['direction_mix'].get('up',0)} / 하락 {summary['direction_mix'].get('down',0)}"
         f" / 중립 {summary['direction_mix'].get('neutral',0)})",
         "",
         "> 채택 기사는 우선순위 내림차순. 리포트 본문은 이 목록 순서대로 쓰면 된다.",
         ""]
    for cat in CAT_ORDER:
        group = [r for r in kept if r["category"] == cat]
        if not group:
            continue
        L += [f"## {CAT_LABEL[cat]} ({len(group)}건)", "",
              "| 우선 | 영향도 | 방향 | 제목 | 출처(티어) | 날짜 | 비고 |",
              "|---:|---:|:--:|---|---|---|---|"]
        for r in group:
            flags = []
            if r["p_speculative"] >= 0.6:
                flags.append(f"전망 {r['p_speculative']:.0%}")
            if r["p_sourced"] < 0.4:
                flags.append("수치·기준일 없음")
            if r["impact_confidence"] < 0.7:
                flags.append("?")
            if r.get("dup_count", 1) > 1:
                flags.append(f"동일사건 {r['dup_count']}건")
            if r["tier"] == 3:
                flags.append("1차 출처 확인 필요")
            if r.get("kept_by_quota"):
                flags.append("섹션 정원")
            arrow = {"up": "▲", "down": "▼", "neutral": "―"}[r["direction"]]
            title = (r["title"] or r["text"][:40]).replace("|", "/")
            if r.get("url"):
                title = f"[{title}]({r['url']})"
            L.append(f"| {r['priority']:.0f} | {r['impact']:.1f}/{r['impact_max']} | {arrow} | {title} | "
                     f"{r.get('source') or '-'} (T{r['tier']}) | {r.get('date') or '-'} | {', '.join(flags) or '-'} |")
        L.append("")
    dropped = [r for r in rows if r.get("keep") is False]
    if dropped:
        L += [f"## 제외 {len(dropped)}건", "", "| 제목 | 우선 | 사유 |", "|---|---:|---|"]
        for r in sorted(dropped, key=lambda x: -x["priority"]):
            L.append(f"| {(r['title'] or r['text'][:40]).replace('|','/')} | {r['priority']:.0f} | "
                     f"{', '.join(r['drop_reasons'])} |")
        L.append("")
    err = [r for r in rows if "error" in r]
    if err:
        L += [f"## 오류 {len(err)}건", ""] + [f"- {r.get('title','')}: {r['error']}" for r in err] + [""]
    c = summary["counts"]
    L += ["---", "",
          f"판독 요약: 중복 {c['dup']} · 기간 외 {c['out_of_window']} · 날짜 없음 {c['no_date']} · "
          f"전망성 {c['speculative']} · 수치·기준일 없음 {c['unsourced']} · 오류 {c['errors']}",
          "",
          "*Jev는 본문에 적힌 것만 판단한다. '출처가 명시됐는가'는 보지만 '그 출처가 사실인가'는 보지 않는다.*"]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# ── CLI ───────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="주간 부동산 뉴스 후보 Jev 판독기")
    ap.add_argument("input", help="candidates.json (또는 --resummarize 시 기존 jev_news.json)")
    ap.add_argument("--resummarize", action="store_true", help="API 재호출 없이 기존 결과를 새 임계값으로 재집계")
    ap.add_argument("--from", dest="dfrom", help="기간 시작 YYYY-MM-DD (기본: 이번 주 월요일)")
    ap.add_argument("--to", dest="dto", help="기간 끝 YYYY-MM-DD (기본: 이번 주 일요일)")
    ap.add_argument("--min-priority", type=float, default=35.0, help="채택 최소 우선순위 (기본 35)")
    ap.add_argument("--no-strict-dates", action="store_true", help="기간 밖 기사도 채택")
    ap.add_argument("--per-category", type=int, default=2,
                    help="우선순위 미달이어도 카테고리마다 살릴 상위 기사 수 (기본 2, 0이면 끔)")
    ap.add_argument("--batch", type=int, default=8, help="한 API 호출에 묶을 기사 수 (기본 8)")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--model", default=None, help="기본 jev-latest")
    ap.add_argument("-o", "--out", help="출력 파일 접두 (기본: 입력 폴더/jev_news)")
    a = ap.parse_args()

    inp = Path(a.input).expanduser().resolve()
    if not inp.exists():
        sys.exit(f"입력 파일 없음: {inp}")
    out_prefix = Path(a.out).expanduser() if a.out else inp.parent / "jev_news"

    if a.resummarize:
        prev = json.loads(inp.read_text(encoding="utf-8"))
        rows = prev["rows"]
        win = (a.dfrom or prev["window"]["from"], a.dto or prev["window"]["to"])
        summary = summarize(rows, win, a.min_priority, not a.no_strict_dates, a.per_category)
        summary["meta"] = prev.get("meta", {})
    else:
        load_env()
        if not os.environ.get("TYPESAFE_API_KEY"):
            sys.exit("TYPESAFE_API_KEY 없음 (~/doc-eval/.env 확인)")
        arts = load_candidates(inp)
        dw = week_range(date.today())
        win = (a.dfrom or dw[0], a.dto or dw[1])
        rows, meta = asyncio.run(readout(arts, win, a.batch, a.concurrency, a.model))
        summary = summarize(rows, win, a.min_priority, not a.no_strict_dates, a.per_category)
        summary["meta"] = {**meta, "generated": datetime.now().isoformat(timespec="seconds"),
                           "input": str(inp)}

    js, md = Path(f"{out_prefix}.json"), Path(f"{out_prefix}.md")
    js.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    write_md(summary, md)
    c = summary["counts"]
    print(f"채택 {c['keep']}/{c['total']} (섹션 정원 {c['by_quota']}) · 중복 {c['dup']} · 기간 외 {c['out_of_window']} · "
          f"오류 {c['errors']} · 톤 {summary['tone']} → {md}")


if __name__ == "__main__":
    main()
