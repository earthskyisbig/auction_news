#!/usr/bin/env python3
"""
텔레그램 양방향 봇 — 인증된 사용자의 메시지를 받아 claude headless로 실행하고 결과를 회신한다.

흐름: getUpdates 롱폴링 → 인증 chat 메시지면 → `claude -p "<메시지>"` 실행 → 결과를 텔레그램으로 회신.
뉴스 수집 명령이면 하네스가 내부적으로 deliver.py를 호출해 리포트 전문도 별도로 발송한다.

보안: delivery-config.json 의 chat_id 와 일치하는 발신자만 응답한다. 그 외는 무시(로그만).
설정: token/chat_id 는 delivery-config.json 의 channels.telegram 에서 읽는다.

실행: launchd(권장) 또는 `nohup python3 telegram_bot.py &`. 노트북이 깨어 있을 때만 동작한다(절전 시 폴링 중단).
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

CFG = Path(__file__).parent.parent / "delivery-config.json"
PROJECT_DIR = "/Users/leomyung/auction_news"
CLAUDE = "/Users/leomyung/.local/bin/claude"
CLAUDE_ENV = dict(os.environ, PATH="/Users/leomyung/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin")
MAX_RUN_SEC = 1800  # claude 실행 최대 30분


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def load_cfg():
    cfg = json.load(open(CFG, encoding="utf-8"))
    tg = cfg["channels"]["telegram"]
    return tg["bot_token"], str(tg["chat_id"])


def api(token, method, params, timeout=70):
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=timeout) as r:
        return json.load(r)


def send(token, chat_id, text):
    """4096자 제한 → 분할 전송."""
    text = text or "(빈 응답)"
    for i in range(0, len(text), 3800):
        try:
            api(token, "sendMessage", {"chat_id": chat_id, "text": text[i:i + 3800]}, timeout=30)
        except Exception as e:
            log(f"send 실패: {e}")


def run_claude(prompt):
    try:
        p = subprocess.run(
            [CLAUDE, "-p", prompt, "--dangerously-skip-permissions", "--model", "claude-opus-4-8"],
            cwd=PROJECT_DIR, capture_output=True, text=True, timeout=MAX_RUN_SEC, env=CLAUDE_ENV)
        out = (p.stdout or "").strip()
        if not out:
            out = (p.stderr or "").strip()
        return out or "(빈 응답)"
    except subprocess.TimeoutExpired:
        return "⏱️ 작업이 30분을 초과해 중단했습니다. 더 좁은 요청으로 다시 시도해 주세요."
    except Exception as e:
        return f"실행 오류: {e}"


def drain_backlog(token):
    """시작 시 밀린 과거 메시지를 처리하지 않도록 offset만 최신으로 맞춘다."""
    try:
        resp = api(token, "getUpdates", {"timeout": 0}, timeout=15)
        results = resp.get("result", [])
        if results:
            return results[-1]["update_id"] + 1
    except Exception as e:
        log(f"drain 실패(무시): {e}")
    return None


HELP = (
    "📰 부동산·경매 뉴스 봇\n\n"
    "메시지를 보내면 하네스를 실행해 결과를 보냅니다.\n\n"
    "예시:\n"
    "• 오늘 부동산 뉴스 모아줘\n"
    "• 정책만 다시 해줘\n"
    "• 어제 결과 기반으로 업데이트\n"
    "• 서울 경매 낙찰가율 요약해줘\n\n"
    "※ 뉴스 수집은 수 분 걸릴 수 있어요. 리포트 전문은 문서로 따로 도착합니다."
)


def main():
    token, auth = load_cfg()
    log(f"봇 시작 (authorized chat_id={auth})")
    offset = drain_backlog(token)
    send(token, auth, "🤖 봇이 켜졌습니다. /help 로 사용법을 보세요.")

    while True:
        try:
            params = {"timeout": 60}
            if offset:
                params["offset"] = offset
            resp = api(token, "getUpdates", params)
        except Exception as e:
            log(f"getUpdates 실패: {e}")
            time.sleep(5)
            continue

        for u in resp.get("result", []):
            offset = u["update_id"] + 1
            msg = u.get("message") or {}
            chat = str(msg.get("chat", {}).get("id", ""))
            text = (msg.get("text") or "").strip()
            if not text:
                continue
            if chat != auth:
                log(f"미인증 발신자 무시: chat_id={chat}")
                continue
            log(f"수신: {text[:80]}")
            if text in ("/start", "/help"):
                send(token, auth, HELP)
                continue
            send(token, auth, f"⏳ 처리 중: {text[:60]}\n(완료까지 잠시 기다려 주세요)")
            reply = run_claude(text)
            send(token, auth, reply)
            log("회신 완료")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("종료")
        sys.exit(0)
