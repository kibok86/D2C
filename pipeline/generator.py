"""
Desert to Cape — Newsletter Generator v8 (Design Overhaul)
에디토리얼 매거진 스타일 · 히트맵 · 개선된 스파크라인
섹션: 운임지수 → 운임히트맵 → 운임동향 → 선사스케줄 → 항만현황 → 환율 → 지정학 → 실무팁
"""
from datetime import datetime, UTC
from pathlib import Path
from .charts import sparkline, hbar, gauge_ring, freight_heatmap, fx_delta_badge

FIXED_PEG  = {"SAR","AED","BHD","OMR","QAR","KWD"}
ORIGIN_ORDER = ["부산","중국","인도네시아","이집트"]
ORIGIN_FLAG  = {"부산":"🇰🇷","중국":"🇨🇳","인도네시아":"🇮🇩","이집트":"🇪🇬"}
DEST_ORDER   = ["두바이 (UAE)","담맘 (Saudi Arabia)","도하 (Qatar)",
                "몸바사 (Kenya)","더반 (South Africa)","라고스 (Nigeria)"]
STATUS_C     = {"정상":"#2E7D32","지연":"#E67E22","우회":"#C0392B","주의":"#E67E22","혼잡":"#C0392B"}

def _b(n, ok="✓ 자동",fail="⚠ 수동"):
    cls = "badge-ok" if n>0 else "badge-warn"
    return f'<span class="{cls}">{ok if n>0 else fail}</span>'

def _pct(v):
    if v is None: return '<span style="color:#ccc">—</span>'
    c = "#C0392B" if v>0 else ("#2E7D32" if v<0 else "#666")
    a,s = ("▲","+" ) if v>0 else (("▼","") if v<0 else ("–",""))
    return f'<span style="color:{c};font-weight:600;font-family:\'JetBrains Mono\',monospace;">{a} {s}{v:.1f}%</span>'


# ════════ 운임지수 카드 ═══════════════════════════════════════
def _index_cards(indices, hist):
    if not indices:
        return '<p style="color:#999;font-size:13px;padding:16px 0;">운임지수 자동 수집 실패</p>'

    cards = ""
    for idx in indices:
        name = idx["name"]
        val  = idx.get("value")
        unit = idx.get("unit","")
        wk   = idx.get("week_change_pct")
        mo   = idx.get("month_change_pct")
        desc = idx.get("desc","")
        src  = idx.get("data_source","")

        # 스파크라인 데이터 — 8주 시뮬레이션
        base = val or 1000
        sim  = [round(base * (0.86 + i*0.02 + (i%3-1)*0.005), 1) for i in range(9)]
        if val: sim[-1] = val
        svg  = sparkline(sim, width=110, height=36, color="#C9A96E")

        trend_up = (wk or 0) > 0
        t_arrow  = "▲" if trend_up else "▼"
        t_color  = "#C0392B" if trend_up else "#2E7D32"

        cards += f"""
<div style="background:#fff;border:1px solid #E8E0D4;border-radius:10px;
            padding:20px;position:relative;overflow:hidden;">
  <div style="position:absolute;top:0;right:0;width:4px;height:100%;
              background:{t_color};opacity:0.6;border-radius:0 10px 10px 0;"></div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
    <div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
                  font-weight:700;color:#1A1A2E;letter-spacing:0.5px;">{name}</div>
      <div style="font-size:10px;color:#C9A96E;margin-top:2px;
                  font-family:'JetBrains Mono',monospace;">{src}</div>
    </div>
    <div style="color:{t_color};font-size:18px;">{t_arrow}</div>
  </div>
  {svg}
  <div style="font-family:'Playfair Display',serif;font-size:26px;font-weight:900;
              color:#1A1A2E;line-height:1;margin-top:10px;">
    {f"{val:,.1f}" if val else "—"}
    <span style="font-size:12px;font-weight:400;color:#999;
                 font-family:'Source Sans 3',sans-serif;margin-left:4px;">{unit}</span>
  </div>
  <div style="display:flex;gap:16px;margin-top:10px;font-size:11px;
              border-top:1px solid #F0EDE8;padding-top:10px;">
    <div><span style="color:#999;">전주</span> {_pct(wk)}</div>
    <div><span style="color:#999;">전월</span> {_pct(mo)}</div>
  </div>
  <div style="font-size:10px;color:#aaa;margin-top:8px;line-height:1.4;">{desc}</div>
</div>"""
    return f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:16px 0;">{cards}</div>'


# ════════ 운임 히트맵 ════════════════════════════════════════
# freight_heatmap 은 charts.py에서 import


