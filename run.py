"""
Desert to Cape — Pipeline Runner v3
실행: python run.py [--issue N] [--no-ai] [--skip-scrape] [--no-translate]
"""
import json, sys, argparse
from pathlib import Path
from datetime import datetime, UTC

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from scrapers.extra_com         import ExtraComScraper
from scrapers.news_rss          import NewsScraper
from scrapers.fx_rates          import FxRateScraper
from scrapers.freight_index     import FreightIndexScraper
from scrapers.port_status       import PortStatusScraper
from scrapers.carrier_schedule  import CarrierScheduleScraper
from scrapers.freight           import load_freight_rates
from pipeline.analyst           import generate_analysis
from pipeline.generator         import generate

def build_scrapers(translate: bool) -> list:
    return [
        FreightIndexScraper(delay=2.0),
        NewsScraper(delay=1.0, translate=translate),
        FxRateScraper(delay=1.0),
        PortStatusScraper(delay=1.5),
        CarrierScheduleScraper(delay=1.5),
        ExtraComScraper(delay=2.0),
    ]

def run(issue_num, use_ai, skip_scrape, translate):
    data_file = ROOT / "data" / "pipeline_output.json"
    data_file.parent.mkdir(exist_ok=True)
    out_html  = ROOT / f"newsletter_{issue_num:03d}.html"

    print("=" * 54)
    print(f"  Desert to Cape — Issue #{issue_num:03d}")
    print("=" * 54)

    if skip_scrape and data_file.exists():
        print("\n[스킵] 기존 pipeline_output.json 사용")
        with open(data_file, encoding="utf-8") as f:
            payload = json.load(f)
    else:
        print("\n[1/4] 데이터 수집...")
        sources = {}
        for scraper in build_scrapers(translate):
            name = scraper.SOURCE_NAME
            print(f"\n  [{name}]")
            result = scraper.run()
            sources[name] = result
            icon = "OK" if result["status"] == "ok" else "ERR"
            print(f"  {icon}: {result['count']}건")

        print(f"\n  [운임 FAK]")
        sources["freight"] = load_freight_rates()

        payload = {
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "issue": issue_num,
            "sources": sources,
        }
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n  pipeline_output.json 저장 완료")

    commentary = {}
    if use_ai:
        print("\n[2/4] AI 코멘터리...")
        s = payload["sources"]
        try:
            commentary = generate_analysis({
                "products":      s.get("extra.com",        {}),
                "news":          s.get("RSS News",          {}),
                "freight":       s.get("freight",           {}),
                "freight_index": s.get("Freight Index",     {}),
            })
        except Exception as e:
            print(f"  ERR: {e}")
    else:
        print("\n[2/4] AI 스킵 (--no-ai)")

    print("\n[3/4] HTML 생성...")
    generate(payload, commentary, issue_num, out_html)

    print("\n" + "=" * 54)
    s = payload["sources"]
    rows = [
        ("운임지수",        s.get("Freight Index",    {}).get("count",0), "자동"),
        ("뉴스+번역",       s.get("RSS News",         {}).get("count",0), "자동"),
        ("환율",            s.get("FX Rates",         {}).get("count",0), "자동"),
        ("항만 현황",       s.get("Port Status",      {}).get("count",0), "반자동"),
        ("선사 스케줄",     s.get("Carrier Schedule", {}).get("count",0), "반자동"),
        ("가전 유통가",     s.get("extra.com",        {}).get("count",0), "자동"),
        ("AI 코멘터리",     len(commentary),                               "자동"),
        ("운임 FAK",        s.get("freight",          {}).get("count",0), "수동"),
    ]
    print(f"\n  {'항목':<18} {'건수':>5}  방식")
    print(f"  {'-'*38}")
    for name, count, method in rows:
        icon = "OK" if count > 0 else ("--" if method == "수동" else "XX")
        print(f"  [{icon}] {name:<16} {count:>5}  {method}")
    print(f"\n  출력: {out_html.name}")
    print("=" * 54)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--issue",        type=int, default=1)
    p.add_argument("--no-ai",        action="store_true")
    p.add_argument("--skip-scrape",  action="store_true")
    p.add_argument("--no-translate", action="store_true")
    args = p.parse_args()
    run(args.issue, not args.no_ai, args.skip_scrape, not args.no_translate)
