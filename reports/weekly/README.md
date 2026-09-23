# 주간 부동산 뉴스 리포트 (Jev 판독 파이프라인)

일일 브리핑(`reports/*-realestate-daily.md`)과 별개로, 주 1회 수집분을 TypeSafe Jev(System One)로
판독·선별해 작성한 주간 리포트를 아카이브한다.

## 파이프라인

```
WebFetch/WebSearch 수집 → candidates.json
  → scripts/news_jev.py           # 기사당 5문항 판독 + 코드 컷오프 → jev_news.{json,md}
  → 리포트 작성 (jev_news.md 채택 순서대로)
  → doc-eval -r news              # 리포트 자체 품질 검사, 종합 75 이상 통과
```

## 재현

```bash
# 판독 (TYPESAFE_API_KEY 필요, ~/doc-eval/.env 에서 자동 로드)
python3 scripts/news_jev.py reports/weekly/news-2026-09-23/candidates.json \
        --from 2026-09-18 --to 2026-09-27

# 임계값만 바꿔 재집계 (API 재호출 없음)
python3 scripts/news_jev.py <jev_news.json> --resummarize --min-priority 45

# 리포트 품질 검사 (scripts/rubrics/news.json 을 ~/doc-eval/rubrics/ 에 두고 실행)
cd ~/doc-eval && uv run doc-eval <리포트.md> -r news
```

## 파일

| 경로 | 내용 |
|---|---|
| `YYYY-MM-DD-weekly-news.md` | 주간 리포트 본문 |
| `news-YYYY-MM-DD/candidates.json` | 수집 원본(판독 입력) |
| `news-YYYY-MM-DD/jev_news.md` | 판독 결과 — 채택·제외 사유·영향도·방향 |
| `news-YYYY-MM-DD/jev_news.json` | 판독 원자료(확률 분포·토큰 사용량 포함) |

## 원본 위치

`scripts/news_jev.py`와 `scripts/rubrics/news.json`은 **아카이브 사본**이다. 원본은
`~/.claude/skills/budongsan-news/scripts/news_jev.py`, `~/doc-eval/rubrics/news.json`이며
수정은 원본에서 한 뒤 여기로 복사한다.

## 판독 결과 읽는 법

- **우선순위(0~100)** = 영향도 정규화 + 출처 티어 보정(T1 +5 / T3 −10) − 전망성 10 − 수치 미명시 5
- **영향도 x.x/4** — 4에 가까울수록 시장 규칙 자체가 바뀌는 사안(기준금리·대출 총량·공급대책)
- Jev는 본문에 적힌 것만 판단한다. **선별 근거이지 사실 검증이 아니다** — 채택 기사 수치는 원문 확인이 필요하다.
- 영향도는 전국 파급을 보므로 국지 뉴스가 컷오프 아래로 떨어진다. 리더가 복원할 경우 리포트 본문에 그 사실을 명시한다.
