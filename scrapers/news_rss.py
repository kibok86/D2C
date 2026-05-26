"""
Desert to Cape — News RSS Scraper v2
뉴스 수집 + Claude API 배치 번역 통합.
단일 API 호출로 전체 헤드라인 일괄 번역 -> 비용/속도 최적화.
캐시 시스템으로 재실행 시 중복 번역 없음.
"""
import re, json, os, hashlib, feedparser, requests
from pathlib import Path
from .base import BaseScraper

FEEDS = {
    "Middle East": [
        "https://news.google.com/rss/search?q=middle+east+shipping+freight+logistics&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=gulf+freight+rates+GRI+shipping&hl=en&gl=US&ceid=US:en",
        "https://www.arabnews.com/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "Africa": [
        "https://news.google.com/rss/search?q=africa+shipping+logistics+port&hl=en&gl=US&ceid=US:en",
        "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
        "https://news.google.com/rss/search?q=west+east+africa+trade+supply+chain&hl=en&gl=US&ceid=US:en",
    ],
    "Shipping": [
        "https://news.google.com/rss/search?q=container+freight+red+sea+houthi+2026&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=MSC+Evergreen+HMM+shipping+schedule+GRI&hl=en&gl=US&ceid=US:en",
    ],
}

SKIP_WORDS     = {"sponsored", "advertisement", "buy now", "deal alert", "sign up"}
MIN_TITLE_LEN  = 25
MAX_PER_REGION = 5
CACHE_FILE     = Path(__file__).parent.parent / "data" / "translation_cache.json"


class NewsScraper(BaseScraper):
    SOURCE_NAME   = "RSS News"
    SOURCE_REGION = "MEA"

    def __init__(self, delay=1.0, translate=True):
        super().__init__(delay)
        self.translate = translate
        self._cache    = self._load_cache()

    def _load_cache(self) -> dict:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        CACHE_FILE.parent.mkdir(exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def _cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()[:12]

    def _clean(self, text: str) -> str:
        return re.sub(r"\s+", " ", re.sub("<[^>]+>", "", text)).strip()

    def _parse_feed(self, region: str, url: str) -> list[dict]:
        feed  = feedparser.parse(url)
        items = []
        seen  = set()
        for e in feed.entries:
            title = self._clean(e.get("title", ""))
            if len(title) < MIN_TITLE_LEN:
                continue
            if any(w in title.lower() for w in SKIP_WORDS):
                continue
            if title in seen:
                continue
            seen.add(title)
            items.append({
                "source":     feed.feed.get("title", url.split("/")[2]),
                "region":     region,
                "fetched_at": self._fetched_at,
                "title":      title,
                "title_ko":   "",
                "summary":    self._clean(e.get("summary", ""))[:300],
                "url":        e.get("link", ""),
                "published":  e.get("published", "")[:10],
            })
        return items

    def _batch_translate(self, items: list[dict]) -> list[dict]:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            print("  -- 번역 스킵 (GEMINI_API_KEY 미설정)")
            return items

        # 캐시 적용
        to_translate = []
        for item in items:
            key = self._cache_key(item["title"])
            if key in self._cache:
                item["title_ko"] = self._cache[key]
            else:
                to_translate.append(item)

        cache_hit = len(items) - len(to_translate)
        if not to_translate:
            print(f"  -- 번역 전체 캐시 히트 ({cache_hit}개)")
            return items

        # 단일 API 호출 배치 번역
        headlines = [{"id": i, "en": item["title"]} for i, item in enumerate(to_translate)]
        prompt = (
            "물류/무역/가전 업계 전문 독자 대상 뉴스레터용 번역.\n"
            "아래 영문 헤드라인을 자연스러운 한국어로 번역하세요.\n"
            "고유명사(항구명, 선사명, 지역명)는 한국어 표기 사용.\n\n"
            f"입력:\n{json.dumps(headlines, ensure_ascii=False)}\n\n"
            'JSON 배열만 반환: [{"id": 0, "ko": "번역문"}, ...]'
        )
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                headers={"content-type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 2000},
                },
                timeout=30,
            )
            resp.raise_for_status()
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip().replace("```json","").replace("```","").strip()
            translations = {t["id"]: t["ko"] for t in json.loads(raw)}
            for i, item in enumerate(to_translate):
                ko = translations.get(i, "")
                item["title_ko"] = ko
                self._cache[self._cache_key(item["title"])] = ko
            self._save_cache()
            print(f"  -- 번역 완료: {len(to_translate)}개 신규 / {cache_hit}개 캐시 히트")
        except Exception as e:
            print(f"  -- 번역 실패: {e}")
        return items

    def fetch(self) -> list[dict]:
        all_items, seen_titles = [], set()
        for region, urls in FEEDS.items():
            region_items = []
            for url in urls:
                try:
                    for item in self._parse_feed(region, url):
                        if item["title"] not in seen_titles:
                            seen_titles.add(item["title"])
                            region_items.append(item)
                except Exception as e:
                    print(f"  -- RSS [{region}] {url[:50]}: {e}")
            top = region_items[:MAX_PER_REGION]
            all_items.extend(top)
            print(f"  -- News / {region}: {len(top)}개")
        if self.translate and all_items:
            all_items = self._batch_translate(all_items)
        return all_items
