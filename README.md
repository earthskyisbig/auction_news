# auction_news — 일일 부동산·경매 투자 뉴스 하네스

대한민국 부동산·경매 투자 뉴스를 **매일 자동 수집·검증**하여 일일 브리핑으로 정리하고, 파일·데스크톱 알림·이메일·텔레그램으로 발송하는 Claude Code 하네스.

## 구성

- **에이전트** (`.claude/agents/`): 수집가 3명(정책·금리 / 시장·지역·청약 / 경매·NPL) + 편집·검증가 1명
- **오케스트레이터 스킬** (`.claude/skills/realestate-news-daily/`): 수집 3명 병렬 → 편집·검증 통합 (하이브리드 실행)
- **수집 소스**: 카테고리별 1차 기관 fetch + WebSearch. JS/리다이렉트로 막힌 사이트(국토부 보도자료·공지, 아실, 호갱노노)는 `render_page.py`(Playwright headless)로 렌더링 → 실패 시 WebSearch 폴백
- **발송** (`scripts/deliver.py`): 파일 / macOS 알림 / 이메일(SMTP) / 텔레그램(요약 + 리포트 문서)
- **양방향 텔레그램 봇** (`scripts/telegram_bot.py`): 텔레그램 메시지로 하네스에 지시 → 결과 회신 (launchd 상주)
- **정기 실행**: 평일 06:30 crontab (`scripts/run-daily.sh`)

## 사용

```bash
# 수동 실행
claude -p "오늘 부동산·경매 뉴스 모아줘"
```

## 설정 (선택)

이메일·텔레그램 발송을 켜려면 `.claude/skills/realestate-news-daily/delivery-config.example.json`을
`delivery-config.json`으로 복사 후 값을 채운다 (방법: `references/delivery-setup.md`).
이 파일은 비밀값을 담으므로 `.gitignore`로 제외된다.

## 의존성

- [Claude Code](https://claude.com/claude-code)
- Playwright + chromium (`pip3 install playwright --break-system-packages && python3 -m playwright install chromium`) — JS 사이트 렌더링용

---
*생성 산출물(reports/·logs/·_workspace/)과 비밀값(delivery-config.json)은 git에서 제외됩니다.*
