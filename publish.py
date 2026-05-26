"""
Desert to Cape — 발행 스크립트 v2 (GitHub Actions 최적화)
python publish.py --issue N [--dry-run] [--skip-scrape]
"""
import json, sys, argparse, os, requests
from pathlib import Path
from datetime import datetime, UTC

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from scrapers.news_rss          import NewsScraper
from scrapers.fx_rates          import FxRateScraper
from scrapers.freight_index     import FreightIndexScraper
from scrapers.port_status       import PortStatusScraper
from scrapers.carrier_schedule  import CarrierScheduleScraper
from scrapers.tv_market         import TVMarketScraper
from scrapers.freight           import load_freight_rates
from pipeline.analyst           import generate_analysis
from pipeline.generator         import generate

LOG_FILE = ROOT / "data" / "publish_log.json"


def send_via_resend(html_path: Path, issue_num: int) -> dict:
    from pipeline.stibee import publish_issue
    return publish_issue(html_path, issue_num)


def _save_log(issue_num, entry):
    LOG_FILE.parent.mkdir(exist_ok=True)
    log = json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else {"issues":[]}
    log["issues"].append({"issue": issue_num,
                           "published_at": datetime.now(UTC).isoformat(), **entry})
    LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2))


def run(issue_num: int, dry_run: bool, skip_scrape: bool):
    data_file = ROOT / "data" / "pipeline_output.json"
    data_file.parent.mkdir(exist_ok=True)
    out_html  = ROOT / f"newsletter_{issue_num:03d}.html"

    print("=" * 50)
    print(f"  Desert to Cape  Issue #{issue_num:03d}" + ("  [DRY RUN]" if dry_run else ""))
    print("=" * 50)

    if skip_scrape and data_file.exists():
        print("\n[1/4] 캐시 데이터 사용")
        payload = json.loads(data_file.read_text())
    else:
        print("\n[1/4] 데이터 수집...")
        sources = {}
        for sc in [FreightIndexScraper(delay=2.0), NewsScraper(delay=1.0, translate=True),
                   FxRateScraper(delay=1.0), PortStatusScraper(delay=1.5),
                   CarrierScheduleScraper(delay=1.5), TVMarketScraper(delay=1.5)]:
            print(f"\n  [{sc.SOURCE_NAME}]")
            res = sc.run()
            sources[sc.SOURCE_NAME] = res
            print(f"  {'OK' if res['status']=='ok' else 'ERR'}: {res['count']}건")
        print(f"\n  [운임 FAK]")
        sources["freight"] = load_freight_rates()
        payload = {"generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "issue": issue_num, "sources": sources}
        data_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    print("\n[2/4] AI 코멘터리...")
    s = payload["sources"]
    try:
        commentary = generate_analysis({
            "news": s.get("RSS News",{}), "freight": s.get("freight",{}),
            "freight_index": s.get("Freight Index",{}),
        })
    except Exception as e:
        print(f"  -- {e}"); commentary = {}

    print("\n[3/4] HTML 생성...")
    generate(payload, commentary, issue_num, out_html)

    print(f"\n[4/4] Resend 발송{'  [SKIPPED]' if dry_run else '...'}")
    send_result = {}
    if not dry_run:
        try:
            send_result = send_via_resend(out_html, issue_num)
        except Exception as e:
            print(f"  -- 실패: {e}"); send_result = {"error": str(e)}
    else:
        print(f"  -> {out_html.name}")

    _save_log(issue_num, {"dry_run": dry_run, "html": str(out_html),
                           "sections": list(commentary.keys()), "send": send_result})
    print(f"\n  완료: {out_html.name}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--issue",       type=int, default=1)
    p.add_argument("--dry-run",     action="store_true")
    p.add_argument("--skip-scrape", action="store_true")
    args = p.parse_args()
    run(args.issue, args.dry_run, args.skip_scrape)