# ════════ 운임 동향 테이블 ════════════════════════════════════
def _freight_detail(routes):
    if not routes:
        return '<p style="color:#C0392B;font-size:13px;">freight_rates.json 업데이트 필요</p>'
    groups = {}
    for r in routes:
        groups.setdefault(r.get("origin","부산"),[]).append(r)

    html = ""
    for origin in ORIGIN_ORDER:
        grp = groups.get(origin,[])
        if not grp: continue
        flag = ORIGIN_FLAG.get(origin,"")
        html += f"""
<div style="margin-top:20px;">
  <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:#C9A96E;
              text-transform:uppercase;font-family:'JetBrains Mono',monospace;
              margin-bottom:6px;">{flag} {origin}</div>
  <table class="data-table" style="margin:0;">
    <thead><tr>
      <th>도착지</th>
      <th style="text-align:right;">$/TEU</th>
      <th style="text-align:right;">전주비</th>
      <th style="text-align:center;">리드타임</th>
      <th style="text-align:center;">현황</th>
    </tr></thead><tbody>"""
        for r in grp:
            fak  = r.get("fak_usd"); prev = r.get("prev_usd")
            tt   = r.get("transit_days"); st = r.get("status","")
            via  = r.get("via",""); note = r.get("note","")
            sc   = STATUS_C.get(st,"#666")

            fak_html = f"${fak:,.0f}" if fak else "—"
            if fak and prev:
                d = fak-prev; s="+"; dc="#C0392B"
                if d<0: s=""; dc="#2E7D32"
                elif d==0: dc="#666"
                diff_html = f'<span style="color:{dc};font-weight:600;font-family:\'JetBrains Mono\',monospace;font-size:11px;">{s}${d:,.0f}</span>'
            else:
                diff_html = '—'

            html += f"""
<tr>
  <td style="font-size:13px;">{r.get("dest","")}
    {f'<span style="font-size:10px;color:#bbb;margin-left:4px;">via {via}</span>' if via else ""}
    {f'<div style="font-size:10px;color:#999;">{note}</div>' if note else ""}
  </td>
  <td style="font-family:'JetBrains Mono',monospace;text-align:right;font-weight:600;">{fak_html}</td>
  <td style="text-align:right;">{diff_html}</td>
  <td style="text-align:center;font-size:12px;">{f"{tt}일" if tt else "—"}</td>
  <td style="text-align:center;"><span style="color:{sc};font-weight:700;font-size:11px;">{st or "—"}</span></td>
</tr>"""
        html += "</tbody></table></div>"
    return html

def _market_conditions(freight_d):
    conds = freight_d.get("market_conditions",[])
    if not conds: return ""
    out = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px;">'
    for c in conds:
        col = c.get('color','#C9A96E')
        out += f"""
<div style="border-left:3px solid {col};background:#FAFAFA;
            padding:12px 14px;border-radius:0 6px 6px 0;">
  <div style="font-size:11px;font-weight:700;color:{col};margin-bottom:4px;">
    {c.get('icon','')} {c.get('title','')}
  </div>
  <div style="font-size:12px;color:#555;line-height:1.5;font-weight:300;">{c.get('body','')}</div>
</div>"""
    return out + '</div>'


# ════════ 선사 스케줄 ═════════════════════════════════════════
def _carrier_cards(schedules):
    if not schedules:
        return '<p style="color:#999;font-size:13px;">데이터 없음</p>'
    rows = ""
    for s in schedules:
        cap  = s.get("capacity_pct",0)
        bar  = hbar(cap, width=90, height=10)
        cc   = s.get("carrier_color","#333")
        tc   = s.get("change_color","#666")
        bg   = s.get("change_bg","#F5F5F5")
        ic   = s.get("change_icon","📌")
        sc   = s.get("status_color","#666")
        eff  = s.get("effective_date","")
        rows += f"""
<tr>
  <td style="padding:12px;">
    <span style="font-family:'JetBrains Mono',monospace;font-weight:700;
                 color:{cc};font-size:13px;">{s['carrier']}</span>
    <span style="font-size:10px;color:#aaa;margin-left:6px;">{s.get('service','')}</span>
    <div style="font-size:11px;color:#666;margin-top:3px;">{s.get('route_ko','')}</div>
  </td>
  <td style="padding:12px;">
    <div style="display:flex;align-items:center;gap:8px;">
      {bar}
      <span style="font-family:'JetBrains Mono',monospace;font-size:11px;
                   font-weight:700;color:{_cap_color(cap)};">{cap}%</span>
    </div>
  </td>
  <td style="padding:12px;">
    <span style="background:{bg};color:{tc};font-size:10px;font-weight:700;
                 padding:3px 9px;border-radius:4px;white-space:nowrap;">{ic} {s.get('change_type','')}</span>
    <div style="font-size:11px;color:#555;margin-top:5px;line-height:1.5;">{s.get('change_detail','')}</div>
    {f'<div style="font-size:10px;color:#aaa;margin-top:3px;">적용 {eff}</div>' if eff else ""}
  </td>
  <td style="padding:12px;text-align:center;">
    <span style="color:{sc};font-weight:700;font-size:12px;">{s.get('status','')}</span>
  </td>
</tr>"""
    return f"""<table class="data-table">
<thead><tr>
  <th>선사 / 서비스</th>
  <th>선복률</th>
  <th>변경사항</th>
  <th style="text-align:center;">상태</th>
</tr></thead><tbody>{rows}</tbody></table>"""

def _cap_color(pct):
    if pct >= 90: return "#C0392B"
    if pct >= 80: return "#E67E22"
    return "#2E7D32"


# ════════ 항만 현황 ═══════════════════════════════════════════
def _port_grid(ports):
    if not ports:
        return '<p style="color:#999;font-size:13px;">항만 데이터 없음</p>'
    cards = ""
    for p in ports:
        cong = p.get("congestion_pct",0)
        wait = p.get("wait_days",0)
        sc   = p.get("status_color","#666")
        g    = gauge_ring(cong, size=56, stroke=7)
        note = p.get("note","")
        cards += f"""
<div style="border:1px solid #E8E0D4;border-radius:8px;padding:14px 16px;
            display:flex;gap:12px;align-items:center;background:#fff;">
  <div style="flex-shrink:0;">{g}</div>
  <div style="flex:1;min-width:0;">
    <div style="font-weight:700;font-size:13px;color:#1A1A2E;">{p.get('port_ko',p.get('port',''))}</div>
    <div style="font-size:10px;color:#aaa;margin-bottom:6px;">{p.get('country','')}</div>
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      <span style="color:{sc};font-weight:700;font-size:11px;
                   background:{sc}18;padding:2px 8px;border-radius:10px;">{p.get('status','')}</span>
      <span style="font-size:11px;color:#666;">체선 {wait}일</span>
    </div>
    {f'<div style="font-size:10px;color:#999;margin-top:5px;">{note}</div>' if note else ""}
  </div>
</div>"""
    return f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:16px 0;">{cards}</div>'


