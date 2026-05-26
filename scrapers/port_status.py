"""
Desert to Cape — Port Status Scraper
주요 항만 혼잡도·체선시간·처리현황 수집.
자동수집 실패 시 port_status.json 수동 업데이트로 fallback.
"""
import json, re, requests
from pathlib import Path
from bs4 import BeautifulSoup
from .base import BaseScraper

STATUS_FILE = Path(__file__).parent.parent / "data" / "port_status.json"

PORT_META = {
    "Busan":    {"ko": "부산", "country": "Korea",        "region": "Origin"},
    "Dubai":    {"ko": "두바이 (제벨알리)", "country": "UAE", "region": "Gulf"},
    "Dammam":   {"ko": "담맘 (킹압둘라)", "country": "Saudi Arabia", "region": "Gulf"},
    "Mombasa":  {"ko": "몸바사", "country": "Kenya",       "region": "East Africa"},
    "Durban":   {"ko": "더반", "country": "South Africa", "region": "South Africa"},
    "Lagos":    {"ko": "라고스 (아파파)", "country": "Nigeria", "region": "West Africa"},
    "PortSaid": {"ko": "포트사이드", "country": "Egypt",   "region": "Med/Transit"},
    "Shanghai": {"ko": "상하이", "country": "China",       "region": "Origin"},
}

DEFAULT_STATUS = [
    {"port": "Busan",    "congestion_pct": 42, "wait_days": 0.8, "status": "정상", "note": ""},
    {"port": "Shanghai", "congestion_pct": 58, "wait_days": 1.2, "status": "정상", "note": ""},
    {"port": "Dubai",    "congestion_pct": 71, "wait_days": 2.1, "status": "주의", "note": "GRI 전 선적 집중"},
    {"port": "Dammam",   "congestion_pct": 65, "wait_days": 1.8, "status": "주의", "note": ""},
    {"port": "PortSaid", "congestion_pct": 48, "wait_days": 1.0, "status": "정상", "note": "수에즈 직항 유지"},
    {"port": "Mombasa",  "congestion_pct": 55, "wait_days": 1.5, "status": "정상", "note": "항만 확장 완공 임박"},
    {"port": "Durban",   "congestion_pct": 38, "wait_days": 0.7, "status": "정상", "note": "혼잡 해소 완료"},
    {"port": "Lagos",    "congestion_pct": 82, "wait_days": 3.4, "status": "혼잡", "note": "나이라 약세로 수입 집중"},
]

STATUS_COLOR = {
    "정상": "#2E7D32", "주의": "#E67E22",
    "혼잡": "#C0392B", "중단": "#C0392B",
}


class PortStatusScraper(BaseScraper):
    SOURCE_NAME   = "Port Status"
    SOURCE_REGION = "MEA"

    SOURCES = [
        ("PortCalls",   "https://www.portcalls.com/port-congestion/"),
        ("MarineTraffic", "https://www.marinetraffic.com/en/ais/home/centerx:0/centery:20/zoom:3"),
        ("VesselFinder", "https://www.vesselfinder.com/ports"),
    ]

    def _try_auto(self) -> list[dict]:
        """공개 소스에서 항만 혼잡 데이터 추출 시도."""
        for name, url in self.SOURCES:
            try:
                resp = self.get(url)
                soup = BeautifulSoup(resp.text, "lxml")
                text = soup.get_text()
                items = []
                for port in PORT_META:
                    # 항만명 주변 혼잡/지연 키워드 + 숫자 추출
                    pat = rf"{port}[^.]*?(\d+(?:\.\d+)?)\s*(?:day|hour|%)"
                    m = re.search(pat, text, re.I)
                    if m:
                        items.append({"port": port, "raw": m.group(0)[:80]})
                if items:
                    print(f"  -- Port [{name}]: {len(items)}개 부분 파싱")
                    break
            except Exception as e:
                print(f"  -- Port [{name}]: {e}")
        return []

    def _load_manual(self) -> list[dict]:
        """data/port_status.json 로드, 없으면 기본값으로 생성."""
        if not STATUS_FILE.exists():
            STATUS_FILE.parent.mkdir(exist_ok=True)
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "_instructions": (
                        "congestion_pct: 혼잡도(0~100) | "
                        "wait_days: 평균 체선일 | "
                        "status: 정상/주의/혼잡/중단 | note: 특이사항"
                    ),
                    "updated_at": self._fetched_at,
                    "ports": DEFAULT_STATUS,
                }, f, ensure_ascii=False, indent=2)
            print(f"  -- port_status.json 템플릿 생성됨")

        with open(STATUS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("ports", DEFAULT_STATUS)

    def fetch(self) -> list[dict]:
        # 자동수집 우선 시도
        auto = self._try_auto()

        # 수동 데이터 로드 (자동 실패 시 대체)
        ports = self._load_manual()
        result = []
        for p in ports:
            meta = PORT_META.get(p["port"], {})
            result.append({
                "source":         self.SOURCE_NAME,
                "region":         meta.get("region", ""),
                "fetched_at":     self._fetched_at,
                "port":           p["port"],
                "port_ko":        meta.get("ko", p["port"]),
                "country":        meta.get("country", ""),
                "congestion_pct": p.get("congestion_pct", 0),
                "wait_days":      p.get("wait_days", 0),
                "status":         p.get("status", "정상"),
                "status_color":   STATUS_COLOR.get(p.get("status", "정상"), "#666"),
                "note":           p.get("note", ""),
                "auto_sourced":   bool(auto),
            })
        print(f"  -- Port Status: {len(result)}개 항만 ({('자동' if auto else '수동')} 기반)")
        return result
