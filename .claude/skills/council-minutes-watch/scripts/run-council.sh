#!/bin/bash
# 의회 회의록 부동산 감시 무인 실행 래퍼 (crontab용)
# 수집(서울시의회·국회) → 규칙 기반 리포트 → LLM 요약(실패해도 진행) → 텔레그램 발송
export PATH="/Users/leomyung/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

PROJECT_DIR="/Users/leomyung/auction_news"
S="$PROJECT_DIR/.claude/skills/council-minutes-watch/scripts"
NEWS="$PROJECT_DIR/.claude/skills/realestate-news-daily"
LOG_DIR="$PROJECT_DIR/logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/council_$(date +%Y%m%d).log"
DAYS="${1:-7}"
TODAY=$(date +%Y-%m-%d)
WORK="$PROJECT_DIR/_workspace/council"
REPORT="$PROJECT_DIR/reports/council/${TODAY}-council.md"
LLM="$WORK/llm_summary_${TODAY}.md"

cd "$PROJECT_DIR" || exit 1
# 무인 실행용 Claude 인증 토큰(cron은 키체인 접근 불가)
[ -f "$NEWS/token.env" ] && { set -a; . "$NEWS/token.env"; set +a; }

echo "===== $(date '+%F %T') 시작 (days=$DAYS) =====" >> "$LOG"
python3 "$S/collect_smc.py" --days "$DAYS" >> "$LOG" 2>&1
python3 "$S/collect_assembly.py" --days "$DAYS" >> "$LOG" 2>&1
python3 "$S/collect_seoul_committees.py" --days "$DAYS" >> "$LOG" 2>&1
python3 "$S/build_report.py" --date "$TODAY" >> "$LOG" 2>&1

# 신규 회의록이 없으면 발송 생략
N=$(python3 -c "import json,glob;print(sum(len(json.load(open(f))) for f in glob.glob('$WORK/*_${TODAY}.json') if 'summary' not in f))" 2>/dev/null || echo 0)
if [ "${N:-0}" = "0" ]; then
  echo "신규 회의록 없음 → 발송 생략" >> "$LOG"; echo "===== $(date '+%F %T') 종료 =====" >> "$LOG"; exit 0
fi

# LLM 요약(도메인 판단 → opus). 실패해도 규칙 기반 리포트로 발송.
rm -f "$LLM"
claude -p "council-minutes-watch 스킬의 '요약 작성(LLM 단계) 지침'에 따라 $REPORT 를 읽고 $LLM 파일에 핵심 요약을 작성해라. 다른 파일은 수정하지 말고 발송도 하지 마라." \
  --dangerously-skip-permissions --model claude-opus-4-8 >> "$LOG" 2>&1 || echo "LLM 요약 실패(무시)" >> "$LOG"
if [ -s "$LLM" ]; then
  python3 "$S/build_report.py" --date "$TODAY" --summary-file "$LLM" >> "$LOG" 2>&1
fi

python3 "$NEWS/scripts/deliver.py" --report "$WORK/digest_${TODAY}.md" --summary "$WORK/summary_${TODAY}.txt" \
  --attach "$REPORT" --title "🏛️ 의회 회의록 부동산 브리핑" >> "$LOG" 2>&1
echo "===== $(date '+%F %T') 종료 (exit=$?) =====" >> "$LOG"

# 리포트 git 아카이빙(실패 무시)
cd "$PROJECT_DIR" && git add reports/council "$PROJECT_DIR/.claude/skills/council-minutes-watch/state" >/dev/null 2>&1 \
  && git commit -q -m "의회 회의록 브리핑: ${TODAY}" >/dev/null 2>&1 && git push -q origin main >/dev/null 2>&1 || true