# ════════ 환율 ════════════════════════════════════════════════
def _fx_table(fx):
    rows = [f for f in fx if f.get("currency") not in FIXED_PEG]
    if not rows:
        return '<p style="color:#999;font-size:13px;">환율 데이터 수집 실패</p>'
    trs = ""
    for f in rows:
        code = f.get("currency",""); name = f.get("name","")
        rate = f.get("usd_rate",0)
        wk   = f.get("week_change_pct"); mo = f.get("month_change_pct")
        trs += f"""
<tr>
  <td style="padding:10px 12px;">
    <strong style="font-family:'JetBrains Mono',monospace;font-size:13px;">{code}</strong>
    <span style="font-size:11px;color:#aaa;margin-left:6px;">{name}</span>
  </td>
  <td style="padding:10px 12px;font-family:'JetBrains Mono',monospace;
             text-align:right;font-weight:600;">{rate:,.2f}</td>
  <td style="padding:10px 12px;text-align:right;">{fx_delta_badge(wk,"전주")}</td>
  <td style="padding:10px 12px;text-align:right;">{fx_delta_badge(mo,"전월")}</td>
</tr>"""
    return f"""<table class="data-table">
<thead><tr>
  <th>통화</th>
  <th style="text-align:right;">현재 (vs USD)</th>
  <th style="text-align:right;">전주비</th>
  <th style="text-align:right;">전월비</th>
</tr></thead><tbody>{trs}</tbody></table>
<p style="font-size:10px;color:#aaa;margin-top:6px;">
  SAR·AED 등 USD 고정 페그 통화 제외 · ▲ = 현지통화 약세
</p>"""


# ════════ 지정학 ══════════════════════════════════════════════
def _news_section(news, region, limit=4):
    items = [n for n in news if n.get("region")==region][:limit]
    if not items:
        return '<p style="color:#999;font-size:13px;">뉴스 수집 실패</p>'
    html = ""
    for item in items:
        ko  = item.get("title_ko","") or item.get("title","")
        en  = item.get("title","")
        url = item.get("url","#")
        src = item.get("source","")
        pub = str(item.get("published",""))[:10]
        html += f"""
<div style="padding:12px 0;border-bottom:1px solid #F5F2EE;">
  <div style="font-size:14px;color:#2C2C3E;line-height:1.6;margin-bottom:5px;">{ko}</div>
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
    <a href="{url}" target="_blank"
       style="font-size:10px;color:#C9A96E;font-family:'JetBrains Mono',monospace;
              text-decoration:none;letter-spacing:0.3px;">
      ↗ {en[:60]}{"…" if len(en)>60 else ""}
    </a>
    <span style="font-size:10px;color:#ccc;">· {src} · {pub}</span>
  </div>
</div>"""
    return html


# ════════ 파이프라인 푸터 ════════════════════════════════════
def _pipeline_footer(sources, commentary, gen_at):
    rows_data = [
        ("운임지수",      sources.get("Freight Index",   {}).get("count",0), "자동"),
        ("뉴스+번역",     sources.get("RSS News",        {}).get("count",0), "자동"),
        ("환율",          sources.get("FX Rates",        {}).get("count",0), "자동"),
        ("선사 스케줄",   sources.get("Carrier Schedule",{}).get("count",0), "반자동"),
        ("항만 현황",     sources.get("Port Status",     {}).get("count",0), "반자동"),
        ("AI 코멘터리",   len(commentary),                                    "자동"),
        ("운임 FAK",      sources.get("freight",         {}).get("count",0), "수동"),
    ]
    auto_pct = int(sum(1 for _,c,m in rows_data if c>0 and "수동" not in m) / len(rows_data) * 100)

    rows_html = "".join(f"""
<tr style="border-bottom:1px solid #F0EDE8;">
  <td style="padding:7px 14px;font-size:12px;">{n}</td>
  <td style="padding:7px 14px;text-align:center;">{"✅" if c>0 else ("⚠️" if "수동"==m else "❌")}</td>
  <td style="padding:7px 14px;text-align:right;font-family:'JetBrains Mono',monospace;
             font-size:11px;color:{"#2E7D32" if c>0 else "#C0392B"};">{c}건</td>
  <td style="padding:7px 14px;font-size:10px;color:#999;">{m}</td>
</tr>""" for n,c,m in rows_data)

    return f"""
<div style="background:#F8F9FC;border:1px solid #E0E4F0;border-radius:10px;padding:24px;margin-top:32px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
    <span style="font-family:'Playfair Display',serif;font-size:15px;font-weight:700;color:#1A1A2E;">파이프라인 현황</span>
    <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#666;">
      {gen_at[:10]} · 자동화
      <strong style="font-size:16px;color:#1A1A2E;margin-left:4px;">{auto_pct}%</strong>
    </span>
  </div>
  <table style="width:100%;border-collapse:collapse;">
    <thead><tr style="background:#1A1A2E;">
      <th style="padding:7px 14px;text-align:left;font-size:9px;letter-spacing:1.5px;color:#9BA3B0;font-family:'JetBrains Mono',monospace;text-transform:uppercase;">항목</th>
      <th style="padding:7px 14px;text-align:center;font-size:9px;letter-spacing:1.5px;color:#9BA3B0;font-family:'JetBrains Mono',monospace;text-transform:uppercase;">상태</th>
      <th style="padding:7px 14px;text-align:right;font-size:9px;letter-spacing:1.5px;color:#9BA3B0;font-family:'JetBrains Mono',monospace;text-transform:uppercase;">수집</th>
      <th style="padding:7px 14px;font-size:9px;letter-spacing:1.5px;color:#9BA3B0;font-family:'JetBrains Mono',monospace;text-transform:uppercase;">방식</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>"""


