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
| `YYYY-MM-DD-weekly-news.html` | 같은 내용의 웹 브리핑 (algo-design 토큰: 크림 배경 + 오렌지/블루 액센트). 카테고리 칩 필터·우선순위 막대·두 기관 통계 비교 포함 |
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

## 자동 실행

`scripts/run-weekly.sh`가 crontab에서 **매일 07:00** 호출되고, 실행 여부는 스크립트가 정한다:

| 조건 | 동작 |
|---|---|
| 이번 주(ISO 월~일) 스탬프 있음 | 종료 — 이미 돌았다 |
| 금요일 이전 | 종료 — 아직 이르다 |
| 금·토·일 + 스탬프 없음 | 실행 — 금요일에 맥이 꺼져 있었으면 토·일에 보정된다 |

금요일을 기준으로 삼은 이유는 한국부동산원 주간동향이 목요일에 나오기 때문이다.
판독 기간은 직전 목요일부터 실행일까지로 잡는다.

- 스탬프: `_workspace/weekly/.done-YYYY-Www` (gitignore). 산출물이 실제로 생겼을 때만 기록하므로,
  실패한 주는 다음 날 다시 시도된다.
- 락: `_workspace/weekly/.lock` — 06:30 일일 브리핑과 겹칠 때 중복 실행을 막는다(3시간 지나면 회수).
- 로그: `logs/weekly_YYYYMMDD.log`
- 푸시 인증: **deploy key**. cron은 GUI 키체인에 접근할 수 없어 https + osxkeychain 조합이 실패한다
  (2026-09-25 실제로 커밋만 쌓이고 푸시가 조용히 멈췄다). 원격은 `git@github-auction-news:...` 별칭을 쓰고,
  키는 `~/.ssh/auction_news_deploy` — **이 저장소에만** 통하므로 유출돼도 다른 저장소·계정은 안전하다.
  ssh 별칭 정의는 `~/.ssh/config`. 되돌리려면
  `git remote set-url origin https://github.com/earthskyisbig/auction_news.git`.
- 푸시가 실패하면 텔레그램으로 알린다(`notify_push_failure`). 로그에만 남기면 아무도 모른다.
- 실행 내용은 전역 스킬 `~/.claude/skills/budongsan-news/`의 Step 1~7이다. 스킬이 없으면 이 자동화도 돌지 않는다.

수동으로 한 회차 돌리려면 스탬프를 지우고 스크립트를 부르거나, 대화에서 `/budongsan-news`를 쓴다.

```bash
rm -f _workspace/weekly/.done-$(date +%G-W%V) && ./scripts/run-weekly.sh
```

## 웹 브리핑

`*-weekly-news.html`은 마크다운 리포트와 같은 내용을 읽기용으로 만든 단일 파일 페이지다.
외부 의존은 Google Fonts(Poppins/Lora)뿐이고 나머지 CSS·JS는 인라인이라 그냥 열면 된다.
디자인 토큰은 `~/.claude/skills/algo-design/assets/tokens.css`를 따른다.

| 회차 | 후보 → 채택 | 품질 | claude.ai 아티팩트 |
|---|---|---:|---|
| 2026-09-23 | 19건 → 11건 + 리더 복원 2건 | 88.0 | https://claude.ai/artifact/F6q2tvD9ndEns4ihS7b7Jr (비공개) |
| 2026-09-25 | 16건 → 6건 + 리더 복원 3건 | 85.6 | 게시 안 함 (무인 실행) |

### 2026-09-25 회차 메모

판독 기간이 **9/24(목)~9/25(금) 2일**이고 그중 9/25가 추석 당일이었다. 후보 16건 중 9건이 기간 외로
탈락했고, 채택 6건 중 3건이 같은 한국부동산원 발표(9월 3주)를 다룬 기사였다. **금리·거시경제·지역별
소식·경매 세 섹션이 기간 내 자료 0건**이어서 리더가 기간 직전 3건(한은 금융안정 9/22, 서울 경매
낙찰가율 9/18, 경기 10월 분양 9/23)을 복원하고 본문·HTML에 모두 복원 표시를 달았다.

교훈: **연휴가 낀 주는 2일 창으로 잡으면 섹션이 구조적으로 빈다.** `run-weekly.sh`가 직전 목요일부터
잡는 기본 규칙은 평상시에는 맞지만, 공휴일이 끼면 `--from`을 한 주 앞으로 늘리는 편이 낫다.
한국부동산원·한국은행 보도자료 게시판은 이번에도 SPA라 WebFetch에 실패해 언론 인용본을 썼다.
