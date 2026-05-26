"""
Desert to Cape — extra.com Scraper (Playwright 기반)
JavaScript 렌더링 필요 → 로컬 실행 전용
설치: pip install playwright && playwright install chromium
"""
import re
from .base import BaseScraper

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


BRAND_URLS = {
    "Samsung": "https://www.extra.com/en-sa/c/televisions/samsung-televisions/SA_TEL_SAM",
    "LG":      "https://www.extra.com/en-sa/c/televisions/lg-televisions/SA_TEL_LG",
    "TCL":     "https://www.extra.com/en-sa/c/televisions/tcl-televisions/SA_TEL_TCL",
    "Hisense": "https://www.extra.com/en-sa/c/televisions/hisense-televisions/SA_TEL_HIS",
}

PRICE_RE  = re.compile(r"SAR\s*([\d,]+(?:\.\d{1,2})?)", re.I)
SIZE_RE   = re.compile(r"(\d{2,3})\s*[\"']?\s*(?:inch|in\b)?", re.I)
MODEL_RE  = re.compile(r"\b([A-Z0-9]{3,10})\b")


class ExtraComScraper(BaseScraper):
    SOURCE_NAME   = "extra.com"
    SOURCE_REGION = "Saudi Arabia"
    SOURCE_URL    = "https://www.extra.com"

    # ── 셀렉터 (변경 시 여기만 수정) ──────────────────────
    CARD_SEL  = "div.product-item, div[class*='ProductCard'], div[class*='product-card'], li.product-item"
    NAME_SEL  = "h2, h3, [class*='product-name'], [class*='ProductName'], [class*='title']"
    PRICE_SEL = "[class*='price'], [class*='Price'], span.amount, [class*='current-price']"
    # ──────────────────────────────────────────────────────

    def _parse_page(self, brand: str, html: str) -> list[dict]:
        soup = self.soup(html)
        products = []
        for card in soup.select(self.CARD_SEL)[:15]:
            name_el  = card.select_one(self.NAME_SEL)
            price_el = card.select_one(self.PRICE_SEL)
            if not name_el or not price_el:
                continue
            name  = name_el.get_text(" ", strip=True)
            price_txt = price_el.get_text(" ", strip=True)
            m = PRICE_RE.search(price_txt)
            if not m:
                continue
            size_m = SIZE_RE.search(name)
            products.append({
                "source":     self.SOURCE_NAME,
                "region":     self.SOURCE_REGION,
                "fetched_at": self._fetched_at,
                "brand":      brand,
                "name":       name[:120],
                "size_inch":  int(size_m.group(1)) if size_m else None,
                "price_sar":  float(m.group(1).replace(",", "")),
            })
        return products

    def fetch(self) -> list[dict]:
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright 미설치: pip install playwright && playwright install chromium")

        all_items = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page    = browser.new_page()
            page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})

            for brand, url in BRAND_URLS.items():
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(2000)
                    html = page.content()
                    items = self._parse_page(brand, html)
                    all_items.extend(items)
                    print(f"  ✓ extra.com / {brand}: {len(items)}개")
                except Exception as e:
                    print(f"  ✗ extra.com / {brand}: {e}")

            browser.close()
        return all_items