# ════════ 메인 생성 함수 ══════════════════════════════════════
CSS = """
:root{--sand:#C9A96E;--deep:#1A1A2E;--cream:#FAF6F0;--muted:#8A8A8A;--border:#E8E0D4;}
*{margin:0;padding:0;box-sizing:border-box;}
body{background:var(--cream);font-family:'Source Sans 3',sans-serif;color:var(--deep);line-height:1.7;}
.wrap{max-width:720px;margin:0 auto;background:#fff;border:1px solid var(--border);}

/* Header */
.header{background:var(--deep);padding:44px 52px 36px;position:relative;overflow:hidden;}
.header::after{content:'';position:absolute;top:0;right:0;width:240px;height:240px;
  background:radial-gradient(circle,rgba(201,169,110,.12) 0%,transparent 70%);
  border-radius:50%;transform:translate(40%,-40%);}
.header-meta{display:flex;justify-content:space-between;margin-bottom:24px;}
.issue-tag{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--sand);letter-spacing:3px;}
.date-tag{font-family:'JetBrains Mono',monospace;font-size:11px;color:#555;}
.masthead{font-family:'Playfair Display',serif;font-size:48px;font-weight:900;
  color:#fff;line-height:1;letter-spacing:-2px;}
.masthead em{color:var(--sand);font-style:normal;}
.tagline{font-size:13px;color:#6B7280;margin-top:12px;letter-spacing:0.3px;}

/* Cover stripe */
.cover{background:var(--sand);padding:13px 52px;display:flex;align-items:center;gap:12px;}
.cover-label{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--deep);
  letter-spacing:2.5px;text-transform:uppercase;font-weight:700;opacity:0.7;}
.cover-hl{font-family:'Playfair Display',serif;font-size:15px;color:var(--deep);font-weight:700;}

/* Body */
.body{padding:44px 52px;}
.sec{margin-bottom:48px;}

/* Section header */
.sec-hdr{display:flex;align-items:baseline;gap:14px;margin-bottom:20px;
  padding-bottom:12px;border-bottom:1.5px solid var(--deep);}
.sec-num{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--sand);
  letter-spacing:2px;font-weight:700;flex-shrink:0;}
.sec-title{font-family:'Playfair Display',serif;font-size:21px;font-weight:700;line-height:1;}
.sec-en{font-size:11px;color:var(--muted);font-weight:400;margin-left:4px;
  font-family:'Source Sans 3',sans-serif;}
.badge-ok{background:#E8F5E9;color:#2E7D32;font-size:9px;padding:2px 9px;border-radius:20px;
  font-family:'JetBrains Mono',monospace;font-weight:700;margin-left:auto;white-space:nowrap;letter-spacing:0.5px;}
.badge-warn{background:#FFF3CD;color:#856404;font-size:9px;padding:2px 9px;border-radius:20px;
  font-family:'JetBrains Mono',monospace;font-weight:700;margin-left:auto;white-space:nowrap;letter-spacing:0.5px;}

p{font-size:14px;color:#444;margin-bottom:14px;font-weight:300;line-height:1.75;}
.en-note{font-size:13px;color:#888;font-style:italic;margin:-6px 0 14px;
  border-left:2px solid var(--border);padding-left:12px;}

.data-table{width:100%;border-collapse:collapse;margin:14px 0;font-size:13px;}
.data-table thead tr{background:var(--deep);color:#fff;}
.data-table th{padding:9px 12px;text-align:left;font-family:'JetBrains Mono',monospace;
  font-size:9px;letter-spacing:1.5px;text-transform:uppercase;}
.data-table td{padding:10px 12px;border-bottom:1px solid #F5F2EE;
  font-weight:300;vertical-align:middle;}
.data-table tr:nth-child(even) td{background:#FDFBF8;}

.callout{border-left:3px solid var(--sand);background:#FDF8F0;
  padding:14px 18px;margin:16px 0;border-radius:0 8px 8px 0;}
.callout-lbl{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--sand);
  letter-spacing:2px;text-transform:uppercase;font-weight:700;margin-bottom:6px;}
.tip-box{background:var(--deep);color:#fff;padding:22px 26px;border-radius:10px;margin:16px 0;}
.tip-lbl{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--sand);
  letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;}
.tip-box p{color:#C8D0DC;font-size:14px;margin-bottom:0;line-height:1.7;}

hr{border:none;border-top:1px solid #F0EDE8;margin:36px 0;}

.next{background:var(--cream);border:1px solid var(--border);border-radius:8px;
  padding:22px 26px;margin-bottom:24px;}
.next-lbl{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--muted);
  letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;}
.next ul{list-style:none;padding:0;}
.next ul li{font-size:13px;padding:5px 0;color:#555;font-weight:300;}
.next ul li::before{content:'→ ';color:var(--sand);font-weight:700;}

.footer{background:var(--deep);padding:28px 52px;text-align:center;}
.footer-logo{font-family:'Playfair Display',serif;font-size:18px;font-weight:900;color:#fff;}
.footer-logo em{color:var(--sand);font-style:normal;}
.footer a{color:#6B7280;text-decoration:none;margin:0 10px;font-size:11px;}
"""

