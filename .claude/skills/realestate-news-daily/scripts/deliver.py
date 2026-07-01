#!/usr/bin/env python3
"""
일일 부동산·경매 뉴스 리포트 다중 채널 발송 스크립트.

채널: file(항상) / macos_notification / email / telegram
설정: 같은 폴더의 delivery-config.json (없으면 file + 알림만 동작).
비밀값(이메일 비번, 텔레그램 토큰)은 config 파일 또는 환경변수로 주입.

사용법:
  python3 deliver.py --report <리포트.md> --summary <summary.txt> [--config <config.json>]

각 채널은 독립적으로 시도하며, 한 채널 실패가 다른 채널을 막지 않는다.
종료 코드: 0=모든 활성 채널 성공, 1=일부 실패(stderr에 상세).
"""
import argparse
import json
import os
import smtplib
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def load_config(path: Path) -> dict:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def env_or(cfg: dict, key: str, env: str):
    """config 값 우선, 없으면 환경변수."""
    return cfg.get(key) or os.environ.get(env)


def deliver_notification(cfg: dict, title: str, summary: str) -> tuple[bool, str]:
    """macOS 데스크톱 알림 (osascript)."""
    if not cfg.get("enabled", True):
        return True, "notification: disabled (skip)"
    # 알림 본문은 길면 잘리므로 첫 200자만
    body = summary.replace('"', "'").replace("\n", " ")[:200]
    safe_title = title.replace('"', "'")
    script = f'display notification "{body}" with title "{safe_title}" sound name "Glass"'
    try:
        subprocess.run(["osascript", "-e", script], check=True,
                       capture_output=True, timeout=15)
        return True, "notification: sent"
    except Exception as e:
        return False, f"notification: FAILED ({e})"


def deliver_email(cfg: dict, subject: str, summary: str, report_md: str) -> tuple[bool, str]:
    if not cfg.get("enabled", False):
        return True, "email: disabled (skip)"
    host = cfg.get("smtp_host", "smtp.gmail.com")
    port = int(cfg.get("smtp_port", 587))
    user = env_or(cfg, "smtp_user", "RE_NEWS_SMTP_USER")
    password = env_or(cfg, "smtp_password", "RE_NEWS_SMTP_PASSWORD")
    to_addr = cfg.get("to") or user
    if not user or not password:
        return False, "email: FAILED (smtp_user/smtp_password 미설정)"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    text = f"{summary}\n\n{'='*40}\n\n{report_md}"
    msg.attach(MIMEText(text, "plain", "utf-8"))
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=ctx)
            server.login(user, password)
            server.sendmail(user, [to_addr], msg.as_string())
        return True, f"email: sent to {to_addr}"
    except Exception as e:
        return False, f"email: FAILED ({e})"


def _tg_send_document(token: str, chat_id: str, file_path: str, caption: str) -> bool:
    """리포트 전문을 텔레그램 문서로 전송(폰에서 바로 열람 가능). multipart/form-data."""
    boundary = "----RENEWSBOUNDARY7MA4YWxkTrZu0gW"
    fname = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        file_data = f.read()
    parts = []

    def field(name, value):
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())

    field("chat_id", chat_id)
    if caption:
        field("caption", caption[:1000])
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="document"; '
        f'filename="{fname}"\r\nContent-Type: text/markdown\r\n\r\n'.encode())
    parts.append(file_data)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendDocument", data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read()).get("ok", False)


def deliver_telegram(cfg: dict, summary: str, report_path: str) -> tuple[bool, str]:
    if not cfg.get("enabled", False):
        return True, "telegram: disabled (skip)"
    token = env_or(cfg, "bot_token", "RE_NEWS_TG_TOKEN")
    chat_id = env_or(cfg, "chat_id", "RE_NEWS_TG_CHATID")
    if not token or not chat_id:
        return False, "telegram: FAILED (bot_token/chat_id 미설정)"
    # 1) 요약 메시지(4096자 제한)
    text = f"📰 일일 부동산·경매 뉴스\n\n{summary}"[:4000]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=30) as resp:
            if not json.loads(resp.read()).get("ok", False):
                return False, "telegram: FAILED (sendMessage ok=false)"
        # 2) 리포트 전문 문서 첨부(있을 때)
        if os.path.exists(report_path):
            doc_ok = _tg_send_document(token, chat_id, report_path, "📄 리포트 전문")
            if not doc_ok:
                return False, "telegram: 요약은 보냄, 문서 전송 실패"
        return True, "telegram: sent (요약 + 리포트 문서)"
    except Exception as e:
        return False, f"telegram: FAILED ({e})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--config", default=str(Path(__file__).parent.parent / "delivery-config.json"))
    args = ap.parse_args()

    report_path = Path(args.report)
    summary_path = Path(args.summary)
    report_md = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    summary = summary_path.read_text(encoding="utf-8").strip() if summary_path.exists() else "요약 없음"

    cfg = load_config(Path(args.config))
    channels = cfg.get("channels", {})
    title = "📰 일일 부동산·경매 투자 브리핑"

    results = []
    # file은 이미 저장된 리포트 경로를 알려주는 것으로 갈음
    results.append((True, f"file: {report_path}"))
    results.append(deliver_notification(channels.get("notification", {"enabled": True}), title, summary))
    results.append(deliver_email(channels.get("email", {}), title, summary, report_md))
    results.append(deliver_telegram(channels.get("telegram", {}), summary, str(report_path)))

    all_ok = True
    for ok, msg in results:
        print(("✅ " if ok else "❌ ") + msg, file=sys.stderr if not ok else sys.stdout)
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
