"""
Desert to Cape — Chart Generator v2
인라인 SVG 차트 (외부 의존성 없음, 이메일·웹 모두 호환).
"""
import math

def _clamp(v, lo, hi): return max(lo, min(hi, v))

# ── 팔레트 ─────────────────────────────────────────────────
def _rate_color(pct_above_min: float) -> str:
    """0=초록(저렴) → 1=빨강(고가). 히트맵용."""
    r = int(46  + pct_above_min * (192 - 46))
    g = int(125 + pct_above_min * (57  - 125))
    b = int(50  + pct_above_min * (43  - 50))
    return f"#{r:02x}{g:02x}{b:02x}"

def _util_color(pct: float) -> str:
    """선복률 색상: 낮음=초록, 높음=빨강."""
    if pct < 70:   return "#2E7D32"
    if pct < 85:   return "#E67E22"
    return "#C0392B"

def _fx_change_color(v) -> str:
    if v is None: return "#ccc"
    return "#C0392B" if v > 0 else ("#2E7D32" if v < 0 else "#666")


# ── 스파크라인 ───────────────────────────────────────────────
def sparkline(values: list, width=100, height=34,
              color="#C9A96E", fill=True, show_dots=True) -> str:
    if not values or len(values) < 2:
        return f'<svg width="{width}" height="{height}"></svg>'
    lo, hi = min(values), max(values)
    rng = hi - lo or 1
    pad = 4
    W, H = width - 2*pad, height - 2*pad

    pts = [(round(pad + i/(len(values)-1)*W, 1),
            round(pad + (1-(v-lo)/rng)*H, 1))
           for i, v in enumerate(values)]
    poly = " ".join(f"{x},{y}" for x,y in pts)

    fill_d = f"M{pts[0][0]},{height} " + " ".join(f"L{x},{y}" for x,y in pts) + f" L{pts[-1][0]},{height} Z"
    fill_svg = f'<path d="{fill_d}" fill="{color}" opacity="0.12"/>' if fill else ""

    dots = ""
    if show_dots:
        for i, (x,y) in enumerate(pts):
            r = 2.5 if i == len(pts)-1 else 1.5
            op = "1" if i == len(pts)-1 else "0.5"
            dots += f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" opacity="{op}"/>'

    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg" style="display:block;">'
            f'{fill_svg}'
            f'<polyline points="{poly}" fill="none" stroke="{color}" '
            f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
            f'{dots}</svg>')


# ── 수평 바 ──────────────────────────────────────────────────
def hbar(value: float, max_v=100, width=80, height=8, color=None) -> str:
    pct   = _clamp(value/max_v*100, 0, 100)
    c     = color or _util_color(pct)
    bar_w = max(3, round(pct/100*width, 1))
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;">'
            f'<rect x="0" y="0" width="{width}" height="{height}" rx="2" fill="#F0EDE8"/>'
            f'<rect x="0" y="0" width="{bar_w}" height="{height}" rx="2" fill="{c}" opacity="0.9"/>'
            f'</svg>')


# ── 링 게이지 ─────────────────────────────────────────────────
def gauge_ring(value: float, max_v=100, size=52, stroke=7) -> str:
    pct  = _clamp(value/max_v, 0, 1)
    r    = (size - stroke) / 2
    cx   = cy = size / 2
    circ = 2 * math.pi * r
    c    = "#2E7D32" if pct < 0.5 else ("#E67E22" if pct < 0.75 else "#C0392B")
    don  = round(pct * circ, 2)
    doff = round(circ - don, 2)
    txt  = f"{round(value)}%"
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#EDE8E2" stroke-width="{stroke}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="{stroke}" '
            f'stroke-linecap="round" stroke-dasharray="{don} {doff}" transform="rotate(-90 {cx} {cy})"/>'
            f'<text x="{cx}" y="{cy+1}" text-anchor="middle" dominant-baseline="middle" '
            f'font-size="10" font-weight="700" fill="{c}" font-family="JetBrains Mono,monospace">{txt}</text>'
            f'</svg>')