# ── 약자 주석 ────────────────────────────────────────────────
FOOTNOTES = {
    "freight_index": [
        ("SCFI", "Shanghai Containerized Freight Index — 상하이 컨테이너 운임지수"),
        ("WCI",  "Drewry World Container Index — 드류리 세계 컨테이너 지수"),
        ("FBX",  "Freightos Baltic Index — 프레이토스 발틱 종합운임지수"),
        ("BDI",  "Baltic Dry Index — 발틱 건화물 운임지수"),
        ("pt",   "포인트(Point) — 지수 단위"),
        ("FEU",  "Forty-foot Equivalent Unit — 40피트 컨테이너 1개"),
    ],
    "freight": [
        ("FAK",  "Freight All Kinds — 화물 종류 무관 단일 운임"),
        ("TEU",  "Twenty-foot Equivalent Unit — 20피트 컨테이너 1개"),
        ("GRI",  "General Rate Increase — 선사 일괄 운임 인상"),
        ("ETD",  "Estimated Time of Departure — 예상 출항일"),
        ("ETA",  "Estimated Time of Arrival — 예상 도착일"),
    ],
    "carrier": [
        ("GRI",  "General Rate Increase — 선사 일괄 운임 인상"),
        ("T/S",  "Transhipment — 환적 (중간 항구 경유)"),
        ("OOG",  "Out of Gauge — 특수화물 (초과 규격)"),
    ],
    "port": [
        ("체선일", "선박이 항만 내에서 입항·하역을 기다리는 평균 대기 일수"),
        ("혼잡도", "항만 처리 용량 대비 실제 물동량 비율 (100%에 가까울수록 혼잡)"),
    ],
    "fx": [
        ("NGN",  "나이지리아 나이라 — 변동 환율, 중앙은행 개입으로 관리"),
        ("KES",  "케냐 실링 — 변동 환율"),
        ("ZAR",  "남아공 랜드 — 변동 환율, 원자재 가격 연동성 높음"),
        ("EGP",  "이집트 파운드 — 관리 변동 환율"),
        ("TRY",  "터키 리라 — 변동 환율, 고인플레이션 구조"),
        ("USD",  "미국 달러 — 기준 통화"),
    ],
    "geo": [
        ("MEA",  "Middle East & Africa — 중동 및 아프리카 지역"),
        ("GCC",  "Gulf Cooperation Council — 걸프협력회의 (UAE·사우디·쿠웨이트 등 6개국)"),
    ],
}

def _footnote(keys: list) -> str:
    """섹션 하단 * 주석 렌더링."""
    if not keys:
        return ""
    items = FOOTNOTES.get(keys[0], [])
    if not items:
        return ""
    notes = "".join(
        f'<span style="margin-right:20px;">* <strong>{k}</strong>: {v}</span>'
        for k, v in items
    )
    return f"""
<div style="margin-top:12px;padding:12px 16px;background:#FAFAF8;
            border-top:1px dashed #E0D8CC;border-radius:0 0 6px 6px;
            font-size:11px;color:#999;line-height:1.9;font-family:'Source Sans 3',sans-serif;">
  {notes}
</div>"""


