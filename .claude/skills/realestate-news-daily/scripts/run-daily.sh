#!/bin/bash
# 일일 부동산·경매 뉴스 하네스 자동 실행 래퍼 (crontab용)
# cron은 최소 PATH로 실행되므로 필요한 바이너리 경로를 직접 설정한다.

export PATH="/Users/leomyung/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

PROJECT_DIR="/Users/leomyung/auction_news"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/daily_$(date +%Y%m%d).log"

cd "$PROJECT_DIR" || exit 1

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 시작 =====" >> "$LOG_FILE"

# headless 실행. .claude/ 의 스킬/에이전트를 자동 인식한다.
# --dangerously-skip-permissions: 무인 실행이므로 권한 프롬프트를 건너뛴다(개인 머신 자동화).
claude -p "오늘 부동산·경매 투자 뉴스 모아서 일일 브리핑 만들고 발송해줘" \
  --dangerously-skip-permissions \
  --model claude-opus-4-8 \
  >> "$LOG_FILE" 2>&1

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 종료 (exit=$?) =====" >> "$LOG_FILE"
