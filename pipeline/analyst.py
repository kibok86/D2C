"""
Desert to Cape — AI Analyst
수집된 원시 데이터를 Gemini API에 전달해 뉴스레터 코멘터리 자동 생성.
수동 작성 시간: 0분.
"""
import json
import requests
from datetime import datetime, UTC

GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def _call_gemini(prompt: str, max_tokens: int = 600) -> str:
    resp = requests.post(
        f"{GEMINI_API}?key={_get_api_key()}",
        headers={"content-type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _get_api_key() -> str:
    import os
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "export GEMINI_API_KEY=AIza..."
        )
    return key


def generate_analysis(data: dict) -> dict:
    """
    수집된 데이터 → AI 코멘터리 딕셔너리 반환.
    각 섹션별 한국어 + 영어 분석문 자동 생성.
    """
    print("\n[AI Analyst] 코멘터리 생성 중...")
    today = datetime.now(UTC).strftime("%Y년 %m월 %d일")
    commentary = {}

    # ── 1. 운임 동향 분석 ──────────────────────────────────
    freight = data.get("freight", {})
    routes  = freight.get("data", [])
    filled  = [r for r in routes if r.get("fak_usd")]

    if filled:
        routes_text = "\n".join(
            f"- {r['route']}: ${r['fak_usd']}/TEU "
            f"(전주: ${r.get('prev_usd','?')})"
            for r in filled
        )
        gri = freight.get("gri_notice", "없음")
        prompt = f"""당신은 물류·해운 전문 애널리스트입니다.
아래 {today} 기준 부산발 MEA 노선 FAK 운임 데이터를 바탕으로
뉴스레터용 운임 동향 분석문을 작성하세요.

{routes_text}
GRI 공지: {gri}

요구사항:
- 한국어로 2~3문장 (트렌드 요약 + 실무 시사점)
- 영어로 1~2문장 (같은 내용 요약)
- JSON 형식으로만 응답: {{"ko": "...", "en": "..."}}
- 추측이나 불확실한 내용 포함 금지"""
        try:
            raw = _call_gemini(prompt, 400)
            commentary["freight"] = json.loads(raw.strip().strip("```json").strip("```"))
            print("  ✓ 운임 코멘터리 생성 완료")
        except Exception as e:
            print(f"  ✗ 운임 코멘터리 실패: {e}")

    # ── 2. 가격 동향 분석 ──────────────────────────────────
    products = data.get("products", {}).get("data", [])
    if products:
        price_summary = []
        for brand in ["Samsung", "LG", "TCL", "Hisense"]:
            brand_items = [p for p in products if p["brand"] == brand]
            if brand_items:
                prices = [p["price_sar"] for p in brand_items]
                price_summary.append(
                    f"{brand}: SAR {min(prices):,.0f}~{max(prices):,.0f} "
                    f"({len(brand_items)}개 모델)"
                )
        price_text = "\n".join(price_summary)
        prompt = f"""당신은 중동 소비가전 시장 전문 애널리스트입니다.
extra.com(사우디 최대 가전 리테일러) {today} 기준 TV 가격 데이터:

{price_text}

요구사항:
- 브랜드 간 가격 포지셔닝과 시장 시사점을 분석
- 한국어 2문장 + 영어 1문장
- JSON만 응답: {{"ko": "...", "en": "..."}}
- 데이터에 없는 내용 추측 금지"""
        try:
            raw = _call_gemini(prompt, 350)
            commentary["retail"] = json.loads(raw.strip().strip("```json").strip("```"))
            print("  ✓ 가격 코멘터리 생성 완료")
        except Exception as e:
            print(f"  ✗ 가격 코멘터리 실패: {e}")

    # ── 3. 지정학 리스크 요약 ─────────────────────────────
    news = data.get("news", {}).get("data", [])
    if news:
        headlines = "\n".join(
            f"[{n['region']}] {n['title']}"
            for n in news[:10]
        )
        prompt = f"""당신은 지정학 리스크 및 공급망 전문 애널리스트입니다.
{today} 기준 MEA 지역 주요 뉴스 헤드라인:

{headlines}

요구사항:
- 물류·공급망·무역에 영향을 줄 수 있는 리스크 요인 2~3개 추출
- 한국어 3문장 이내 + 영어 2문장
- JSON만 응답: {{"ko": "...", "en": "...", "risk_level": "낮음|중간|높음"}}
- 헤드라인에 없는 내용 추측·추가 금지"""
        try:
            raw = _call_gemini(prompt, 400)
            commentary["geopolitics"] = json.loads(raw.strip().strip("```json").strip("```"))
            print("  ✓ 지정학 코멘터리 생성 완료")
        except Exception as e:
            print(f"  ✗ 지정학 코멘터리 실패: {e}")

    # ── 4. 이번 주 실무 팁 ────────────────────────────────
    context_parts = []
    if filled:
        context_parts.append(f"운임 트렌드: {commentary.get('freight', {}).get('ko', '')}")
    if commentary.get("geopolitics"):
        context_parts.append(f"리스크 레벨: {commentary['geopolitics'].get('risk_level', '')}")
    context = " | ".join(context_parts) or "일반 MEA 무역·물류 컨텍스트"

    prompt = f"""당신은 MEA 무역·물류 실무 전문가입니다.
컨텍스트: {context}

이번 주 상황에 맞는 물류/무역 실무 팁 1개를 작성하세요.
요구사항:
- 구체적이고 즉시 활용 가능한 팁
- 한국어 2~3문장 + 영어 1~2문장
- JSON만 응답: {{"ko": "...", "en": "..."}}"""
    try:
        raw = _call_gemini(prompt, 300)
        commentary["pro_tip"] = json.loads(raw.strip().strip("```json").strip("```"))
        print("  ✓ 실무 팁 생성 완료")
    except Exception as e:
        print(f"  ✗ 실무 팁 실패: {e}")

    # ── 5. TV 시장 코멘터리 ────────────────────────────
    tv_data = data.get("tv_market", {})
    if tv_data.get("data"):
        try:
            commentary["tv_market"] = generate_tv_commentary(tv_data)
            print("  ✓ TV 시장 코멘터리 생성 완료")
        except Exception as e:
            print(f"  ✗ TV 코멘터리 실패: {e}")

    return commentary


def generate_tv_commentary(tv_data: dict) -> dict:
    """TV 시장 데이터 → AI 코멘터리 생성."""
    brands  = [i for i in tv_data.get("data",[]) if i.get("type")=="brand"]
    cats    = [i for i in tv_data.get("data",[]) if i.get("type")=="category"]
    regions = [i for i in tv_data.get("data",[]) if i.get("type")=="region"]
    news    = [i for i in tv_data.get("data",[]) if i.get("type")=="news"]

    if not brands:
        return {}

    brand_txt = "\n".join(
        f"- {b['brand']} ({b['segment']}): 점유율 {b.get('market_share_pct','?')}% "
        f"추세={b.get('trend','?')} 가격지수={b.get('price_index','?')} "
        f"{b.get('note','')}"
        for b in brands
    )
    cat_txt = "\n".join(
        f"- {c['category']}: {c.get('trend','?')} — {c.get('note','')}"
        for c in cats
    )
    news_txt = "\n".join(f"- {n.get('title_ko') or n.get('title','')}" for n in news[:4])

    prompt = f"""당신은 MEA 소비가전 시장 전문 애널리스트입니다.
아래 데이터를 바탕으로 뉴스레터용 TV 시장 동향 코멘터리를 작성하세요.

브랜드 현황:
{brand_txt}

카테고리 트렌드:
{cat_txt}

주요 뉴스:
{news_txt}

요구사항:
- 한국어 3~4문장 (브랜드 경쟁구도 + 카테고리 동향 + 지역 시사점)
- 영어 2문장 요약
- JSON만 응답: {{"ko": "...", "en": "..."}}
- 데이터에 없는 수치 추측 금지"""

    try:
        raw = _call_gemini(prompt, 500)
        return json.loads(raw.strip().strip("```json").strip("```"))
    except Exception as e:
        print(f"  ✗ TV 코멘터리 실패: {e}")
        return {}
