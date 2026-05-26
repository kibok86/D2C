"""
Desert to Cape — FX Rate Scraper v2
다중 API fallback + 히스토리 기반 전주비/전월비 자동 계산.
"""
import json, requests
from .base import BaseScraper
from .storage import save_fx_snapshot, get_fx_changes

FX_APIS = [
    "https://open.er-api.com/v6/latest/USD",
    "https://api.exchangerate-api.com/v4/latest/USD",
    "https://api.frankfurter.app/latest?from=USD&to=NGN,KES,ZAR,EGP,TRY,IDR,INR,CNY",
    "https://api.fxratesapi.com/latest?base=USD&currencies=NGN,KES,ZAR,EGP,TRY,IDR,INR,CNY",
]

FIXED_PEG = {"SAR", "AED", "BHD", "OMR", "QAR", "KWD", "JOD"}

CURRENCY_META = {
    "NGN": {"name": "나이지리아 나이라", "country": "Nigeria",      "region": "Africa"},
    "KES": {"name": "케냐 실링",        "country": "Kenya",         "region": "Africa"},
    "ZAR": {"name": "남아공 랜드",       "country": "South Africa",  "region": "Africa"},
    "EGP": {"name": "이집트 파운드",     "country": "Egypt",         "region": "Middle East"},
    "TRY": {"name": "터키 리라",         "country": "Turkey",        "region": "Middle East"},
    "IDR": {"name": "인도네시아 루피아", "country": "Indonesia",     "region": "Asia"},
    "INR": {"name": "인도 루피",         "country": "India",         "region": "Asia"},
    "CNY": {"name": "중국 위안",         "country": "China",         "region": "Asia"},
}
TARGET = set(CURRENCY_META.keys())


class FxRateScraper(BaseScraper):
    SOURCE_NAME   = "FX Rates"
    SOURCE_REGION = "MEA"

    def fetch(self) -> list[dict]:
        raw_rates = {}

        for url in FX_APIS:
            try:
                resp = self.get(url)
                data = resp.json()
                raw  = data.get("rates") or data.get("conversion_rates") or {}
                found = {k: float(v) for k, v in raw.items() if k in TARGET}
                if found:
                    raw_rates.update(found)
                    print(f"  -- FX [{url.split('/')[2]}]: {len(found)}개 통화 수집")
                    if len(raw_rates) >= len(TARGET):
                        break
            except Exception as e:
                print(f"  -- FX [{url.split('/')[2]}]: {e}")

        if not raw_rates:
            print("  -- FX: 모든 API 실패")
            return []

        # 기본 항목 구성
        base_rates = []
        for code, rate in raw_rates.items():
            meta = CURRENCY_META.get(code, {})
            base_rates.append({
                "source":     "FX API",
                "region":     meta.get("country", ""),
                "fetched_at": self._fetched_at,
                "currency":   code,
                "name":       meta.get("name", code),
                "usd_rate":   round(rate, 4),
            })

        # 히스토리 저장 -> 전주비/전월비 계산
        save_fx_snapshot(base_rates)
        enriched = get_fx_changes(base_rates)
        return enriched
