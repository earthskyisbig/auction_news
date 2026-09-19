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
