#!/usr/bin/env python3
"""서울시 도시·건축 위원회 심의결과(commission.eseoul.go.kr) 수집 → JSON.

대상: 도시계획위원회·도시건축공동위원회·도시재정비위원회·건축위원회·정비사업통합심의위원회·
      소규모주택정비통합심의·공공주택통합심의위원회. 회차별 안건명·유형·심의결과(원안가결/수정가결/보류 등).
curl 수준의 POST 두 번으로 동작(세션 불필요).
사용법: python3 collect_seoul_committees.py [--days 14] [--force]
출력: _workspace/council/seoulcmt_<날짜>.json
"""
import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import KW_RE, WORK_DIR, date_range, keyword_tags, load_seen, save_seen

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
BASE = "https://commission.eseoul.go.kr"
COMMITTEES = {"CM01": "도시계획위원회", "CM02": "도시건축공동위원회", "CM03": "도시재정비위원회",
              "CM05": "건축위원회", "CM08": "정비사업통합심의위원회", "CM10": "소규모주택정비통합심의",
              "CM12": "공공주택통합심의위원회"}
# 건축위원회는 안건이 많고 비주거도 섞여 있어 키워드 있는 안건만 남긴다
KW_ONLY = {"CM05"}
SESSION_RE = re.compile(r'id="(\d{10})">.*?<dd>([^<]*(?:위원회|심의|자문단)[^<]*)</dd>.*?<dd>(\d{4}-\d{2}-\d{2})</dd>', re.S)


def post(path, data):
    req = urllib.request.Request(BASE + path, data=urllib.parse.urlencode(data).encode(), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "ignore")


def clean(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", s))).strip()


def parse_agenda(frag):
    """안건 표: <tr> 안건명 | 유형 | 결과."""
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", frag, re.S):
        cells = [clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        cells = [c for c in cells if c]
        if len(cells) >= 2 and not cells[0].startswith("안건명"):
            name = cells[0]
            kind = re.sub(r"^유형\s*", "", cells[1]) if len(cells) >= 3 else ""
            result = re.sub(r"^결과\s*", "", cells[-1]) if len(cells) >= 2 else ""
            out.append({"name": re.sub(r"^\d+\.\s*", "", name), "kind": kind, "result": result})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--pages", type=int, default=2)
    a = ap.parse_args()
    start, end = date_range(a.days)
    seen = load_seen("seoulcmt")
    results = []
    for cid, cname in COMMITTEES.items():
        sessions = []
        for page in range(1, a.pages + 1):
            try:
                lst = post("/cmitInfo/cmitSchdulList.do", {"cmitId": cid, "pageNo": page})
            except Exception as e:
                print(f"[seoulcmt] {cname} 목록 실패: {e}", file=sys.stderr)
                break
            rows = SESSION_RE.findall(lst)
            sessions += rows
            if not rows or min(r[2] for r in rows) < start.isoformat():
                break
        for sid, title, d in sessions:
            if not (start.isoformat() <= d <= end.isoformat()):
                continue
            if sid in seen and not a.force:
                continue
            try:
                frag = post("/cmitInfo/cmitSchdulSubList.do", {"cmitId": cid, "cmitOpmtInfoId": sid, "searchKeyword": ""})
            except Exception as e:
                print(f"[seoulcmt] {title} 안건 실패: {e}", file=sys.stderr)
                continue
            agenda = parse_agenda(frag)
            if cid in KW_ONLY:
                agenda = [g for g in agenda if KW_RE.search(g["name"])]
            if not agenda:
                seen[sid] = {"date": d, "title": title, "skip": True}
                continue
            text = " ".join(g["name"] for g in agenda)
            results.append({
                "source": "서울시 위원회", "id": sid, "committee": cname, "title": clean(title), "date": d,
                "url": f"{BASE}/subMenu.do?menuId=fnMainCmitSchdul&param={cid}",
                "tags": [n for n, _ in keyword_tags(text)][:8], "agenda": agenda,
                "n_pass": sum(1 for g in agenda if re.search(r"가결|의결|동의", g["result"])),
                "n_hold": sum(1 for g in agenda if any(k in g["result"] for k in ("보류", "재심의", "부결", "반려"))),
            })
            seen[sid] = {"date": d, "title": title, "collected": date.today().isoformat()}
            time.sleep(0.3)
    save_seen("seoulcmt", seen)
    out = WORK_DIR / f"seoulcmt_{date.today().isoformat()}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[seoulcmt] 신규 회차 {len(results)}건 → {out}", file=sys.stderr)
    print(str(out))


if __name__ == "__main__":
    main()
