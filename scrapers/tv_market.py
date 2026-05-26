"""
Desert to Cape — TV Market Intelligence Scraper
MEA TV 시장 동향 수집.
뉴스: RSS 자동 수집 (Samsung·LG·TCL·Hisense MEA 관련)
시장 데이터: data/tv_market.json 수동 입력 (주간 업데이트)
"""
import json, re, feedparser
from pathlib import Path
from .base import BaseScraper

TV_DATA_FILE = Path(__file__).parent.parent / "data" / "tv_market.json"

# ── RSS 피드 (TV·가전 MEA 뉴스) ──────────────────────────
TV_FEEDS = [
    "https://news.google.com/rss/search?q=Samsung+LG+TV+Middle+East+Africa+2026&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=TCL+Hisense+MEA+television+market+2026&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=OLED+QLED+UHD+TV+Saudi+UAE+Africa&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=consumer+electronics+Middle+East+Africa+market+share&hl=en&gl=US&ceid=US:en",
]

BRAND_KEYWORDS = {
    "Samsung": ["samsung", "삼성"],
    "LG":      ["lg electronics", "lg tv", "lg oled"],
    "TCL":     ["tcl"],
    "Hisense": ["hisense"],
    "Sony":    ["sony"],
}

CATEGORY_KEYWORDS = {
    "OLED":    ["oled"],
    "QLED":    ["qled", "qned", "nanocell"],
    "MiniLED": ["mini led", "mini-led", "miniled"],
    "UHD":     ["uhd", "4k", "crystal uhd"],
    "FHD":     ["full hd", "fhd", "1080p"],
}

# ── 기본 템플릿 ──────────────────────────────────────────
DEFAULT_TV_DATA = {
    "_instructions": (
        "brands: 브랜드별 시장 현황 | "
        "market_share_pct: 추정 점유율 | "
        "trend: up/flat/down | "
        "price_index: 100=기준가(LG OLED 65인치) 대비 상대 지수 | "
        "regions: 주요 활동 지역"
    ),
    "updated_at": "",
    "source_note": "GfK MEA / 현지 유통 파트너 / 업계 리포트 기반",
    "period": "",
    "brands": [
        {
            "brand": "Samsung", "segment": "Premium",
            "hero_model": "OLED S95D", "hero_category": "OLED",
            "market_share_pct": None, "trend": "up",
            "price_index": 113,
            "regions": ["Saudi Arabia", "UAE", "Nigeria"],
            "note": "",
        },
        {
            "brand": "LG", "segment": "Premium",
            "hero_model": "OLED C4", "hero_category": "OLED",
            "market_share_pct": None, "trend": "flat",
            "price_index": 100,
            "regions": ["Saudi Arabia", "UAE", "Kenya"],
            "note": "",
        },
        {
            "brand": "TCL", "segment": "Mid-Value",
            "hero_model": "QLED C645", "hero_category": "QLED",
            "market_share_pct": None, "trend": "up",
            "price_index": 42,
            "regions": ["Nigeria", "Kenya", "South Africa"],
            "note": "서아프리카 공식 유통망 확장 중",
        },
        {
            "brand": "Hisense", "segment": "Value",
            "hero_model": "ULED U7K", "hero_category": "MiniLED",
            "market_share_pct": None, "trend": "up",
            "price_index": 48,
            "regions": ["Kenya", "South Africa", "Egypt"],
            "note": "동아프리카 점유율 빠르게 확대",
        },
        {
            "brand": "Sony", "segment": "Ultra Premium",
            "hero_model": "Bravia 9", "hero_category": "MiniLED",
            "market_share_pct": None, "trend": "flat",
            "price_index": 145,
            "regions": ["UAE", "Saudi Arabia"],
            "note": "",
        },
    ],
    "category_trends": [
        {"category": "OLED",    "trend": "up",   "note": "프리미엄 수요 견조, 삼성·LG 경쟁 심화"},
        {"category": "QLED",    "trend": "up",   "note": "중동 중가 시장 주력 카테고리"},
        {"category": "MiniLED", "trend": "up",   "note": "Hisense·TCL 공격적 진입"},
        {"category": "UHD",     "trend": "flat", "note": "보급형 수요 안정적, 가격 압박 지속"},
        {"category": "FHD",     "trend": "down", "note": "UHD 전환 가속화로 수요 감소"},
    ],
    "regional_highlights": [
        {
            "region": "Saudi Arabia",
            "key_metric": "Vision 2030 소비재 내수 확대 정책으로 프리미엄 TV 수요 증가",
            "risk": "관세 변경 모니터링 필요",
        },
        {
            "region": "UAE",
            "key_metric": "두바이 쇼핑 시즌 앞두고 프로모션 경쟁 심화",
            "risk": "",
        },
        {
            "region": "Nigeria",
            "key_metric": "나이라 약세로 수입가 압박, TCL·Hisense 가성비 모델 수혜",
            "risk": "환율 변동성 지속 주의",
        },
        {
            "region": "Kenya",
            "key_metric": "몸바사 항만 확장 완공 후 물류비 절감 → 현지가 하락 기대",
            "risk": "",
        },
    ],
}


