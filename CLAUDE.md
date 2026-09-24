# auction_news

## 하네스: 일일 부동산·경매 투자 뉴스

**목표:** 대한민국 부동산·경매 투자 뉴스를 매일 자동 수집·검증하여 일일 브리핑으로 정리하고 파일·데스크톱알림·이메일·텔레그램으로 발송한다.

**트리거:** 부동산/경매 뉴스 수집·브리핑·리포트 관련 요청(초기·후속·부분 재실행 포함) 시 `realestate-news-daily` 스킬을 사용하라. 서울시의회·국회 회의록 관련 요청은 `council-minutes-watch` 스킬. 단순 단발 질문은 직접 응답 가능.

**구성 요약:** 서브 에이전트 하이브리드(수집가 3명 병렬 → 편집·검증가 1명). 세부 에이전트/스킬 목록은 `.claude/agents/`, `.claude/skills/realestate-news-daily/`에서 관리한다.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-07-01 | 초기 구성 (수집가 3 + 편집가 1 + 오케스트레이터 + 다중채널 발송) | 전체 | - |
| 2026-07-01 | 평일 06:30 자동 실행 등록 (run-daily.sh + crontab) | scripts/run-daily.sh | "매일 아침 정기 수집" 요청 |
| 2026-07-01 | 텔레그램 양방향 봇 추가 (수신 명령→claude 실행→회신, 리포트 전문 문서 발송) | scripts/telegram_bot.py + launchd | "텔레그램에서 뉴스 보고 지시" 요청 |
| 2026-07-01 | 브라우저 렌더링 소스 추가 (국토부 보도자료·공지, 아실, 호갱노노) | scripts/render_page.py + categories-sources.md + 수집가 2명 | WebFetch 차단 사이트 스크래핑 요청 |
| 2026-07-01 | GitHub 저장소 연결 + 리포트 매일 자동 아카이빙 | scripts/archive_report.sh + run-daily.sh + .gitignore | 리포트 git 아카이빙 요청 |
| 2026-07-02 | 텔레그램: 리포트를 채팅 본문 텍스트로 분할 전송(문서 첨부 옵션화) | scripts/deliver.py | ".md 대신 채팅에서 직접 보기" 요청 |
| 2026-07-03 | 무인 실행 인증 토큰 도입(cron 키체인 접근 불가 해결) | token.env(gitignore) + run-daily.sh + telegram_bot.py | 06:30 cron이 "Not logged in"으로 실패 |
| 2026-09-19 | 연예인 부동산 거래 지도(매입·매도·경매·매물 89건, 선행지표 섹션) 생성 + 데이터·빌드 스크립트 보관 | reports/celeb-realestate-map.html, reports/celeb-realestate-data.json, scripts/build_celeb_map.py, scripts/celeb_data.py | "연예인 매입 물건을 선행지표로 지도에 표시" 요청 |
| 2026-09-19 | 의회 회의록 감시 스킬 추가(서울시의회 Playwright 검색 + 국회 열린국회정보 API/PDF → 발언 추출 → LLM 요약 → 텔레그램) + 평일 07:30 cron | .claude/skills/council-minutes-watch/, deliver.py(--title/--attach), reports/council/ | "시의회·국회 회의록 부동산 관련 정기 검색" 요청 |
| 2026-09-19 | 서울시 도시계획위원회 등 7개 위원회 심의결과 수집 단계 추가(commission.eseoul.go.kr) | council-minutes-watch/scripts/collect_seoul_committees.py, build_report.py, run-council.sh | "서울시 도시계획위원회 등도 추가 검색" 요청 |
| 2026-09-23 | 주간 리포트 라인 추가: Jev(TypeSafe System One) 판독으로 기사 선별·등급화 → 리포트 작성 → doc-eval `news` 루브릭 품질 검사. 첫 회차(2026-09-23) 후보 19건→채택 11건+리더 복원 2건, 품질 88.0 무플래그 | reports/weekly/, scripts/news_jev.py, scripts/rubrics/news.json | 일일 브리핑과 별개로 주 1회 선별 근거가 남는 리포트가 필요 |
| 2026-09-23 | 교훈: Jev 영향도는 전국 파급 기준이라 국지 뉴스(노원 +1.68%, 재건축 추진위)가 컷오프 미달로 탈락한다. 섹션 정원으로도 못 살리면 리더가 복원하고 리포트에 명시한다. 판독기는 선별 보조이지 결정권자가 아니다 | reports/weekly/README.md | 첫 실전 운영 |
| 2026-09-23 | 주간 리포트 웹 브리핑 추가(algo-design 토큰, 칩 필터·우선순위 막대·두 기관 비교·판독 분포 막대). claude.ai 아티팩트로도 게시 | reports/weekly/2026-09-23-weekly-news.html | 마크다운만으로는 판독 결과가 한눈에 안 들어옴 |
| 2026-09-24 | 주간 브리핑 무인화: `scripts/run-weekly.sh` + crontab 매일 07:00 호출(스크립트가 금요일에만 실행, 토·일 결손 보정, 주간 스탬프·락). budongsan-news 스킬에 Step 6(HTML 브리핑)·Step 7(아카이브·커밋)과 무인 실행 규칙 추가 | scripts/run-weekly.sh, ~/.claude/skills/budongsan-news/SKILL.md | "다음 주 브리핑도 이 흐름으로 자동화" 요청. 목요일 부동산원 발표를 담으려고 금요일 기준 |
| 2026-09-25 | 주간 브리핑 2회차(기간 9/24~9/25). 후보 16건 → Jev 채택 6건 + 리더 복원 3건, 품질 85.6 무플래그. 아티팩트 게시 생략, HTML까지만 | reports/weekly/2026-09-25-weekly-news.{md,html} | 사용자 지시(무인 실행, Step 1~7) |
| 2026-09-25 | 교훈: 공휴일이 낀 주는 '직전 목요일~실행일' 2일 창으로 잡으면 금리·지역·경매 섹션이 구조적으로 0건이 된다. 리더가 기간 직전 자료를 복원하되 본문·HTML에 복원 표시를 단다. 다음부터 연휴 주는 --from을 한 주 앞으로 늘린다 | reports/weekly/README.md | 추석(9/25) 연휴와 판독 기간이 겹침 |

