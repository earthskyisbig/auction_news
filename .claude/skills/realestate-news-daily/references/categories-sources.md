# 카테고리별 수집 소스 & 검색어

> 수집 전략: **WebFetch 우선(SSR 페이지) → 실패 시 WebSearch fallback**. fetch 실패 판단: 빈 페이지/200자 미만/JS 렌더링 오류/4xx·3xx/로그인 요구 → 즉시 WebSearch.
> 검색어의 `[연]`, `[월]`, `[주]`는 실행 시점 날짜로 치환한다.

## 목차
1. 정책·규제 (policy-rate-collector)
2. 금리·거시경제 (policy-rate-collector)
3. 시장 동향 (market-region-collector)
4. 지역별 소식 (market-region-collector)
5. 분양·청약 (market-region-collector)
6. 경매·NPL (auction-collector)
7. WebFetch 불가 소스

---

## 1. 정책·규제

**render_page.py 소스 (국토부 — WebFetch 리다이렉트 차단, 브라우저 렌더링 필요)** ✓검증
- 국토부 보도자료: `https://www.molit.go.kr/USR/NEWS/m_71/lst.jsp` — 제목·분야·등록일·조회수 표가 렌더링됨. **주택토지·국토도시 분야** 위주로 최신 5~7건 추출.
- 국토부 공지사항: `https://www.molit.go.kr/USR/BORD0201/m_69/BRD.jsp` — 공지 목록(제목·날짜) 최신 5건.
```
python3 .claude/skills/realestate-news-daily/scripts/render_page.py \
  --url "https://www.molit.go.kr/USR/NEWS/m_71/lst.jsp" \
  --url "https://www.molit.go.kr/USR/BORD0201/m_69/BRD.jsp" --max-chars 4000
```
렌더링 텍스트에서 수집기간(예: 어제~오늘) 날짜에 해당하는 항목만 골라, 제목이 중요하면 해당 상세를 WebSearch로 보강한다.

**WebFetch 소스**
- 금융위 보도자료(부동산): `https://www.fsc.go.kr/no010101?srchKey=sj&srchText=부동산`
- 금융위 보도자료(DSR): `https://www.fsc.go.kr/no010101?srchKey=sj&srchText=DSR`

**WebSearch 검색어**
- `부동산 정책 규제 [연]년 [월]월`
- `부동산 대출 규제 LTV DSR 최신`
- `주택 세제 양도세 취득세 [연]년 [월]월`

## 2. 금리·거시경제

**WebFetch 소스**
- 한국은행 기준금리 이력(SSR ✓): `https://www.bok.or.kr/portal/singl/baseRate/list.do?dataSeCd=01&menuNo=200643` — 현재 기준금리 + 최근 금통위 결정.
- 주금공 보금자리론 금리: `https://www.hf.go.kr/ko/sub01/sub01_01_04.do`
- 주금공 디딤돌 대출 금리: `https://www.hf.go.kr/ko/sub01/sub01_02_03.do`

**WebSearch 검색어**
- `한국은행 기준금리 [연]년 [월]월`
- `주담대 금리 코픽스 최신`
- `금통위 [연]년 [월]월 결정`

## 3. 시장 동향

**WebFetch 소스**
- 한국부동산원 주간 아파트 가격동향 목록: `https://www.reb.or.kr/reb/cm/cntnts/cntntsView.do?mi=10001&cntntsId=1308`
- 투데영 서울 구별 평당가(SSR ✓★): `https://www.todayoung.com/apart/1100000000.html`
- 투데영 경기 시군별 평당가(SSR ✓★): `https://www.todayoung.com/apart/4100000000.html`

**render_page.py 소스 (JS SPA — 브라우저 렌더링 필요)** ✓검증
- 아실(실거래·거래량·순위): `https://asil.kr/asil/index.jsp` — 시도별 세대수, 순위/가격 분석. 특정 지역 데이터는 지역 선택 URL이 필요할 수 있으니 우선 랜딩에서 잡히는 거래량·랭킹·시세 요약을 추출.
- 호갱노노(인기단지·실시간 시세): `https://hogangnono.com` — 평형별 시세와 "N명 보는중"(관심도) 신호. 단지명이 안 보이면 추세/관심 신호로만 활용.
```
python3 .claude/skills/realestate-news-daily/scripts/render_page.py \
  --url "https://asil.kr/asil/index.jsp" --url "https://hogangnono.com" --wait-ms 6000 --max-chars 6000
```
> 이 두 사이트는 지도·상호작용 기반이라 랜딩 텍스트만으로는 정보가 제한적일 수 있다. 핵심 수치(매매/전세가, 거래량, 전세가율)는 한국부동산원·KB 검색으로 교차 확인하고, 아실/호갱노노는 **관심도·인기단지·시세 참고**로 보조 활용한다. 렌더 실패 시 WebSearch로 폴백.