# ── 운임 히트맵 매트릭스 ─────────────────────────────────────
def freight_heatmap(routes: list, origins: list, destinations: list) -> str:
    """
    출발지 × 도착지 운임 히트맵 매트릭스.
    colors: 저렴(초록) → 고가(빨강) by 컬럼 정규화.
    """
    if not routes:
        return ""

    # 빠른 조회 dict
    rate_map = {}
    for r in routes:
        key = (r.get("origin",""), r.get("dest",""))
        fak = r.get("fak_usd")
        if fak:
            rate_map[key] = r

    # 목적지별 최소/최대 (컬럼 정규화)
    col_stats = {}
    for dest in destinations:
        vals = [r.get("fak_usd",0) for r in routes
                if r.get("dest","").startswith(dest[:4]) and r.get("fak_usd")]
        if vals:
            col_stats[dest] = (min(vals), max(vals))

    ORIGIN_FLAG = {"부산":"🇰🇷","중국":"🇨🇳","인도네시아":"🇮🇩","이집트":"🇪🇬"}
    DEST_SHORT  = {
        "두바이 (UAE)":       "두바이",
        "담맘 (Saudi Arabia)":"담맘",
        "도하 (Qatar)":       "도하",
        "몸바사 (Kenya)":     "몸바사",
        "더반 (South Africa)":"더반",
        "라고스 (Nigeria)":   "라고스",
    }

    # 헤더
    th_cells = "".join(
        f'<th style="padding:8px 10px;font-size:10px;letter-spacing:0.5px;'
        f'color:#9BA3B0;font-weight:600;text-align:center;white-space:nowrap;">'
        f'{DEST_SHORT.get(d,d[:4])}</th>'
        for d in destinations
    )
    header = f'<tr><th style="padding:8px 12px;text-align:left;font-size:10px;color:#9BA3B0;">출발지</th>{th_cells}</tr>'

    # 행
    rows = ""
    for origin in origins:
        flag = ORIGIN_FLAG.get(origin,"")
        cells = ""
        for dest in destinations:
            # dest prefix 매칭
            match = next((r for r in routes
                          if r.get("origin")==origin
                          and r.get("dest","").startswith(dest[:4])), None)
            if match and match.get("fak_usd"):
                fak  = match["fak_usd"]
                prev = match.get("prev_usd")
                lo, hi = col_stats.get(dest, (fak, fak))
                norm = (fak-lo)/(hi-lo) if hi != lo else 0.5
                bg   = _rate_color(norm)

                diff_html = ""
                if prev:
                    d = fak - prev
                    s = "+" if d>=0 else ""
                    dc = "#fff" if abs(d)<50 else ("#ffcccc" if d>0 else "#ccffcc")
                    diff_html = (f'<div style="font-size:9px;color:{dc};opacity:0.85;margin-top:1px;">'
                                 f'{s}${d:,.0f}</div>')

                cells += (f'<td style="padding:8px 6px;text-align:center;background:{bg};border:1px solid rgba(255,255,255,0.15);">'
                          f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:12px;font-weight:700;color:#fff;">'
                          f'${fak:,.0f}</div>'
                          f'{diff_html}</td>')
            else:
                cells += '<td style="padding:8px 6px;text-align:center;background:#F5F2EE;"><span style="color:#ccc;font-size:11px;">—</span></td>'

        rows += (f'<tr><td style="padding:8px 12px;font-size:12px;font-weight:600;'
                 f'color:#1A1A2E;white-space:nowrap;">{flag} {origin}</td>{cells}</tr>')

    legend = (
        '<div style="display:flex;align-items:center;gap:8px;margin-top:10px;font-size:10px;color:#999;">'
        '<span>저렴</span>'
        '<div style="height:8px;width:120px;border-radius:4px;background:linear-gradient(to right,#2e7d32,#e67e22,#c0392b);"></div>'
        '<span>고가</span>'
        '<span style="margin-left:12px;">기준: 목적지별 정규화</span>'
        '</div>'
    )

    return (f'<div style="overflow-x:auto;margin:16px 0;">'
            f'<table style="border-collapse:collapse;width:100%;font-family:\'Source Sans 3\',sans-serif;">'
            f'<thead style="background:#1A1A2E;">{header}</thead>'
            f'<tbody>{rows}</tbody>'
            f'</table>{legend}</div>')


# ── 환율 미니 델타 ────────────────────────────────────────────
def fx_delta_badge(pct, label="전주") -> str:
    if pct is None:
        return f'<span style="color:#ddd;font-size:10px;">—</span>'
    c = _fx_change_color(pct)
    a = "▲" if pct > 0 else ("▼" if pct < 0 else "–")
    s = "+" if pct > 0 else ""
    return (f'<span style="color:{c};font-size:11px;font-family:\'JetBrains Mono\',monospace;font-weight:600;">'
            f'{a}{s}{pct:.1f}%</span>')