class TVMarketScraper(BaseScraper):
    SOURCE_NAME   = "TV Market"
    SOURCE_REGION = "MEA"

    # ── 뉴스 수집 ────────────────────────────────────────
    def _fetch_news(self) -> list[dict]:
        items, seen = [], set()
        for url in TV_FEEDS:
            try:
                feed = feedparser.parse(url)
                for e in feed.entries[:5]:
                    title = re.sub(r"\s+", " ", e.get("title","")).strip()
                    if len(title) < 20 or title in seen:
                        continue
                    seen.add(title)

                    # 브랜드 태깅
                    brands = [b for b, kws in BRAND_KEYWORDS.items()
                              if any(kw in title.lower() for kw in kws)]
                    categories = [c for c, kws in CATEGORY_KEYWORDS.items()
                                  if any(kw in title.lower() for kw in kws)]
                    items.append({
                        "type":       "news",
                        "source":     feed.feed.get("title", "Google News"),
                        "region":     "MEA",
                        "fetched_at": self._fetched_at,
                        "title":      title,
                        "title_ko":   "",     # AI 번역 후 채움
                        "url":        e.get("link",""),
                        "published":  e.get("published","")[:10],
                        "brands":     brands,
                        "categories": categories,
                    })
            except Exception as ex:
                print(f"  -- TV RSS 실패: {ex}")
        print(f"  -- TV 뉴스: {len(items)}건")
        return items[:12]

    # ── 수동 데이터 로드 ────────────────────────────────
    def _load_manual(self) -> dict:
        if not TV_DATA_FILE.exists():
            TV_DATA_FILE.parent.mkdir(exist_ok=True)
            template = dict(DEFAULT_TV_DATA)
            template["updated_at"] = self._fetched_at[:10]
            with open(TV_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
            print(f"  -- tv_market.json 템플릿 생성됨 → {TV_DATA_FILE}")
        with open(TV_DATA_FILE, encoding="utf-8") as f:
            return json.load(f)

    def fetch(self) -> list[dict]:
        news   = self._fetch_news()
        manual = self._load_manual()

        # 브랜드 데이터
        brands = []
        for b in manual.get("brands", []):
            brands.append({
                "type":       "brand",
                "source":     "tv_market.json",
                "region":     "MEA",
                "fetched_at": self._fetched_at,
                **b,
            })

        # 카테고리 트렌드
        cats = []
        for c in manual.get("category_trends", []):
            cats.append({
                "type":       "category",
                "source":     "tv_market.json",
                "region":     "MEA",
                "fetched_at": self._fetched_at,
                **c,
            })

        # 지역 하이라이트
        regions = []
        for r in manual.get("regional_highlights", []):
            regions.append({
                "type":       "region",
                "source":     "tv_market.json",
                "region":     r.get("region",""),
                "fetched_at": self._fetched_at,
                **r,
            })

        all_items = brands + cats + regions + news
        print(f"  -- TV Market: 브랜드 {len(brands)}개 · 카테고리 {len(cats)}개 · 뉴스 {len(news)}건")

        # 메타 정보 반환용으로 저장
        self._meta = {
            "source_note":         manual.get("source_note",""),
            "period":              manual.get("period",""),
            "updated_at":          manual.get("updated_at",""),
            "regional_highlights": manual.get("regional_highlights",[]),
            "category_trends":     manual.get("category_trends",[]),
        }
        return all_items
