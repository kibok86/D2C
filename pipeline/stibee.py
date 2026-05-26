"""
Desert to Cape — Resend API 연동
뉴스레터 이메일 발송 (Resend 무료: 3,000건/월)

환경변수:
  RESEND_API_KEY  - Resend API 키 (re_...)
  RESEND_FROM     - 발신자 (예: Desert to Cape <news@yourdomain.com>)
  RESEND_TO       - 수신자 이메일, 콤마 구분 (테스트: 본인 이메일 1개)
"""
import os, requests
from pathlib import Path

RESEND_API = "https://api.resend.com/emails"


def _api_key() -> str:
    key = os.environ.get("RESEND_API_KEY", "")
    if not key:
        raise RuntimeError(
            "RESEND_API_KEY 환경변수 미설정\n"
            "resend.com > API Keys에서 발급 후:\n"
            "export RESEND_API_KEY=re_..."
        )
    return key


def send_newsletter(html_path: Path, issue_num: int) -> dict:
    """생성된 HTML 파일을 Resend로 발송."""
    api_key    = _api_key()
    from_addr  = os.environ.get("RESEND_FROM", "Desert to Cape <onboarding@resend.dev>")
    to_raw     = os.environ.get("RESEND_TO", "")

    if not to_raw:
        print("  -- RESEND_TO 미설정 → 발송 스킵")
        return {"skipped": True}

    to_list = [e.strip() for e in to_raw.split(",") if e.strip()]
    subject = f"[Desert to Cape #{issue_num:03d}] MEA 물류·무역 주간 브리핑"
    html    = html_path.read_text(encoding="utf-8")

    resp = requests.post(
        RESEND_API,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        json={
            "from":    from_addr,
            "to":      to_list,
            "subject": subject,
            "html":    html,
        },
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    print(f"  ✓ 발송 완료: {len(to_list)}명 / id={result.get('id','')}")
    return result


def publish_issue(html_path: Path, issue_num: int) -> dict:
    """publish.py에서 호출하는 메인 발행 함수."""
    try:
        return send_newsletter(html_path, issue_num)
    except Exception as e:
        print(f"  ✗ 발송 실패: {e}")
        return {"error": str(e)}
