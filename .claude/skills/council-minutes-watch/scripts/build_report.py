#!/usr/bin/env python3
"""수집 JSON(smc_*.json, assembly_*.json) → 규칙 기반 마크다운 브리핑 + 요약 텍스트.

사용법: python3 build_report.py [--date YYYY-MM-DD] [--summary-file <LLM 요약 md>]
출력: reports/council/<날짜>-council.md, _workspace/council/summary_<날짜>.txt
"""
import argparse
import json
import sys
from collections import Counter
from datetime import date

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import REPORT_DIR, WORK_DIR


def load(day):
    items = []
    for name in ("smc", "assembly"):
        p = WORK_DIR / f"{name}_{day}.json"
        if p.exists():
            items += json.loads(p.read_text(encoding="utf-8"))
    return items


def fmt_item(it):
    lines = [f"### {it['source']} · {it['meeting']} · {it['date']}",
             f"- 회의: {it['title']}",
             f"- 키워드: {', '.join(it['tags'][:6]) or '-'}"]
    if it.get("why"):
        lines.append(f"- 선별 사유: {it['why']}")
    ag = [a for a in it.get("agenda", []) if a]
    if ag:
        show = ag[:6]
        lines.append("- 안건: " + " / ".join(a[:60] for a in show) + (f" 외 {len(ag) - 6}건" if len(ag) > 6 else ""))
    for h in it.get("hits", [])[:4]:
        snip = h["snippet"]
        if len(snip) > 420:
            snip = snip[:420] + "…"
        lines.append(f"- **{h['speaker']}** [{', '.join(h['tags'][:3])}]: {snip}")
    lines.append(f"- 원문: {it['url']}" + (f" · PDF: {it['pdf']}" if it.get("pdf") else ""))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--summary-file", default="", help="LLM이 작성한 요약 마크다운(있으면 맨 위에 삽입)")
    a = ap.parse_args()
    items = load(a.date)
    items.sort(key=lambda x: (x["source"] != "서울시의회", x["date"]), reverse=False)
    smc = [i for i in items if i["source"] == "서울시의회"]
    asm = [i for i in items if i["source"] == "국회"]

    tagc = Counter(t for i in items for t in i["tags"][:5])
    spk = Counter(h["speaker"] for i in items for h in i["hits"] if not h["speaker"].startswith("("))
    top_tags = ", ".join(f"{k}({v})" for k, v in tagc.most_common(8))
    top_spk = ", ".join(f"{k}({v})" for k, v in spk.most_common(8))

    out = [f"# 의회 회의록 부동산 브리핑 — {a.date}", ""]
    out.append(f"신규 회의록 {len(items)}건 (서울시의회 {len(smc)} · 국회 {len(asm)}). 키워드 상위: {top_tags or '-'}")
    if top_spk:
        out.append(f"발언 많은 인물: {top_spk}")
    out.append("")
    if a.summary_file:
        p = __import__("pathlib").Path(a.summary_file)
        if p.exists() and p.read_text(encoding="utf-8").strip():
            out += ["## 핵심 요약", "", p.read_text(encoding="utf-8").strip(), ""]
    if not items:
        out.append("이 기간에 부동산 관련 신규 회의록이 없습니다.")
    if smc:
        out += ["## 서울시의회", ""] + [fmt_item(i) + "\n" for i in smc]
    if asm:
        out += ["## 국회", ""] + [fmt_item(i) + "\n" for i in asm]
    out += ["---", "출처: 서울특별시의회 회의록시스템(ms.smc.seoul.kr), 열린국회정보·국회회의록(record.assembly.go.kr). "
            "발췌는 키워드 주변 발언이며 전체 맥락은 원문 링크에서 확인.",]
    rp = REPORT_DIR / f"{a.date}-council.md"
    rp.write_text("\n".join(out), encoding="utf-8")

    # 텔레그램용 다이제스트(회의당 3줄) — 전문은 문서로 첨부
    dg = [f"신규 회의록 {len(items)}건 (서울시의회 {len(smc)} · 국회 {len(asm)})", f"키워드 상위: {top_tags or '-'}", ""]
    if a.summary_file:
        p = __import__("pathlib").Path(a.summary_file)
        if p.exists() and p.read_text(encoding="utf-8").strip():
            dg += ["[핵심 요약]", p.read_text(encoding="utf-8").strip(), ""]
    for i in items:
        best = i["hits"][0] if i["hits"] else None
        dg.append(f"■ {i['source']} {i['meeting']} {i['date']} — {', '.join(i['tags'][:3])}")
        if best:
            dg.append(f"  {best['speaker']}: {best['snippet'][:170].rstrip()}…")
        dg.append(f"  {i['url']}")
    dp = WORK_DIR / f"digest_{a.date}.md"
    dp.write_text("\n".join(dg), encoding="utf-8")

    # 알림용 요약(짧게)
    s = [f"의회 회의록 부동산 브리핑 {a.date}: 신규 {len(items)}건 (서울시의회 {len(smc)}, 국회 {len(asm)})"]
    for i in items[:6]:
        s.append(f"- {i['source']} {i['meeting']} {i['date']}: {', '.join(i['tags'][:3])}")
    sp = WORK_DIR / f"summary_{a.date}.txt"
    sp.write_text("\n".join(s), encoding="utf-8")
    print(str(rp))
    print(str(sp))
    print(str(dp))


if __name__ == "__main__":
    main()
