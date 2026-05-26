"""
Desert to Cape — 스티비 API 연동
구독자 관리, 뉴스레터 발송, 유료/무료 티어 분기.

스티비 API 문서: https://api.stibee.com/docs
환경변수: STIBEE_API_KEY, STIBEE_LIST_ID_FREE, STIBEE_LIST_ID_PAID
"""
import os, json, requests
from datetime import datetime, UTC
from pathlib import Path

STIBEE_BASE   = "https://api.stibee.com/v1"
HEADERS_BASE  = {"Content-Type": "application/json"}

# 구독자 티어 정의
TIERS = {
    "free": {
        "label":    "무료 구독자",
        "sections": ["00","01","02","03","04","05","06"],  # 전체 섹션
        "price":    0,
    },
    "pro": {
        "label":    "프로 구독자",
        "sections": ["00","01","02","03","04","05","06"],  # 동일 + 데이터 파일 첨부
        "price":    9900,   # 월 9,900원
        "perks":    ["weekly_data_xlsx", "priority_qa"],
    },
}


def _api_key() -> str:
    key = os.environ.get("STIBEE_API_KEY", "")
    if not key:
        raise RuntimeError(
            "STIBEE_API_KEY 환경변수 미설정\n"
            "스티비 계정 > 설정 > API에서 발급 후:\n"
            "export STIBEE_API_KEY=your_key"
        )
    return key

def _list_id(tier: str) -> str:
    env_key = f"STIBEE_LIST_ID_{tier.upper()}"
    lid = os.environ.get(env_key, "")
    if not lid:
        raise RuntimeError(f"{env_key} 환경변수 미설정")
    return lid


# ── 구독자 추가 ─────────────────────────────────────────────
def add_subscriber(email: str, name: str = "", tier: str = "free") -> dict:
    """
    스티비 주소록에 구독자 추가.
    tier: "free" | "pro"
    """
    url = f"{STIBEE_BASE}/lists/{_list_id(tier)}/subscribers"
    payload = {
        "subscribers": [{
            "email":  email,
            "name":   name,
            "fields": {"tier": tier, "joined_at": datetime.now(UTC).isoformat()},
        }],
        "mode": "SUB",          # SUB = 중복 시 업데이트
    }
    resp = requests.post(
        url,
        headers={**HEADERS_BASE, "AccessToken": _api_key()},
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()
    print(f"  ✓ 구독자 추가: {email} ({tier})")
    return result


# ── 구독자 목록 조회 ───────────────────────────────────────
def list_subscribers(tier: str = "free", limit: int = 50) -> list[dict]:
    url = f"{STIBEE_BASE}/lists/{_list_id(tier)}/subscribers"
    resp = requests.get(
        url,
        headers={**HEADERS_BASE, "AccessToken": _api_key()},
        params={"pageSize": limit},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    subs = data.get("subscribers", [])
    print(f"  ✓ {tier} 구독자 {len(subs)}명 조회")
    return subs


# ── 뉴스레터 발송 ──────────────────────────────────────────
def send_newsletter(
    html_path: Path,
    subject: str,
    tier: str = "free",
    preview_text: str = "",
) -> dict:
    """
    생성된 HTML 파일을 스티비 API로 발송.
    tier별 주소록에 각각 발송.
    """
    html_content = html_path.read_text(encoding="utf-8")

    url = f"{STIBEE_BASE}/emails"
    payload = {
        "name":         subject,
        "subject":      subject,
        "fromName":     "Desert to Cape",
        "fromEmail":    os.environ.get("DTC_FROM_EMAIL", "newsletter@desertocape.com"),
        "previewText":  preview_text or subject,
        "contentType":  "html",
        "content":      html_content,
        "listIds":      [_list_id(tier)],
    }
    resp = requests.post(
        url,
        headers={**HEADERS_BASE, "AccessToken": _api_key()},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    email_id = result.get("id", "")
    print(f"  ✓ 뉴스레터 등록: id={email_id} / tier={tier}")

    # 즉시 발송
    send_resp = requests.post(
        f"{STIBEE_BASE}/emails/{email_id}/send",
        headers={**HEADERS_BASE, "AccessToken": _api_key()},
        timeout=15,
    )
    send_resp.raise_for_status()
    print(f"  ✓ 발송 완료: {tier} 구독자")
    return result


# ── 통계 조회 ──────────────────────────────────────────────
def get_stats(email_id: str) -> dict:
    """발송된 뉴스레터 오픈율·클릭률 조회."""
    resp = requests.get(
        f"{STIBEE_BASE}/emails/{email_id}/stats",
        headers={**HEADERS_BASE, "AccessToken": _api_key()},
        timeout=15,
    )
    resp.raise_for_status()
    stats = resp.json()
    print(f"  오픈율: {stats.get('openRate','?')}% | 클릭율: {stats.get('clickRate','?')}%")
    return stats


# ── 전체 발행 플로우 ───────────────────────────────────────
def publish_issue(html_path: Path, issue_num: int) -> dict:
    """
    뉴스레터 HTML → 스티비 발송 전체 플로우.
    무료/유료 구독자 동시 발송.
    """
    subject      = f"[Desert to Cape #{issue_num:03d}] MEA 물류·무역 주간 브리핑"
    preview_text = "이번 주 아시아-걸프 운임, 항만 현황, 지정학 리스크 정리"

    results = {}
    for tier in ["free", "pro"]:
        try:
            results[tier] = send_newsletter(html_path, subject, tier, preview_text)
        except Exception as e:
            print(f"  ✗ {tier} 발송 실패: {e}")
            results[tier] = {"error": str(e)}

    return results
