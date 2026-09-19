#!/usr/bin/env python3
"""의회 회의록 감시 공통 모듈: 환경변수(~/.env → 프로젝트 .env), 키워드, 상태 파일, 텍스트 분석."""
import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = SKILL_DIR.parent.parent.parent          # auction_news/
STATE_DIR = SKILL_DIR / "state"
WORK_DIR = PROJECT_DIR / "_workspace" / "council"
REPORT_DIR = PROJECT_DIR / "reports" / "council"
for d in (STATE_DIR, WORK_DIR, REPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------- .env 로딩: 전역(~/.env) 먼저, 프로젝트 .env 가 덮어씀 ----------
def load_env():
    for p in (Path.home() / ".env", PROJECT_DIR / ".env"):
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")

load_env()

# ---------- 감시 키워드 ----------
# (표시명, 정규식) — 정규식은 본문 매칭용. 서울시의회 검색폼에는 '검색어' 열을 쓴다.
KEYWORDS = [
    ("재개발", r"(?<!인)재개발"),
    ("재건축", r"재건축"),
    ("정비사업·정비구역", r"정비사업|정비구역|정비계획"),
    ("모아타운·모아주택", r"모아타운|모아주택"),
    ("신속통합기획", r"신속통합기획|신통기획"),
    ("공공재개발·공공재건축", r"공공재개발|공공재건축"),
    ("도시정비형", r"도시정비형|도시환경정비"),
    ("토지거래허가", r"토지거래허가"),
    ("분양가·분양가상한제", r"분양가"),
    ("주택공급", r"주택\s?공급|주택공급"),
    ("용적률·종상향", r"용적률|종상향|종 상향"),
    ("그린벨트·개발제한구역", r"그린벨트|개발제한구역"),
    ("임대주택", r"임대주택|공공임대"),
    ("전세·임대차", r"전세사기|전세보증|임대차"),
    ("경매·공매", r"경매|공매"),
    ("종부세·양도세·취득세", r"종합부동산세|종부세|양도소득세|양도세|취득세|보유세"),
    ("재건축부담금", r"재건축부담금|재초환|초과이익"),
    ("리모델링", r"리모델링"),
    ("역세권·지구단위", r"역세권|지구단위계획"),
    ("도시재생·뉴타운", r"도시재생|뉴타운"),
    ("주요 지역", r"용산공원|용산\s?미군|압구정|한남[동뉴]|성수전략|목동\s?아파트|상계동|중계동|노량진|흑석동|신림동|봉천동|창동|상봉동|답십리|장위동|미아동|수색|증산동|북아현|아현동|마천동|거여동|탄천"),
]
# 서울시의회 검색 폼에 던질 검색어(단일 키워드만 가능 → 핵심어만 순회)
SMC_SEARCH_TERMS = ["재개발", "재건축", "정비사업", "모아타운", "신속통합기획", "토지거래허가",
                    "분양가", "주택공급", "용적률", "그린벨트", "임대주택", "전세사기",
                    "경매", "종합부동산세", "리모델링", "역세권", "뉴타운", "용산공원"]

# 국회: 우선 감시 위원회(그 외 위원회는 안건명/본문에 키워드가 있을 때만)
ASSEMBLY_COMMITTEES = ["국토교통위원회", "기획재정위원회", "재정경제기획위원회", "행정안전위원회",
                       "예산결산특별위원회"]

KW_RE = re.compile("|".join(f"(?:{p})" for _, p in KEYWORDS))


def keyword_tags(text: str):
    """본문에 등장한 키워드 표시명 목록(등장 횟수 내림차순)."""
    out = []
    for name, pat in KEYWORDS:
        n = len(re.findall(pat, text))
        if n:
            out.append((name, n))
    out.sort(key=lambda x: -x[1])
    return out


SPEAKER_RE = re.compile(r"^\s*[○◯]\s*([^\n]{1,40}?)\s{2,}|^\s*[○◯]\s*((?:위원장|의장|부의장|위원|의원|시장|부시장|교육감|국장|본부장|장관|차관|청장|처장|실장|과장|단장|대표)?\s?[가-힣]{2,4}\s?(?:위원장|의장|부의장|위원|의원|시장|부시장|교육감|국장|본부장|장관|차관|청장|처장|실장|과장|단장|대표)?)")


def split_turns(text: str):
    """'○발언자  내용' 단위로 분할 → [(speaker, body)]."""
    lines = text.split("\n")
    turns, cur_sp, buf = [], None, []
    for ln in lines:
        m = re.match(r"^\s*[○◯]\s*(.+?)(?:\t| {2,}|\xa0+|　+)(.*)$", ln)
        if m and len(m.group(1)) <= 30:
            if buf:
                turns.append((cur_sp, "\n".join(buf).strip()))
            cur_sp, buf = m.group(1).strip(), [m.group(2)]
        else:
            buf.append(ln)
    if buf:
        turns.append((cur_sp, "\n".join(buf).strip()))
    return turns


def extract_hits(text: str, max_turns: int = 6, ctx: int = 260):
    """키워드가 포함된 발언 턴을 추려 [(speaker, snippet, tags)] 반환. 턴이 길면 키워드 주변만."""
    hits = []
    for sp, body in split_turns(text):
        if not KW_RE.search(body):
            continue
        b = re.sub(r"\s+", " ", body)
        if len(b) > ctx * 2:
            # 첫 키워드 주변 창 + 두 번째 키워드 창 병합
            idxs = [m.start() for m in KW_RE.finditer(b)]
            wins = []
            for i in idxs[:3]:
                s, e = max(0, i - ctx), min(len(b), i + ctx)
                if wins and s <= wins[-1][1]:
                    wins[-1][1] = e
                else:
                    wins.append([s, e])
            b = " … ".join(("…" if s > 0 else "") + b[s:e] + ("…" if e < len(b) else "") for s, e in wins)
        tags = [n for n, _ in keyword_tags(body)]
        hits.append({"speaker": sp or "(사회/미상)", "snippet": b, "tags": tags[:6]})
    # 키워드 다양성 우선, 길이 보정
    hits.sort(key=lambda h: (-len(h["tags"]), -len(h["snippet"])))
    return hits[:max_turns]


# ---------- 상태(이미 처리한 회의록) ----------
def load_seen(name: str) -> dict:
    p = STATE_DIR / f"seen_{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_seen(name: str, seen: dict):
    (STATE_DIR / f"seen_{name}.json").write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")


def date_range(days: int):
    end = date.today()
    return end - timedelta(days=days), end