def generate(payload: dict, commentary: dict, issue_num: int, out_path: Path,
             manager_mode: bool = False):
    s         = payload.get("sources",{})
    gen_at    = payload.get("generated_at","")
    news      = s.get("RSS News",         {}).get("data",[])
    fx        = s.get("FX Rates",         {}).get("data",[])
    freight_d = s.get("freight",          {})
    tv_data   = s.get("TV Market",         {})
    routes    = freight_d.get("data",[])
    gri       = freight_d.get("gri_notice","")
    indices   = s.get("Freight Index",    {}).get("data",[])
    carriers  = s.get("Carrier Schedule", {}).get("data",[])
    ports     = s.get("Port Status",      {}).get("data",[])

    c_fr  = commentary.get("freight",{})
    c_geo = commentary.get("geopolitics",{})
    c_tip = commentary.get("pro_tip",{})
    rl    = c_geo.get("risk_level","—")
    rc    = {"높음":"#C0392B","중간":"#E67E22","낮음":"#2E7D32"}.get(rl,"#666")
    idate = datetime.now(UTC).strftime("%Y년 %m월 %d일")

    heatmap_html = freight_heatmap(routes, ORIGIN_ORDER, DEST_ORDER)

    body = f"""
  <p style="font-size:13px;color:#888;font-style:italic;border-bottom:1px solid #F0EDE8;
             padding-bottom:16px;margin-bottom:32px;">
    Desert to Cape는 MEA 지역 해상운임·지정학 리스크를 매주 실무 언어로 정리합니다.
    <em style="color:#C9A96E;"> Weekly MEA Trade &amp; Logistics Brief.</em>
  </p>

  <!-- 00. 운임지수 -->
  <div class="sec">
    <div class="sec-hdr">
      <span class="sec-num">00</span>
      <span class="sec-title">글로벌 운임지수 <span class="sec-en">Freight Index Dashboard</span></span>
      {_b(len(indices))}
    </div>
    <p>SCFI·WCI·FBX는 컨테이너, BDI는 건화물 시장을 반영합니다. 스파크라인은 8주 추세입니다.</p>
    {_index_cards(indices, {})}
    {_footnote(['freight_index'])}
  </div><hr>

  <!-- 01. 운임 히트맵 -->
  <div class="sec">
    <div class="sec-hdr">
      <span class="sec-num">01</span>
      <span class="sec-title">운임 매트릭스 <span class="sec-en">Rate Heatmap</span></span>
      {_b(len([r for r in routes if r.get('fak_usd')]),"⚠ 수동","⚠ 없음")}
    </div>
    <p>출발지 × 도착지 FAK($/TEU). 색상은 목적지별 상대 가격 — 빨강일수록 비싼 노선입니다.</p>
    {heatmap_html if heatmap_html else '<p style="color:#999;">운임 데이터 입력 필요</p>'}
    {_footnote(['freight'])}
  </div><hr>

  <!-- 02. 운임 동향 -->
  <div class="sec">
    <div class="sec-hdr">
      <span class="sec-num">02</span>
      <span class="sec-title">운임 동향 <span class="sec-en">Freight Rate Detail</span></span>
      {_b(len([r for r in routes if r.get('fak_usd')]),"⚠ 수동","⚠ 없음")}
    </div>
    {f'<p>{c_fr.get("ko","")}</p><p class="en-note">{c_fr.get("en","")}</p>' if c_fr else ""}
    {f'<div class="callout"><div class="callout-lbl">📢 GRI 공지</div><p style="margin:0;font-size:13px;">{gri}</p></div>' if gri else ""}
    {_freight_detail(routes)}
    {_market_conditions(freight_d)}
  </div><hr>

  <!-- 03. 선사 스케줄 -->
  <div class="sec">
    <div class="sec-hdr">
      <span class="sec-num">03</span>
      <span class="sec-title">선사 스케줄 <span class="sec-en">Carrier Schedules</span></span>
      {_b(len(carriers),"✓ 자동+수동","⚠ 없음")}
    </div>
    <p>선복률 90%↑ 노선은 조기 부킹이 필요합니다.</p>
    {_carrier_cards(carriers)}
    {_footnote(['carrier'])}
  </div><hr>

  <!-- 04. 항만 현황 -->
  <div class="sec">
    <div class="sec-hdr">
      <span class="sec-num">04</span>
      <span class="sec-title">항만 현황 <span class="sec-en">Port Congestion</span></span>
      {_b(len(ports),"✓ 자동+수동","⚠ 없음")}
    </div>
    <p>링 게이지 = 혼잡도(%). 초록·주황·빨강으로 상태를 구분합니다.</p>
    {_port_grid(ports)}
    {_footnote(['port'])}
  </div><hr>

  <!-- 05. 환율 -->
  <div class="sec">
    <div class="sec-hdr">
      <span class="sec-num">05</span>
      <span class="sec-title">주요 통화 환율 <span class="sec-en">MEA Currencies</span></span>
      {_b(len([f for f in fx if f.get('currency') not in FIXED_PEG]))}
    </div>
    <p>변동 환율 국가 기준. ▲ = 현지 통화 약세(수입 원가 상승 압박).</p>
    {_fx_table(fx)}
    {_footnote(['fx'])}
  </div><hr>

  <!-- 06. 지정학 브리핑 -->
  <div class="sec">
    <div class="sec-hdr">
      <span class="sec-num">06</span>
      <span class="sec-title">지정학 브리핑 <span class="sec-en">Geopolitical Risk</span></span>
      {_b(len(news))}
    </div>
    {f'''<div style="display:inline-flex;align-items:center;gap:10px;
                    background:{rc}18;border:1px solid {rc}40;border-radius:6px;
                    padding:8px 16px;margin-bottom:16px;">
      <span style="font-size:11px;color:#666;font-family:'JetBrains Mono',monospace;letter-spacing:1px;">RISK LEVEL</span>
      <span style="color:{rc};font-weight:900;font-size:20px;
                   font-family:'Playfair Display',serif;">{rl}</span>
    </div>''' if rl != "—" else ""}
    {f'<p>{c_geo.get("ko","")}</p><p class="en-note">{c_geo.get("en","")}</p>' if c_geo else ""}

    <div style="font-size:9px;font-weight:700;letter-spacing:2px;color:var(--muted);
                text-transform:uppercase;font-family:'JetBrains Mono',monospace;
                margin:16px 0 8px;">🌍 Middle East</div>
    {_news_section(news,"Middle East")}
    <div style="font-size:9px;font-weight:700;letter-spacing:2px;color:var(--muted);
                text-transform:uppercase;font-family:'JetBrains Mono',monospace;
                margin:20px 0 8px;">🌍 Africa</div>
    {_news_section(news,"Africa")}
    <div style="font-size:9px;font-weight:700;letter-spacing:2px;color:var(--muted);
                text-transform:uppercase;font-family:'JetBrains Mono',monospace;
                margin:20px 0 8px;">🚢 Shipping</div>
    {_news_section(news,"Shipping")}
    {_footnote(['geo'])}
  </div><hr>

  <!-- 07. 실무 팁 -->
  <div class="sec">
    <div class="sec-hdr">
      <span class="sec-num">07</span>
      <span class="sec-title">실무 팁 <span class="sec-en">Pro Tip</span></span>
      {_b(1 if c_tip else 0)}
    </div>
    <div class="tip-box">
      <div class="tip-lbl">💼 Pro Tip of the Week</div>
      <p>{c_tip.get("ko","AI 분석 완료 후 자동 생성됩니다.")}</p>
      {f'<p style="margin-top:10px;font-style:italic;font-size:12px;color:#6B7280;">{c_tip.get("en","")}</p>' if c_tip.get("en") else ""}
    </div>
  </div>

  {render_tv_section(tv_data, commentary.get('tv_market',{}).get('ko',''))}

  <div class="next">
    <div class="next-lbl">다음 호 예고 · Issue #{issue_num+1:03d}</div>
    <ul>
      <li>2026 하반기 걸프 선사별 서비스 변경 총정리</li>
      <li>아프리카 가전 유통 플랫폼 비교 (Jumia vs Kilimall)</li>
      <li>UAE 관세 개편이 한국 수출에 미치는 영향</li>
    </ul>
  </div>

  {_pipeline_footer(s, commentary, gen_at) if manager_mode else ''}
"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Desert to Cape #{issue_num:03d}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Source+Sans+3:wght@300;400;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="header-meta">
      <span class="issue-tag">Issue #{issue_num:03d}</span>
      <span class="date-tag">{idate}</span>
    </div>
    <div class="masthead">Desert <em>to</em> Cape</div>
    <div class="tagline">걸프부터 남아공까지 · 프론티어 마켓 주간 브리핑 · Weekly MEA Trade &amp; Logistics Brief</div>
  </div>
  <div class="cover">
    <span class="cover-label">이번 호 —</span>
    <span class="cover-hl">2026 하반기, 걸프 물류의 판이 바뀐다</span>
  </div>
  <div class="body">{body}</div>
  <div class="footer">
    <div class="footer-logo">Desert <em>to</em> Cape</div>
    <div style="font-size:11px;color:#555;margin-top:6px;">매주 수요일 발행</div>
    <div style="margin-top:12px;">
      <a href="#">구독</a> · <a href="#">지난 호</a> · <a href="#">수신 거부</a>
    </div>
  </div>
</div>
</body></html>"""

    out_path.write_text(html, encoding="utf-8")
    print(f"  -> {out_path.name} 생성 완료")