**WebSearch 검색어**
- `한국부동산원 주간 아파트 매매가 전세가 [연]년 [월]월`
- `KB부동산 주간 시계열 [연]년 [월]월 [주]주`
- `아파트 거래량 [연]년 [월]월`

## 4. 지역별 소식

**WebFetch 소스**
- 서울시 부동산 정보광장: `https://land.seoul.go.kr/land/rtms/aptTrend.do` (구별 변동률 테이블, 기준일 명시)

**WebSearch 검색어**
- `서울 수도권 아파트 거래 [연]년 [월]월 [주]주`
- `[광역시명] 부동산 [연]년 [월]월` (부산·대구·대전·광주 순환)
- `재건축 재개발 [연]년 [월]월`

## 5. 분양·청약

**WebFetch 소스**
- 청약홈 APT 청약 목록: `https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancListView.do` — 단지명·지역·청약일·세대수, 경쟁률 있으면 함께.

**WebSearch 검색어**
- `아파트 청약 분양 경쟁률 [연]년 [월]월`
- `이번 주 청약 일정 [연]년 [월]월`
- `분양가 상한제 [연]년 [월]월`

## 6. 경매·NPL

> 경매 통계는 주간·월간 발표가 많아 매일 신규가 없을 수 있다. 신규가 없으면 직전 지표 유지로 기록.

**WebSearch 검색어 (1차)**
- `법원경매 낙찰가율 응찰자수 [연]년 [월]월`
- `아파트 경매 낙찰 통계 지지옥션 옥션원 [연]년 [월]월`
- `부동산 경매 시장 동향 [연]년 [월]월`
- `NPL 부실채권 부동산 [연]년 [월]월`
- `경매 권리분석 명도 판례 [연]년 [월]월`
- `공매 온비드 부동산 [연]년 [월]월`

**경매 전문 통계 소스 (WebSearch로 최신 보도 확인)**: 지지옥션, 옥션원, 탱크옥션 월간 통계 보도.

**정량 물건 데이터(선택)**: 스킬 `court-auction-scraper` (법원경매정보 courtauction.go.kr 스크래핑). IP 차단·헤드리스 감지 위험이 있어 **오케스트레이터가 명시 요청할 때만** 사용. 평소엔 뉴스·통계로 충분.

---

## 7. WebFetch 불가 소스 → 대안

`scripts/render_page.py`는 헤드리스 브라우저로 JS 페이지를 렌더링해 본문 텍스트를 반환한다(headless로 작동 → cron 무인 실행 OK). 사이트 셀렉터에 의존하지 않으므로 구조 변경에 강하다. **렌더 실패 시 WebSearch로 폴백한다.**

| 소스 | WebFetch | render_page.py | 비고 |
|------|---------|----------------|------|
| 국토부 보도자료/공지 | ❌ 리다이렉트 | ✅ 검증됨 | 표 전체 렌더 |
| 아실(asil.kr) | ❌ | ✅ 검증됨 | 지도 기반, 보조 활용 |
| 호갱노노 | ❌ | ✅ 검증됨 | 관심도/시세 참고 |
| KB부동산 | ❌ JS SPA | △ 시도 가능 | 안 되면 WebSearch |
| 한국부동산원 가격동향 상세 | ❌ JS SPA | △ 시도 가능 | 안 되면 WebSearch |
| ECOS(한국은행 통계) | ❌ Webpack SPA | △ | WebSearch 권장 |
| courtauction.go.kr | ❌ IP차단 | ❌ headless 감지 | 전용 스킬 `court-auction-scraper`(headful) 필요 |

**render_page.py 사용 패턴:**
```
python3 .claude/skills/realestate-news-daily/scripts/render_page.py --url "<URL>" [--url "<URL2>"] [--wait-ms 6000] [--max-chars 8000]
```
출력 텍스트에서 수집기간 날짜 항목만 골라 출처·날짜와 함께 정리. 시간이 오래 걸리면(브라우저 기동) WebSearch를 먼저 쓰고 render는 핵심 소스에만 쓴다.

## 데이터 품질 원칙 (전 수집가 공통)

- 출처 없는 수치 금지 — 가격·금리·낙찰가율 등 모든 수치에 출처·기준일.
- 추측 금지 — 미확인 정보는 "확인 필요".
- 날짜 엄격 — 지정 수집 기간 밖 기사 제외.
- 분량 우선순위 — 뉴스 많은 카테고리는 상세히, 없으면 "이번 기간 주요 동향 없음".
