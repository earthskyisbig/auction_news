#!/bin/bash
# 주간 부동산 뉴스 브리핑 자동 실행 래퍼 (crontab용)
#
# crontab은 매일 07:00에 이 스크립트를 부르고, 실행 여부는 여기서 정한다:
#   - 이번 주(ISO 월~일) 스탬프가 있으면 종료 (이미 돌았음)
#   - 금요일 이전이면 종료 (아직 이름)
#   - 금·토·일이고 스탬프가 없으면 실행 (금요일에 맥이 꺼져 있었으면 토·일에 보정)
# 이렇게 하면 크론 한 줄로 정규 실행과 결손 보정이 모두 된다.
#
# cron은 최소 PATH로 실행되므로 필요한 바이너리 경로를 직접 설정한다.

export PATH="/Users/leomyung/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

PROJECT_DIR="/Users/leomyung/auction_news"
LOG_DIR="$PROJECT_DIR/logs"
STAMP_DIR="$PROJECT_DIR/_workspace/weekly"
mkdir -p "$LOG_DIR" "$STAMP_DIR"

WEEK="$(date +%G-W%V)"            # ISO 연-주 (월요일 시작)
DOW="$(date +%u)"                 # 1=월 … 7=일
STAMP="$STAMP_DIR/.done-$WEEK"
LOCK="$STAMP_DIR/.lock"
LOG_FILE="$LOG_DIR/weekly_$(date +%Y%m%d).log"

log(){ echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG_FILE"; }

# --- 실행 조건 ---------------------------------------------------------------
[ -f "$STAMP" ] && exit 0                      # 이번 주 이미 완료
[ "$DOW" -lt 5 ] && exit 0                     # 금요일 전

# --- 중복 실행 방지 (06:30 일일 브리핑과 겹칠 수 있음) -------------------------
if ! mkdir "$LOCK" 2>/dev/null; then
    # 3시간 넘은 락은 죽은 것으로 보고 회수
    if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +180 2>/dev/null)" ]; then
        log "오래된 락 회수"
        rmdir "$LOCK" 2>/dev/null
        mkdir "$LOCK" 2>/dev/null || exit 0
    else
        log "다른 실행이 진행 중 — 건너뜀"
        exit 0
    fi
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

cd "$PROJECT_DIR" || exit 1

# 무인 실행용 Claude 인증 토큰 로드(키체인 접근 불가한 cron 환경 대응)
ENV_FILE="$PROJECT_DIR/.claude/skills/realestate-news-daily/token.env"
if [ -f "$ENV_FILE" ]; then
    set -a; . "$ENV_FILE"; set +a
fi

# 기간: 직전 목요일 ~ 오늘. 목요일에 나오는 한국부동산원 주간동향을 포함시키기 위함.
if [ "$DOW" -eq 5 ]; then DAYS_BACK=1; else DAYS_BACK=$((DOW - 4)); fi
FROM="$(date -v-${DAYS_BACK}d +%Y-%m-%d)"
TO="$(date +%Y-%m-%d)"

log "===== 주간 브리핑 시작 (주 $WEEK, 기간 $FROM ~ $TO) ====="

claude -p "이번 주 부동산 뉴스 브리핑을 만들어줘. budongsan-news 스킬의 Step 1~7을 끝까지 수행한다.
무인 실행이므로 되묻지 말고 진행하고, 판독 기간은 --from $FROM --to $TO 로 잡는다.
아티팩트 게시는 건너뛰고 HTML 파일까지만 만든 뒤, reports/weekly/ 에 아카이브하고 커밋·푸시까지 마친다." \
  --dangerously-skip-permissions \
  --model claude-opus-5 \
  >> "$LOG_FILE" 2>&1
RC=$?

log "===== 종료 (exit=$RC) ====="

# 산출물이 실제로 생겼을 때만 이번 주 완료로 표시한다.
# (실패했으면 스탬프를 남기지 않아 토·일에 다시 시도된다)
if ls "$PROJECT_DIR"/reports/weekly/*-weekly-news.md >/dev/null 2>&1 && \
   [ -n "$(find "$PROJECT_DIR/reports/weekly" -maxdepth 1 -name '*-weekly-news.md' -mtime -1 2>/dev/null)" ]; then
    date '+%Y-%m-%d %H:%M:%S' > "$STAMP"
    log "완료 스탬프 기록: $STAMP"
    # 커밋되지 않은 산출물이 남아 있으면 마지막 안전망으로 올린다.
    if [ -n "$(git status --porcelain reports/weekly 2>/dev/null)" ]; then
        log "미커밋 산출물 발견 — 안전망 커밋"
        git add reports/weekly >> "$LOG_FILE" 2>&1
        git commit -q -m "주간 부동산 브리핑: $TO (자동 아카이브)" >> "$LOG_FILE" 2>&1
        git push -q origin main >> "$LOG_FILE" 2>&1 || log "푸시 실패 — 다음 실행에서 재시도"
    fi
else
    log "산출물 없음 — 스탬프 미기록, 다음 실행일에 재시도"
fi