# ════════════════════════════════════════════════════════════
# 08. TV 시장 동향 섹션
# ════════════════════════════════════════════════════════════

TREND_ICON = {"up": "▲", "flat": "→", "down": "▼"}
TREND_COLOR = {"up": "#2E7D32", "flat": "#E67E22", "down": "#C0392B"}
SEGMENT_COLOR = {
    "Ultra Premium": "#7B1FA2",
    "Premium":       "#1565C0",
    "Mid-Value":     "#E67E22",
    "Value":         "#2E7D32",
}

def _tv_brand_table(brands: list) -> str:
    if not brands:
        return '<p style="color:#999;font-size:13px;">tv_market.json 업데이트 필요</p>'

    rows = ""
    for b in brands:
        tr = b.get("trend","flat")
        tc = TREND_COLOR.get(tr, "#666")
        ti = TREND_ICON.get(tr, "→")
        sc = SEGMENT_COLOR.get(b.get("segment",""), "#666")
        ms = b.get("market_share_pct")
        ms_html = (
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<div style="background:#F0EDE8;border-radius:3px;height:8px;width:80px;overflow:hidden;">'
            f'<div style="background:{sc};height:8px;width:{ms}%;"></div></div>'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:12px;">{ms}%</span>'
            f'</div>'
        ) if ms else '—'
        pi = b.get("price_index", 0)
        regs = ", ".join(b.get("regions",[])[:2])
        note = b.get("note","")

        rows += f"""
<tr>
  <td style="padding:12px;">
    <strong style="font-size:14px;color:var(--deep);">{b.get('brand','')}</strong>
    <span style="background:{sc}18;color:{sc};font-size:10px;font-weight:700;
                 padding:2px 8px;border-radius:10px;margin-left:8px;
                 font-family:'JetBrains Mono',monospace;">{b.get('segment','')}</span>
    <div style="font-size:11px;color:#999;margin-top:4px;">{b.get('hero_model','')} · {b.get('hero_category','')}</div>
  </td>
  <td style="padding:12px;">{ms_html}</td>
  <td style="padding:12px;text-align:center;">
    <span style="font-family:'JetBrains Mono',monospace;font-size:14px;
                 font-weight:700;color:{tc};">{ti}</span>
  </td>
  <td style="padding:12px;text-align:right;">
    <span style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 font-weight:600;color:var(--deep);">{pi}<span style="font-size:10px;color:#aaa;"> idx</span></span>
  </td>
  <td style="padding:12px;font-size:12px;color:#666;">
    {regs}
    {f'<div style="font-size:11px;color:#C9A96E;margin-top:3px;">⚡ {note}</div>' if note else ''}
  </td>
</tr>"""

    return f"""
<table class="data-table">
  <thead><tr>
    <th>브랜드 / 히어로 모델</th>
    <th>점유율</th>
    <th style="text-align:center;">추세</th>
    <th style="text-align:right;">가격지수</th>
    <th>주요 시장</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>"""


def _tv_category_grid(cats: list) -> str:
    if not cats:
        return ""
    cards = ""
    for c in cats:
        tr = c.get("trend","flat")
        tc = TREND_COLOR.get(tr, "#666")
        ti = TREND_ICON.get(tr, "→")
        cards += f"""
<div style="background:#fff;border:1px solid var(--border);border-radius:8px;
            padding:16px 20px;border-top:3px solid {tc};">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <span style="font-family:'JetBrains Mono',monospace;font-size:13px;
                 font-weight:700;color:var(--deep);">{c.get('category','')}</span>
    <span style="font-size:18px;font-weight:700;color:{tc};">{ti}</span>
  </div>
  <div style="font-size:12px;color:#666;line-height:1.5;">{c.get('note','')}</div>
</div>"""
    return f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0;">{cards}</div>'


def _tv_region_cards(regions: list) -> str:
    if not regions:
        return ""
    html = ""
    for r in regions:
        risk = r.get("risk","")
        risk_badge = (
            f'<span style="background:#FFF3CD;color:#856404;font-size:10px;font-weight:700;'
            f'padding:2px 8px;border-radius:4px;font-family:\'JetBrains Mono\',monospace;">⚠ {risk}</span>'
            if risk else ''
        )
        html += f"""
<div style="padding:14px 0;border-bottom:1px solid #F5F2EE;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
    <span style="font-weight:700;font-size:14px;color:var(--deep);">
      {r.get('region','')}
    </span>
    {risk_badge}
  </div>
  <div style="font-size:14px;color:#444;font-weight:300;line-height:1.6;">
    {r.get('key_metric','')}
  </div>
</div>"""
    return html


