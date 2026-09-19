#!/usr/bin/env python3
"""서울시의회 회의록(ms.smc.seoul.kr) 키워드 검색 → 신규 회의록 본문 수집 → JSON.

검색 폼은 CSRF+세션 기반이라 Playwright(헤드리스 크로미움)로 실행한다.
사용법: python3 collect_smc.py [--days 7] [--force]
출력: _workspace/council/smc_<날짜>.json
"""
import argparse
import html
import json
import re
import sys
import time
from datetime import date

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import (SMC_SEARCH_TERMS, WORK_DIR, date_range, extract_hits, keyword_tags,
                    load_seen, save_seen)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
BASE = "https://ms.smc.seoul.kr"
ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
KEY_RE = re.compile(r"recordView\.do\?key=([0-9a-f]+)")


def clean(s: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s))).strip()


def parse_results(page_html: str):
    rows = []
    for tr in ROW_RE.findall(page_html):
        if "recordView.do" not in tr:
            continue
        cells = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        key = KEY_RE.search(tr).group(1)
        title_m = re.search(r'title="([^"]+)"', tr)
        if len(cells) >= 6:
            kind = re.search(r"\[\s*(\S+)\s*\]", cells[4])
            meeting = re.sub(r"\[\s*\S+\s*\]\s*", "", cells[4]).strip()
            rows.append({"key": key, "th": cells[1], "session": cells[2], "round": cells[3],
                         "meeting": meeting, "date": cells[5][:10].replace(".", "-"),
                         "title": f"{cells[2]}({kind.group(1) + '회' if kind else ''}) {meeting} {cells[3]}({cells[5][:10]})"})
    return rows


def record_text(page) -> str:
    h = page.content()
    m = re.search(r'<div[^>]+id="canvas"[^>]*>(.*)', h, re.S)
    body = m.group(1) if m else h
    t = re.sub(r"<br\s*/?>|</p>|</div>|</li>", "\n", body)
    t = html.unescape(re.sub("<[^>]+>", "", t))
    t = t.replace("\xa0\xa0", "\t").replace("\xa0", " ")   # 발언자 뒤 이중공백은 탭으로 보존
    t = re.sub(r" {2,}", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    # 뷰어 UI 텍스트 꼬리 제거
    t = re.split(r"\n(?:top Scroll|발언 저장|발언 인쇄)", t)[0]
    return t.strip()


def agenda_items(text: str):
    """회의록 앞부분의 의사일정/부의안건 번호 목록."""
    head = text[:6000]
    items = re.findall(r"^\s*\d{1,2}\.\s+(.{4,120})$", head, re.M)
    seen, out = set(), []
    for it in items:
        it = it.strip()
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out[:20]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--force", action="store_true", help="이미 본 회의록도 다시 수집")
    ap.add_argument("--terms", default="", help="검색어 쉼표 구분(기본: 공통 목록)")
    a = ap.parse_args()
    start, end = date_range(a.days)
    terms = [t for t in a.terms.split(",") if t] or SMC_SEARCH_TERMS
    seen = load_seen("smc")
    found = {}  # key -> row(+terms)

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(locale="ko-KR", user_agent=UA)
        pg = ctx.new_page()
        pg.goto(f"{BASE}/kr/assembly/details.do", wait_until="networkidle", timeout=60000)
        for term in terms:
            try:
                pg.goto(f"{BASE}/kr/assembly/details.do", wait_until="networkidle", timeout=60000)
                pg.fill("input[name=keyword]", term)
                pg.fill("input[name=startDay]", start.strftime("%Y%m%d"))
                pg.fill("input[name=endDay]", end.strftime("%Y%m%d"))
                pg.click("form input[type=image]")
                pg.wait_for_load_state("networkidle", timeout=60000)
            except Exception as e:
                print(f"[smc] 검색 실패 '{term}': {e}", file=sys.stderr)
                continue
            page_no, total_rows = 1, 0
            while True:
                rows = parse_results(pg.content())
                total_rows += len(rows)
                for r in rows:
                    found.setdefault(r["key"], {**r, "terms": []})["terms"].append(term)
                nxt = pg.query_selector(f'#pagingNav a[title="{page_no + 1} 페이지로 이동"]')
                if not nxt or page_no >= 10:
                    break
                page_no += 1
                try:
                    nxt.click()
                    pg.wait_for_load_state("networkidle", timeout=60000)
                except Exception:
                    break
            print(f"[smc] '{term}': {total_rows}건", file=sys.stderr)
            time.sleep(0.5)

        # 본문 수집(신규만)
        results = []
        for key, r in found.items():
            if key in seen and not a.force:
                continue
            try:
                pg.goto(f"{BASE}/record/recordView.do?key={key}", wait_until="networkidle", timeout=90000)
                text = record_text(pg)
            except Exception as e:
                print(f"[smc] 본문 실패 {r['title']}: {e}", file=sys.stderr)
                continue
            hits = extract_hits(text)
            results.append({
                "source": "서울시의회", "id": key, "title": r["title"], "meeting": r["meeting"],
                "date": r["date"], "session": r["session"], "round": r["round"],
                "url": f"{BASE}/record/recordView.do?key={key}",
                "search_terms": sorted(set(r["terms"])), "tags": [n for n, _ in keyword_tags(text)][:8],
                "agenda": agenda_items(text), "hits": hits, "text_len": len(text),
            })
            seen[key] = {"date": r["date"], "title": r["title"], "collected": date.today().isoformat()}
            time.sleep(0.5)
        b.close()

    save_seen("smc", seen)
    out = WORK_DIR / f"smc_{date.today().isoformat()}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[smc] 검색 {len(found)}건 중 신규 {len(results)}건 → {out}", file=sys.stderr)
    print(str(out))


if __name__ == "__main__":
    main()
