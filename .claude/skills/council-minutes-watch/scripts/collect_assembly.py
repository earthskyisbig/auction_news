#!/usr/bin/env python3
"""국회 회의록(열린국회정보) 수집 → 부동산 관련 회의만 PDF 텍스트 추출 → JSON.

1) 목록: 열린국회정보 Open API(ASSEMBLY_API_KEY 필요). 키가 없으면 포털의 시트 조회 엔드포인트로 대체.
   - 위원회 회의록 ncwgseseafwbuheph / 본회의 회의록 nzbyfwhwaoanttzje
2) 선별: 감시 위원회(국토교통·기재·행안·예결·법사)에 속하거나 안건명에 키워드가 있는 회의.
3) 본문: record.assembly.go.kr PDF → pdftotext → 발언 단위 키워드 추출.

사용법: python3 collect_assembly.py [--days 7] [--force]
출력: _workspace/council/assembly_<날짜>.json
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import (ASSEMBLY_COMMITTEES, KW_RE, WORK_DIR, date_range, extract_hits,
                    keyword_tags, load_seen, save_seen)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
API = {"committee": "ncwgseseafwbuheph", "plenary": "nzbyfwhwaoanttzje"}
INF = {"committee": "OR137O001023MZ19321", "plenary": "OO1X9P001017YF13038"}
DAE = "22"


def http(url, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_tags(s):
    return html.unescape(re.sub("<[^>]+>", "", s or "")).strip()


# ---------- 목록 조회 ----------
def list_official(kind, day, key):
    """정식 Open API. CONF_DATE는 '검색어'라 하루 단위로 조회한다."""
    rows, p = [], 1
    while True:
        q = {"KEY": key, "Type": "json", "pIndex": p, "pSize": 100, "DAE_NUM": DAE, "CONF_DATE": day}
        raw = http(f"https://open.assembly.go.kr/portal/openapi/{API[kind]}?" + urllib.parse.urlencode(q))
        d = json.loads(raw)
        if API[kind] not in d:   # 결과 없음/오류 → {"RESULT":{"CODE":"INFO-200",...}}
            code = d.get("RESULT", {}).get("CODE", "")
            if code and not code.startswith("INFO-200"):
                raise RuntimeError(f"API 오류 {d.get('RESULT')}")
            break
        head, body = d[API[kind]][0]["head"], d[API[kind]][1].get("row", [])
        rows += body
        total = head[0].get("list_total_count", 0)
        if p * 100 >= total or not body:
            break
        p += 1
    return rows


def list_portal(kind, start, end):
    """포털 시트 조회(무키). 날짜 범위 지원."""
    rows, p = [], 1
    while True:
        data = urllib.parse.urlencode([("rows", 100), ("infId", INF[kind]), ("infSeq", 1), ("DAE_NUM", DAE),
                                       ("CONF_DATE", start), ("CONF_DATE", end), ("CONF_DATE_DAYS", ""),
                                       ("CLASS_NAME", ""), ("COMM_NAME", ""), ("TITLE", ""), ("SUB_NAME", ""),
                                       ("orderby", "")]).encode()
        d = json.loads(http(f"https://open.assembly.go.kr/portal/data/sheet/searchSheetData.do?page={p}", data))
        rows += d.get("data", [])
        if p >= int(d.get("pages") or 1):
            break
        p += 1
    return rows


def fetch_list(start, end):
    key = os.environ.get("ASSEMBLY_API_KEY")
    out = []
    for kind in ("committee", "plenary"):
        try:
            if key:
                d = start
                while d <= end:
                    out += [dict(r, _kind=kind) for r in list_official(kind, d.isoformat(), key)]
                    d += timedelta(days=1)
                    time.sleep(0.2)
            else:
                print("[assembly] ASSEMBLY_API_KEY 없음 → 포털 시트 조회로 대체", file=sys.stderr)
                out += [dict(r, _kind=kind) for r in list_portal(kind, start.isoformat(), end.isoformat())]
        except Exception as e:
            print(f"[assembly] 목록 조회 실패({kind}): {e}", file=sys.stderr)
    return out


# ---------- PDF 본문 ----------
def pdf_text(conf_num: str) -> str:
    raw = http(f"https://record.assembly.go.kr/assembly/viewer/minutes/download/pdf.do?id={conf_num}", timeout=120)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(raw)
        path = f.name
    try:
        txt = subprocess.run(["pdftotext", "-raw", path, "-"], capture_output=True, text=True, timeout=180).stdout
    finally:
        os.unlink(path)
    # 정리: 페이지 머리글(제439회-국토교통제2차(2026년9월16일) 3) 제거, '◯직함 이름 내용' → 발언자 뒤 탭
    txt = re.sub(r"\s*제\d+회-\S*\(\d{4}년\d{1,2}월\d{1,2}일\)\s*\d*", "\n", txt)
    txt = re.sub(r"^([○◯]\S+ \S+) ", r"\1\t", txt, flags=re.M)
    txt = re.sub(r"[ ]{2,}", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n", txt)
    return txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    start, end = date_range(a.days)
    seen = load_seen("assembly")

    rows = fetch_list(start, end)
    # 회의 단위로 묶기(안건 여러 행 → 1회의)
    meetings = {}
    for r in rows:
        cid = str(r.get("CONFER_NUM") or r.get("CONF_ID") or "")
        if not cid:
            continue
        m = meetings.setdefault(cid, {
            "id": cid, "date": r.get("CONF_DATE", ""), "committee": strip_tags(r.get("COMM_NAME") or "본회의"),
            "class": strip_tags(r.get("CLASS_NAME", "")), "title": strip_tags(r.get("TITLE", "")),
            "agenda": [], "pdf": r.get("PDF_LINK_URL") or f"https://record.assembly.go.kr/assembly/viewer/minutes/download/pdf.do?id={cid}",
            "summary_url": r.get("CONF_LINK_URL") or f"https://record.assembly.go.kr/assembly/viewer/minutes/xml.do?id={cid}&type=summary",
            "kind": r["_kind"]})
        sub = strip_tags(r.get("SUB_NAME", ""))
        if sub and sub not in m["agenda"]:
            m["agenda"].append(sub)
    print(f"[assembly] {start}~{end} 회의 {len(meetings)}건(안건 {len(rows)}행)", file=sys.stderr)

    # 선별: 감시 위원회 또는 안건명 키워드
    picked = []
    for m in meetings.values():
        watch = any(c in m["committee"] for c in ASSEMBLY_COMMITTEES) or m["kind"] == "plenary"
        kw = bool(KW_RE.search(" ".join(m["agenda"]) + " " + m["title"]))
        if watch or kw:
            m["why"] = ("감시위원회" if watch else "") + ("+안건키워드" if kw else "")
            picked.append(m)

    results = []
    for m in picked:
        if m["id"] in seen and not a.force:
            continue
        try:
            text = pdf_text(m["id"])
        except Exception as e:
            print(f"[assembly] PDF 실패 {m['id']} {m['title']}: {e}", file=sys.stderr)
            continue
        tags = [n for n, _ in keyword_tags(text)]
        hits = extract_hits(text)
        if not [t for t in tags if t != "주요 지역"] and not KW_RE.search(" ".join(m["agenda"])):
            # 감시 위원회지만 부동산 언급이 전혀 없는 회의는 제외(본 것으로 기록)
            seen[m["id"]] = {"date": m["date"], "title": m["title"], "skip": True}
            continue
        results.append({
            "source": "국회", "id": m["id"], "title": m["title"] or f"{m['committee']} ({m['date']})",
            "meeting": m["committee"], "date": m["date"], "class": m["class"], "why": m["why"],
            "url": m["summary_url"], "pdf": m["pdf"], "agenda": m["agenda"][:20],
            "tags": tags[:8], "hits": hits, "text_len": len(text),
        })
        seen[m["id"]] = {"date": m["date"], "title": m["title"], "collected": date.today().isoformat()}
        time.sleep(0.5)

    save_seen("assembly", seen)
    out = WORK_DIR / f"assembly_{date.today().isoformat()}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[assembly] 선별 {len(picked)}건 중 신규·유효 {len(results)}건 → {out}", file=sys.stderr)
    print(str(out))


if __name__ == "__main__":
    main()