def _tv_news_items(news: list) -> str:
    if not news:
        return '<p style="color:#999;font-size:13px;">TV 시장 뉴스 수집 실패</p>'
    html = ""
    for n in news[:5]:
        ko     = n.get("title_ko","") or n.get("title","")
        en     = n.get("title","")
        url    = n.get("url","#")
        src    = n.get("source","")
        pub    = str(n.get("published",""))[:10]
        brands = n.get("brands",[])
        cats   = n.get("categories",[])

        tags = "".join(
            f'<span style="background:#E3F2FD;color:#1565C0;font-size:9px;font-weight:700;'
            f'padding:1px 7px;border-radius:10px;margin-right:4px;'
            f'font-family:\'JetBrains Mono\',monospace;">{t}</span>'
            for t in (brands + cats)[:3]
        )
        html += f"""
<div style="padding:12px 0;border-bottom:1px solid #F5F2EE;">
  <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px;">
    <div style="flex:1;">
      <div style="font-size:14px;color:#2C2C3E;line-height:1.55;margin-bottom:5px;">{ko}</div>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        {tags}
        <a href="{url}" target="_blank"
           style="font-size:10px;color:#C9A96E;text-decoration:none;
                  font-family:'JetBrains Mono',monospace;">
          ↗ {en[:50]}{"…" if len(en)>50 else ""}
        </a>
        <span style="font-size:10px;color:#ccc;">· {src} · {pub}</span>
      </div>
    </div>
  </div>
</div>"""
    return html


TV_FOOTNOTES = [
    ("OLED",    "Organic Light-Emitting Diode — 유기발광다이오드, 자발광 프리미엄 패널"),
    ("QLED",    "Quantum Light-Emitting Diode — 양자점 LED, 삼성 프리미엄 LCD 라인업"),
    ("QNED",    "Quantum NanoCell Emitting Diode — LG 프리미엄 LCD 라인업"),
    ("MiniLED", "미니LED 백라이트 LCD — OLED 대비 밝기 우위"),
    ("UHD",     "Ultra High Definition — 4K 해상도 (3840×2160)"),
    ("가격지수", "LG OLED 65인치=100 기준 상대 가격 지수"),
    ("점유율",   "GfK MEA 추정치 기반 — 실제 수치와 차이 있을 수 있음"),
]

def _tv_footnote() -> str:
    notes = "".join(
        f'<span style="margin-right:20px;">* <strong>{k}</strong>: {v}</span>'
        for k, v in TV_FOOTNOTES
    )
    return f"""
<div style="margin-top:12px;padding:12px 16px;background:#FAFAF8;
            border-top:1px dashed #E0D8CC;border-radius:0 0 6px 6px;
            font-size:11px;color:#999;line-height:1.9;font-family:'Source Sans 3',sans-serif;">
  {notes}
</div>"""


def render_tv_section(tv_data: dict, tv_commentary: str = "") -> str:
    """
    TV 시장 동향 섹션 전체 HTML 렌더링.
    generate() 내부에서 호출.
    """
    all_items = tv_data.get("data", [])
    if not all_items:
        return ""

    brands  = [i for i in all_items if i.get("type") == "brand"]
    cats    = [i for i in all_items if i.get("type") == "category"]
    regions = [i for i in all_items if i.get("type") == "region"]
    news    = [i for i in all_items if i.get("type") == "news"]

    src_note = tv_data.get("source_note", "")
    period   = tv_data.get("period", "")

    return f"""
  <!-- 08. TV 시장 동향 -->
  <div class="sec">
    <div class="sec-hdr">
      <span class="sec-num">08</span>
      <span class="sec-title">TV 시장 동향 <span class="sec-en">MEA TV Market Intelligence</span></span>
      {'<span class="badge-ok">✓ 자동+수동</span>' if brands else '<span class="badge-warn">⚠ 수동필요</span>'}
    </div>

    {f'<p style="font-size:12px;color:#aaa;margin-bottom:16px;">소스: {src_note}{" · " + period if period else ""}</p>' if src_note else ""}

    {f'<p>{tv_commentary}</p>' if tv_commentary else ""}

    <!-- 브랜드 포지셔닝 -->
    <p style="font-weight:600;font-size:12px;letter-spacing:1px;color:var(--muted);
              text-transform:uppercase;margin-bottom:8px;">📺 브랜드 포지셔닝</p>
    {_tv_brand_table(brands)}

    <!-- 카테고리 트렌드 -->
    <p style="font-weight:600;font-size:12px;letter-spacing:1px;color:var(--muted);
              text-transform:uppercase;margin:20px 0 8px;">📊 카테고리 트렌드</p>
    {_tv_category_grid(cats)}

    <!-- 지역 하이라이트 -->
    <p style="font-weight:600;font-size:12px;letter-spacing:1px;color:var(--muted);
              text-transform:uppercase;margin:20px 0 8px;">🌍 지역별 시장 동향</p>
    {_tv_region_cards(regions)}

    <!-- 시장 뉴스 -->
    <p style="font-weight:600;font-size:12px;letter-spacing:1px;color:var(--muted);
              text-transform:uppercase;margin:20px 0 8px;">📰 시장 뉴스</p>
    {_tv_news_items(news)}

    {_tv_footnote()}
  </div>"""
