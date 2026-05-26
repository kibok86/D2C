"""
Desert to Cape — Storage
주간/월간 비교를 위한 히스토리 데이터 저장소.
FX 환율, 운임지수 이력을 JSON 파일로 관리.
"""
import json
from pathlib import Path
from datetime import datetime, UTC, timedelta

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

FX_HISTORY_FILE      = DATA_DIR / "fx_history.json"
FREIGHT_INDEX_FILE   = DATA_DIR / "freight_index_history.json"
FREIGHT_MANUAL_FILE  = DATA_DIR / "freight_rates.json"   # 기존 수동 입력 파일 통합


# ── 공통 유틸 ──────────────────────────────────────────────
def _load(path: Path) -> dict:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _weeks_ago(n: int) -> str:
    return (datetime.now(UTC) - timedelta(weeks=n)).strftime("%Y-%m-%d")


def _months_ago(n: int) -> str:
    return (datetime.now(UTC) - timedelta(days=30 * n)).strftime("%Y-%m-%d")


def _closest_date(history: dict, target_date: str) -> str | None:
    """target_date에 가장 가까운 기존 날짜 키 반환."""
    if not history:
        return None
    dates = sorted(history.keys())
    # target 이전 날짜 중 가장 최근
    before = [d for d in dates if d <= target_date]
    return before[-1] if before else None


# ── FX 히스토리 ────────────────────────────────────────────
def save_fx_snapshot(rates: list[dict]):
    """오늘 날짜로 환율 스냅샷 저장."""
    history = _load(FX_HISTORY_FILE)
    today   = _today()
    history[today] = {r["currency"]: r["usd_rate"] for r in rates}
    _save(FX_HISTORY_FILE, history)
    print(f"  💾 FX 히스토리 저장: {today} ({len(rates)}개 통화)")


def get_fx_changes(rates: list[dict]) -> list[dict]:
    """
    현재 환율에 전주비·전월비 자동 계산 후 반환.
    히스토리 없으면 None 처리.
    """
    history   = _load(FX_HISTORY_FILE)
    week_date = _closest_date(history, _weeks_ago(1))
    month_date = _closest_date(history, _months_ago(1))

    enriched = []
    for r in rates:
        code  = r["currency"]
        curr  = r["usd_rate"]
        item  = dict(r)

        # 전주비
        if week_date and code in history.get(week_date, {}):
            prev_w = history[week_date][code]
            item["week_change_pct"] = round((curr - prev_w) / prev_w * 100, 2)
            item["prev_week_rate"]  = prev_w
        else:
            item["week_change_pct"] = None

        # 전월비
        if month_date and code in history.get(month_date, {}):
            prev_m = history[month_date][code]
            item["month_change_pct"] = round((curr - prev_m) / prev_m * 100, 2)
        else:
            item["month_change_pct"] = None

        enriched.append(item)

    return enriched


# ── 운임지수 히스토리 ────────────────────────────────────────
def save_freight_index(indices: list[dict]):
    """운임지수 스냅샷 저장."""
    history = _load(FREIGHT_INDEX_FILE)
    today   = _today()
    history[today] = {i["name"]: i["value"] for i in indices}
    _save(FREIGHT_INDEX_FILE, history)
    print(f"  💾 운임지수 히스토리 저장: {today} ({len(indices)}개 지수)")


def get_freight_index_history(name: str, weeks: int = 8) -> list[dict]:
    """
    특정 지수의 최근 N주 데이터 반환 (스파크라인용).
    반환: [{"date": "2026-05-18", "value": 3200}, ...]
    """
    history = _load(FREIGHT_INDEX_FILE)
    cutoff  = _weeks_ago(weeks)
    result  = []
    for date in sorted(history.keys()):
        if date >= cutoff and name in history[date]:
            result.append({"date": date, "value": history[date][name]})
    return result


def get_freight_index_change(name: str) -> dict:
    """전주비·전월비 반환."""
    history    = _load(FREIGHT_INDEX_FILE)
    today_data = history.get(_today(), {})
    curr       = today_data.get(name)
    if curr is None:
        return {"current": None, "week_change_pct": None, "month_change_pct": None}

    week_date  = _closest_date({k: v for k, v in history.items() if k < _today()}, _weeks_ago(1))
    month_date = _closest_date({k: v for k, v in history.items() if k < _today()}, _months_ago(1))

    week_pct  = None
    month_pct = None
    if week_date and name in history.get(week_date, {}):
        prev = history[week_date][name]
        week_pct = round((curr - prev) / prev * 100, 2)
    if month_date and name in history.get(month_date, {}):
        prev = history[month_date][name]
        month_pct = round((curr - prev) / prev * 100, 2)

    return {"current": curr, "week_change_pct": week_pct, "month_change_pct": month_pct}
