#!/bin/bash
# 생성된 리포트를 git에 아카이빙(add → commit → push).
# reports/ 만 스테이징하므로 비밀값(delivery-config.json)·로그는 절대 커밋되지 않는다.
# 푸시 실패해도 하네스 실행을 막지 않는다(로컬 커밋은 남김, 로그에 기록).

export PATH="/Users/leomyung/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
PROJECT_DIR="/Users/leomyung/auction_news"
cd "$PROJECT_DIR" || exit 0

LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/archive_$(date +%Y%m%d).log"
ts() { date '+%Y-%m-%d %H:%M:%S'; }

# 변경된 리포트가 없으면 종료
if [ -z "$(git status --porcelain reports/ 2>/dev/null)" ]; then
    echo "$(ts) 변경된 리포트 없음, 스킵" >> "$LOG"
    exit 0
fi

# reports/ 만 스테이징
git add reports/ >> "$LOG" 2>&1

# 🔒 안전 가드: 스테이징에 텔레그램 봇 토큰 패턴이 있으면 중단(비정상 상황 방어)
# 토큰 형태: 숫자8~12자리:AA+영숫자 → 실제 토큰을 하드코딩하지 않고 패턴으로 탐지
if git grep -I -E -q -e '[0-9]{8,12}:AA[0-9A-Za-z_-]{30,}' --cached 2>/dev/null; then
    echo "$(ts) ❌ 스테이징에서 봇 토큰 패턴 감지 — 아카이브 중단" >> "$LOG"
    git reset -q
    exit 1
fi

git commit -q -m "리포트 아카이브: $(date +%Y-%m-%d)" >> "$LOG" 2>&1

if git push origin main >> "$LOG" 2>&1; then
    echo "$(ts) ✅ 푸시 성공" >> "$LOG"
else
    echo "$(ts) ⚠️ 푸시 실패(로컬 커밋은 완료). git 인증 확인 필요." >> "$LOG"
fi
