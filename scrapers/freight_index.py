"""
Desert to Cape — Freight Index Scraper
공개 운임지수(SCFI, Drewry WCI, FBX) 자동 수집.
소스별 실패 시 다음 소스로 자동 전환 (Cascade fallback).
"""
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, UTC
from .base import BaseScraper
from .storage import save_freight_index, get_freight_index_change

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

# ── 지수 메타 정보 ────────────────────────────────────────
INDEX_META = {
    "SCFI":    {"full": "Shanghai Containerized Freight Index", "unit": "pt", "desc": "상하이 발 컨테이너 종합운임지수"},
    "WCI":     {"full": "Drewry World Container Index",         "unit": "$/FEU", "desc": "글로벌 8개 주요 노선 평균 운임"},
    "FBX":     {"full": "Freightos Baltic Index",               "unit": "$/FEU", "desc": "글로벌 컨테이너 운임 종합지수"},
    "CCFI":    {"full": "China Containerized Freight Index",    "unit": "pt", "desc": "중국 발 컨테이너 종합운임지수"},
    "BDI":     {"full": "Baltic Dry Index",                     "unit": "pt", "desc": "건화물 해운 운임지수"},
}


class FreightIndexScraper(BaseScraper):
    SOURCE_NAME   = "Freight Index"
    SOURCE_REGION = "Global"

    # ── 소스별 파서 목록 (실패 시 다음으로) ────────────────
    PARSERS = [
        "_parse_scfi_sse",
        "_parse_drewry_wci",
        "_parse_fbx",
        "_parse_google_news_indices",  # 뉴스에서 지수 값 추출 (최후 fallback)
    ]

    # ── SCFI: 상하이 해운 거래소 ─────────────────────────
    def _parse_scfi_sse(self) -> list[dict]:
        url  = "https://en.sse.net.cn/indices/scfinew.jsp"
        resp = self.get(url)
        soup = BeautifulSoup(resp.text, "lxml")

        # 테이블에서 SCFI 값 추출
        tables = soup.find_all("table")
        for table in tables:
            text = table.get_text()
            m = re.search(r"SCFI\s*[\s\S]{0,50}?([\d,]+\.?\d*)", text, re.I)
            if m:
                value = float(m.group(1).replace(",", ""))
                if 500 < value < 20000:  # 합리적 범위 검증
                    return [self._make_item("SCFI", value)]
        raise ValueError("SCFI 파싱 실패")

    # ── Drewry WCI ────────────────────────────────────────
    def _parse_drewry_wci(self) -> list[dict]:
        url  = "https://www.drewry.co.uk/supply-chain-advisors/supply-chain-expertise/world-container-index-assessed-by-drewry"
        resp = self.get(url)
        soup = BeautifulSoup(resp.text, "lxml")

        # WCI 수치 패턴: "$X,XXX" 형태
        text = soup.get_text()
        matches = re.findall(r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:per FEU|/FEU)", text, re.I)
        if matches:
            value = float(matches[0].replace(",", ""))
            if 500 < value < 30000:
                return [self._make_item("WCI", value)]
        raise ValueError("Drewry WCI 파싱 실패")

    # ── Freightos FBX ─────────────────────────────────────
    def _parse_fbx(self) -> list[dict]:
        url  = "https://fbx.freightos.com/"
        resp = self.get(url)
        soup = BeautifulSoup(resp.text, "lxml")

        text = soup.get_text()
        m = re.search(r"FBX\s*[\s\S]{0,100}?\$\s*([\d,]+(?:\.\d+)?)", text, re.I)
        if m:
            value = float(m.group(1).replace(",", ""))
            if 500 < value < 30000:
                return [self._make_item("FBX", value)]
        raise ValueError("FBX 파싱 실패")

    # ── Google News fallback: 뉴스 텍스트에서 지수값 추출 ──
    def _parse_google_news_indices(self) -> list[dict]:
        import feedparser
        results = []
        queries = [
            ("SCFI", "https://news.google.com/rss/search?q=SCFI+shanghai+containerized+freight+index&hl=en"),
            ("WCI",  "https://news.google.com/rss/search?q=drewry+world+container+index+WCI&hl=en"),
            ("FBX",  "https://news.google.com/rss/search?q=freightos+baltic+index+FBX&hl=en"),
        ]
        for name, url in queries:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                text = entry.get("title", "") + " " + entry.get("summary", "")
                # "$X,XXX" 또는 "X,XXX points" 패턴
                patterns = [
                    rf"{name}[^\d]{{0,30}}?\$?\s*([\d,]+(?:\.\d+)?)\s*(?:per FEU|/FEU|pts?|points?)?",
                    r"\$\s*([\d,]+(?:\.\d+)?)\s*per FEU",
                ]
                for pat in patterns:
                    m = re.search(pat, text, re.I)
                    if m:
                        try:
                            value = float(m.group(1).replace(",", ""))
                            if 200 < value < 30000:
                                results.append(self._make_item(name, value, source="Google News"))
                                break
                        except ValueError:
                            pass
                if any(r["name"] == name for r in results):
                    break
        if not results:
            raise ValueError("뉴스 fallback 파싱 실패")
        return results

    def _make_item(self, name: str, value: float, source: str = "Web") -> dict:
        meta = INDEX_META.get(name, {})
        change = get_freight_index_change(name)
        return {
            "source":           self.SOURCE_NAME,
            "region":           "Global",
            "fetched_at":       self._fetched_at,
            "name":             name,
            "full_name":        meta.get("full", name),
            "unit":             meta.get("unit", ""),
            "desc":             meta.get("desc", ""),
            "value":            value,
            "week_change_pct":  change.get("week_change_pct"),
            "month_change_pct": change.get("month_change_pct"),
            "data_source":      source,
        }

    def fetch(self) -> list[dict]:
        all_results = []
        attempted   = set()

        for parser_name in self.PARSERS:
            parser = getattr(self, parser_name)
            try:
                results = parser()
                for r in results:
                    if r["name"] not in attempted:
                        all_results.append(r)
                        attempted.add(r["name"])
                        print(f"  ✓ {r['name']}: {r['value']:,.1f} {r['unit']} ({r['data_source']})")
            except Exception as e:
                print(f"  ✗ {parser_name}: {e}")

        # 히스토리 저장
        if all_results:
            save_freight_index(all_results)

        return all_results
