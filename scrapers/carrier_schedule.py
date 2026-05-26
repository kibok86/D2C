"""
Desert to Cape — Carrier Schedule Scraper
선사별 MEA 서비스 스케줄 변경·GRI 공지 수집.
선사 사이트 직접 파싱 시도 + carrier_schedule.json fallback.
"""
import json, re, feedparser
from pathlib import Path
from .base import BaseScraper

SCHEDULE_FILE = Path(__file__).parent.parent / "data" / "carrier_schedule.json"

CARRIERS = {
    "MSC":      {"ko": "MSC",      "color": "#FF6B35"},
    "COSCO":    {"ko": "COSCO",    "color": "#E63946"},
    "HMM":      {"ko": "HMM",      "color": "#2196F3"},
    "Evergreen":{"ko": "에버그린",  "color": "#4CAF50"},
    "CMA CGM":  {"ko": "CMA CGM",  "color": "#9C27B0"},
    "ONE":      {"ko": "ONE",      "color": "#FF9800"},
}

DEFAULT_SCHEDULES = [
    {
        "carrier": "MSC", "service": "MUSTANG",
        "route_ko": "아시아 → 걸프 (UAE·사우디)",
        "frequency": "주 1회", "capacity_pct": 91,
        "change_type": "GRI",
        "change_detail": "7월 1일 $350/TEU GRI 적용 예정",
        "effective_date": "2026-07-01", "status": "예정",
    },
    {
        "carrier": "COSCO", "service": "MEX",
        "route_ko": "아시아 → 중동·동아프리카",
        "frequency": "주 1회", "capacity_pct": 88,
        "change_type": "우회",
        "change_detail": "홍해 우회 → 케이프타운 경유 유지 (3Q까지)",
        "effective_date": "2026-06-01", "status": "진행중",
    },
    {
        "carrier": "HMM", "service": "GAX",
        "route_ko": "부산·중국 → 걸프 (오만·UAE·사우디)",
        "frequency": "주 1회", "capacity_pct": 85,
        "change_type": "스케줄",
        "change_detail": "부산 ETD 매주 화요일 → 목요일로 변경",
        "effective_date": "2026-06-15", "status": "예정",
    },
    {
        "carrier": "Evergreen", "service": "AEX",
        "route_ko": "아시아 → 이집트·지중해",
        "frequency": "주 2회", "capacity_pct": 72,
        "change_type": "정상",
        "change_detail": "수에즈 운하 직항 유지, 스케줄 변동 없음",
        "effective_date": "", "status": "정상",
    },
    {
        "carrier": "CMA CGM", "service": "AFRICA EXPRESS",
        "route_ko": "아시아 → 서아프리카 (나이지리아·가나)",
        "frequency": "격주", "capacity_pct": 78,
        "change_type": "스케줄",
        "change_detail": "라고스 입항 빈도 격주 → 주 1회로 증편 (7월)",
        "effective_date": "2026-07-01", "status": "예정",
    },
    {
        "carrier": "ONE", "service": "IEX",
        "route_ko": "아시아 → 인도·중동·동아프리카",
        "frequency": "주 1회", "capacity_pct": 80,
        "change_type": "정상",
        "change_detail": "스케줄 정상 운영",
        "effective_date": "", "status": "정상",
    },
]

CHANGE_TYPE_STYLE = {
    "GRI":    ("📢", "#C0392B", "#FFEBEE"),
    "우회":   ("🔄", "#E67E22", "#FFF3E0"),
    "스케줄": ("📅", "#1565C0", "#E3F2FD"),
    "정상":   ("✅", "#2E7D32", "#E8F5E9"),
    "증편":   ("➕", "#6A1B9A", "#F3E5F5"),
}

STATUS_STYLE = {
    "예정":   "#E67E22",
    "진행중": "#C0392B",
    "정상":   "#2E7D32",
}


class CarrierScheduleScraper(BaseScraper):
    SOURCE_NAME   = "Carrier Schedule"
    SOURCE_REGION = "MEA"

    def _try_rss(self) -> list[dict]:
        """선사 GRI·스케줄 관련 뉴스 RSS에서 변경사항 추출."""
        results = []
        feeds = [
            "https://news.google.com/rss/search?q=MSC+COSCO+HMM+Evergreen+GRI+schedule+MEA+2026&hl=en",
            "https://news.google.com/rss/search?q=container+shipping+schedule+change+Gulf+Africa&hl=en",
        ]
        for url in feeds:
            try:
                feed = feedparser.parse(url)
                for e in feed.entries[:3]:
                    title = e.get("title", "")
                    # 선사 이름 + 변경 키워드 필터
                    carriers_in_title = [c for c in CARRIERS if c.lower() in title.lower()]
                    if carriers_in_title and any(
                        kw in title.lower() for kw in
                        ["gri", "schedule", "route", "service", "change", "suspend"]
                    ):
                        results.append({"carrier": carriers_in_title[0], "news": title})
            except Exception:
                pass
        return results

    def _load_manual(self) -> list[dict]:
        if not SCHEDULE_FILE.exists():
            SCHEDULE_FILE.parent.mkdir(exist_ok=True)
            with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "_instructions": (
                        "change_type: GRI/우회/스케줄/정상/증편 | "
                        "capacity_pct: 선복률(0-100) | "
                        "effective_date: YYYY-MM-DD"
                    ),
                    "updated_at": self._fetched_at,
                    "schedules": DEFAULT_SCHEDULES,
                }, f, ensure_ascii=False, indent=2)
            print("  -- carrier_schedule.json 템플릿 생성됨")

        with open(SCHEDULE_FILE, encoding="utf-8") as f:
            return json.load(f).get("schedules", DEFAULT_SCHEDULES)

    def fetch(self) -> list[dict]:
        news_hits = self._try_rss()
        schedules = self._load_manual()
        result = []
        for s in schedules:
            carrier = s.get("carrier", "")
            ctype   = s.get("change_type", "정상")
            icon, txt_color, bg_color = CHANGE_TYPE_STYLE.get(ctype, ("📌", "#666", "#F5F5F5"))
            carrier_meta = CARRIERS.get(carrier, {})
            result.append({
                "source":         self.SOURCE_NAME,
                "region":         "MEA",
                "fetched_at":     self._fetched_at,
                "carrier":        carrier,
                "carrier_color":  carrier_meta.get("color", "#666"),
                "service":        s.get("service", ""),
                "route_ko":       s.get("route_ko", ""),
                "frequency":      s.get("frequency", ""),
                "capacity_pct":   s.get("capacity_pct", 0),
                "change_type":    ctype,
                "change_icon":    icon,
                "change_color":   txt_color,
                "change_bg":      bg_color,
                "change_detail":  s.get("change_detail", ""),
                "effective_date": s.get("effective_date", ""),
                "status":         s.get("status", "정상"),
                "status_color":   STATUS_STYLE.get(s.get("status", "정상"), "#666"),
                "has_news":       any(n["carrier"] == carrier for n in news_hits),
            })
        print(f"  -- Carrier Schedule: {len(result)}개 선사 / 뉴스 매칭 {len(news_hits)}건")
        return result
