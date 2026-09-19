---
name: council-minutes-watch
description: 서울시의회 회의록(ms.smc.seoul.kr)·국회 회의록(열린국회정보·record.assembly.go.kr)·서울시 도시계획위원회 등 도시건축위원회 심의결과(commission.eseoul.go.kr)에서 부동산·정비사업·주택정책 관련 발언을 정기 수집해 브리핑으로 만들고 텔레그램으로 발송한다. "의회 회의록 브리핑", "시의회/국회에서 재개발 얘기 나온 것", "도시계획위원회 심의결과", "회의록 감시 다시 실행", "지난주 의회 부동산 발언 정리", "회의록 키워드 추가" 같은 요청이면 이 스킬을 쓴다. 뉴스 브리핑은 realestate-news-daily.
---

# council-minutes-watch — 의회 회의록 부동산 감시

**목표:** 서울시의회·국회 회의록에서 재개발·재건축·정비사업·주택공급·세제·주요 구역 관련 발언을 주기적으로 찾아 "누가(발언자) · 어디서(회의) · 무엇을(발언 요지)"로 정리하고 원문 링크와 함께 발송한다. 뉴스보다 앞서는 정책·구역별 신호를 잡는 것이 목적이다.

## 파이프라인 (scripts/)

| 단계 | 스크립트 | 방식 | 산출물 |
|---|---|---|---|
| 1 | `collect_smc.py --days N` | Playwright(헤드리스)로 단순검색 폼에 키워드 18개 순회, 신규 회의록 본문 수집·발언 추출 | `_workspace/council/smc_<날짜>.json` |
| 2 | `collect_assembly.py --days N` | 열린국회정보 Open API(`ASSEMBLY_API_KEY`, `~/.env`) 로 위원회·본회의 목록 → 감시 위원회/안건 키워드 선별 → PDF→`pdftotext -raw` → 발언 추출. 키 없으면 포털 시트 엔드포인트로 대체 | `_workspace/council/assembly_<날짜>.json` |
| 2b | `collect_seoul_committees.py --days N` | 서울시 도시건축위원회 시스템(commission.eseoul.go.kr) POST 2회로 도시계획위·도시건축공동위·도시재정비위·건축위(키워드 안건만)·정비사업통합심의위·소규모주택정비·공공주택통합심의 회차별 안건·심의결과(원안/수정/조건부가결·보류) 수집 | `_workspace/council/seoulcmt_<날짜>.json` |
| 3 | `build_report.py [--summary-file]` | 규칙 기반 마크다운 전문 + 텔레그램 다이제스트 + 알림 요약 | `reports/council/<날짜>-council.md`, `_workspace/council/digest_<날짜>.md` |
| 4 | (LLM) 아래 "요약 작성" 지침 | 전문을 읽고 핵심 요약 작성 | `_workspace/council/llm_summary_<날짜>.md` |
| 5 | `../realestate-news-daily/scripts/deliver.py --report digest --attach 전문 --title ...` | 텔레그램 본문 + 전문 .md 첨부 | 발송 |

`scripts/run-council.sh` 가 1→2→3→4→3(요약 삽입)→5 를 무인 실행한다(crontab 등록). 처리한 회의록 ID는 `state/seen_*.json`에 기록되어 재실행 시 신규만 다룬다. 다시 보려면 `--force`.

## 키워드·대상 (scripts/common.py)
- `KEYWORDS`: 본문 매칭 정규식(재개발(인재개발 제외)·재건축·정비사업·모아타운·신통기획·토지거래허가·분양가·주택공급·용적률/종상향·그린벨트·임대주택·전세/임대차·경매/공매·세제·재초환·리모델링·역세권/지구단위·도시재생/뉴타운·주요 구역명).
- `SMC_SEARCH_TERMS`: 서울시의회 검색폼용 단일 검색어 목록(폼이 한 단어만 받음).
- `ASSEMBLY_COMMITTEES`: 국회 감시 위원회(국토교통·기재/재정경제기획·행안·예결). 본회의는 항상 포함. 그 외 위원회는 안건명에 키워드가 있을 때만.
- 키워드 추가 요청은 이 파일만 고치면 된다.

## 요약 작성(LLM 단계) 지침
`reports/council/<날짜>-council.md` 를 읽고 `_workspace/council/llm_summary_<날짜>.md` 에 다음을 쓴다(마크다운, 총 12줄 이내):
1. **핵심 3~5줄**: 이번 기간 의회에서 부동산 관련해 실제로 결정·요구·예고된 것. 발언자 이름과 회의명을 붙인다.
2. **투자 시사점 2~3줄**: 특정 구역·정책(용적률 상향, 용산공원 주택, 신통기획 속도, 세제 등)이 어느 방향으로 움직이는지. 추정은 "추정"이라고 표시.
3. **주목 발언 2~3개**: 인용 1문장 + 발언자 + 회의.
원문에 없는 사실을 만들지 않는다. 회의록 발췌가 키워드 주변 260자 창이므로 맥락이 불확실하면 "맥락 확인 필요"로 표시한다.

## 수동 실행 예
```bash
S=/Users/leomyung/auction_news/.claude/skills/council-minutes-watch/scripts
python3 $S/collect_smc.py --days 7 && python3 $S/collect_assembly.py --days 7 && python3 $S/build_report.py
# 전체 무인 파이프라인(요약+발송 포함)
bash $S/run-council.sh
```

## 주의
- 서울시의회 검색 폼은 CSRF·세션 기반이라 curl로는 500. 반드시 Playwright.
- 국회 PDF는 `pdftotext -layout`이면 글자 순서가 깨진다. `-raw` 사용.
- 발언자 분리는 `○/◯ 직함 이름` 패턴 의존. 서울시의회는 이름 뒤 `\xa0\xa0`, 국회는 한 칸 공백.
- 국회 Open API의 `CONF_DATE`는 검색어 방식이라 하루 단위로 호출한다(days=7이면 14회).
