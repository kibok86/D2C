"""
Desert to Cape — 구독 관리 시스템
무료/유료 구독자 티어 관리, 결제 상태 추적, 업그레이드 플로우.
로컬 JSON 기반 (추후 DB 마이그레이션 용이하도록 설계).
"""
import json, hashlib
from pathlib import Path
from datetime import datetime, UTC, timedelta

SUB_FILE = Path(__file__).parent.parent / "data" / "subscribers.json"


# ── 구독자 스키마 ──────────────────────────────────────────
def _new_subscriber(email: str, name: str = "", tier: str = "free") -> dict:
    return {
        "id":           hashlib.md5(email.lower().encode()).hexdigest()[:12],
        "email":        email.lower().strip(),
        "name":         name,
        "tier":         tier,          # "free" | "pro"
        "status":       "active",      # "active" | "unsubscribed" | "paused"
        "joined_at":    datetime.now(UTC).isoformat(),
        "upgraded_at":  None,
        "paid_until":   None,          # ISO date, pro 구독자만
        "open_count":   0,
        "click_count":  0,
        "last_opened":  None,
        "source":       "web",         # "web" | "linkedin" | "dm" | "referral"
        "notes":        "",
    }


# ── CRUD ─────────────────────────────────────────────────
def _load() -> dict:
    if SUB_FILE.exists():
        with open(SUB_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"subscribers": [], "updated_at": ""}


def _save(data: dict):
    SUB_FILE.parent.mkdir(exist_ok=True)
    data["updated_at"] = datetime.now(UTC).isoformat()
    with open(SUB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add(email: str, name: str = "", tier: str = "free", source: str = "web") -> dict:
    data  = _load()
    subs  = data["subscribers"]
    existing = next((s for s in subs if s["email"] == email.lower().strip()), None)
    if existing:
        print(f"  이미 등록됨: {email} ({existing['tier']})")
        return existing
    new_sub = _new_subscriber(email, name, tier)
    new_sub["source"] = source
    subs.append(new_sub)
    _save(data)
    print(f"  ✓ 구독자 추가: {email} / {tier}")
    return new_sub


def upgrade_to_pro(email: str, months: int = 1) -> dict:
    """무료 → 프로 업그레이드. paid_until 자동 설정."""
    data  = _load()
    sub   = next((s for s in data["subscribers"] if s["email"] == email.lower().strip()), None)
    if not sub:
        raise ValueError(f"{email} 구독자를 찾을 수 없습니다.")
    sub["tier"]        = "pro"
    sub["status"]      = "active"
    sub["upgraded_at"] = datetime.now(UTC).isoformat()
    sub["paid_until"]  = (datetime.now(UTC) + timedelta(days=30 * months)).strftime("%Y-%m-%d")
    _save(data)
    print(f"  ✓ 프로 업그레이드: {email} (until {sub['paid_until']})")
    return sub


def unsubscribe(email: str) -> bool:
    data = _load()
    sub  = next((s for s in data["subscribers"] if s["email"] == email.lower().strip()), None)
    if not sub:
        return False
    sub["status"] = "unsubscribed"
    _save(data)
    return True


# ── 통계·리포트 ───────────────────────────────────────────
def get_stats() -> dict:
    data = _load()
    subs = data["subscribers"]
    active = [s for s in subs if s["status"] == "active"]
    free   = [s for s in active if s["tier"] == "free"]
    pro    = [s for s in active if s["tier"] == "pro"]

    # 만료된 pro 체크
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    expired = [s for s in pro if s.get("paid_until","") < today]

    mrr = len(pro) * 9900  # 월 수익 (원)

    return {
        "total":          len(active),
        "free":           len(free),
        "pro":            len(pro),
        "pro_expired":    len(expired),
        "conversion_pct": round(len(pro) / len(active) * 100, 1) if active else 0,
        "mrr_krw":        mrr,
        "mrr_display":    f"₩{mrr:,}",
        "updated_at":     data.get("updated_at",""),
    }


def print_dashboard():
    s = get_stats()
    print("\n" + "═" * 40)
    print("  Desert to Cape — 구독 현황")
    print("═" * 40)
    print(f"  전체 활성 구독자   {s['total']:>6}명")
    print(f"  무료              {s['free']:>6}명")
    print(f"  프로 (유료)       {s['pro']:>6}명")
    print(f"  전환율            {s['conversion_pct']:>5.1f}%")
    print(f"  이번 달 수익      {s['mrr_display']:>10}")
    if s['pro_expired']:
        print(f"  ⚠ 만료 예정       {s['pro_expired']:>6}명")
    print("═" * 40)


# ── 업그레이드 대상 추천 ───────────────────────────────────
def upgrade_candidates(min_opens: int = 5) -> list[dict]:
    """
    오픈 횟수 min_opens 이상인 무료 구독자 → 유료 전환 DM 대상.
    """
    data = _load()
    candidates = [
        s for s in data["subscribers"]
        if s["status"] == "active"
        and s["tier"] == "free"
        and s.get("open_count", 0) >= min_opens
    ]
    candidates.sort(key=lambda x: x.get("open_count", 0), reverse=True)
    return candidates
