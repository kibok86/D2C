"""
Desert to Cape — Freight Rate Loader
운임 데이터는 freight_rates.json 파일을 직접 업데이트.
→ 파일이 없으면 자동으로 템플릿 생성.
→ 이전 주 값이 기본값으로 채워져 있어 변경된 것만 수정하면 됩니다.
"""
import json
from pathlib import Path
from datetime import datetime, UTC

FREIGHT_FILE = Path(__file__).parent.parent / "freight_rates.json"

# 기본 템플릿 (처음 실행 시 생성)
DEFAULT_ROUTES = [
    # 부산
    {"origin":"부산","dest":"두바이 (UAE)",        "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"부산","dest":"담맘 (Saudi Arabia)",  "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"부산","dest":"도하 (Qatar)",         "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"부산","dest":"무스카트 (Oman)",      "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"부산","dest":"몸바사 (Kenya)",       "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"부산","dest":"더반 (South Africa)",  "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"부산","dest":"라고스 (Nigeria)",     "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    # 중국
    {"origin":"중국","dest":"두바이 (UAE)",         "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"중국","dest":"담맘 (Saudi Arabia)",  "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"중국","dest":"몸바사 (Kenya)",       "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"중국","dest":"더반 (South Africa)",  "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    # 인도네시아
    {"origin":"인도네시아","dest":"두바이 (UAE)",        "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"인도네시아","dest":"담맘 (Saudi Arabia)",  "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"인도네시아","dest":"더반 (South Africa)",  "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    # 이집트
    {"origin":"이집트","dest":"두바이 (UAE)",        "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"이집트","dest":"담맘 (Saudi Arabia)",  "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"이집트","dest":"몸바사 (Kenya)",       "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
    {"origin":"이집트","dest":"더반 (South Africa)",  "fak_usd":None,"prev_usd":None,"transit_days":None,"status":"","via":"","note":""},
]


def load_freight_rates() -> dict:
    """freight_rates.json 로드. 없으면 템플릿 생성 후 반환."""
    if not FREIGHT_FILE.exists():
        _create_template()

    with open(FREIGHT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    routes = data.get("routes", [])
    verified = [r for r in routes if r.get("fak_usd") is not None]
    print(f"  ✓ 운임: {len(verified)}/{len(routes)}개 루트 입력됨")

    return {
        "source":     "freight_rates.json",
        "region":     "MEA",
        "fetched_at": data.get("updated_at", ""),
        "status":     "ok" if verified else "empty",
        "count":      len(verified),
        "data":       routes,
        "gri_notice": data.get("gri_notice", ""),
        "source_note": data.get("source_note", ""),
    }


def _create_template():
    template = {
        "_instructions": (
            "fak_usd: 이번 주 FAK 운임 ($/TEU) | "
            "prev_usd: 지난 주 운임 | "
            "note: 특이사항 (선택)"
        ),
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_note": "Freightos / 선사 공지 기준",
        "gri_notice": "",
        "routes": DEFAULT_ROUTES,
    }
    FREIGHT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FREIGHT_FILE, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    print(f"  📝 freight_rates.json 템플릿 생성됨 → {FREIGHT_FILE}")
    print("     ↳ 운임 입력 후 다시 실행해주세요.")
