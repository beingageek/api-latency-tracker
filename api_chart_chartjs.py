"""
API Call Time HTML Report Generator
Reads a CSV with EventDate/EventComments columns and writes a single self-contained
HTML file with interactive Chart.js charts for:
  1. Daily Median response time by API type
  2. Daily Minimum response time by API type
  3. Daily Maximum response time by API type
  4. Monthly Median response time by API type
  5. Year-over-Year same-month comparison (one chart per API, tabbed)
  6. Daily Median split by 6-hour time frames (one chart per time frame, all APIs, tabbed)

Usage:
    pip install pandas
    python api_chart_chartjs.py <path_to_csv> [output.html]
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ── Colour palettes ──────────────────────────────────────────────────────────

API_PALETTE = [
    "#00e5ff", "#69ff6e", "#ffb347", "#ff79c6",
    "#bd93f9", "#50fa7b", "#ff5555", "#f1fa8c",
    "#8be9fd", "#ffb86c", "#ff6e6e", "#cba6f7",
]

TF_COLORS = {
    "12AM-6AM": "#7c4dff",
    "6AM-12PM": "#00bcd4",
    "12PM-6PM": "#ff9800",
    "6PM-12AM": "#e91e63",
}

TIMEFRAMES = ["12AM-6AM", "6AM-12PM", "12PM-6PM", "6PM-12AM"]


# ── Data loading & parsing ────────────────────────────────────────────────────

def load_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()

    df["EventDate"] = pd.to_datetime(df["EventDate"], errors="coerce")
    df = df.dropna(subset=["EventDate"])

    pattern = r"(API\s+\d+)\s+time taken millis\s*=\s*(\d+)"
    extracted = df["EventComments"].str.extract(pattern, flags=re.IGNORECASE)
    df["api_type"] = extracted[0].str.strip()
    df["millis"]   = pd.to_numeric(extracted[1], errors="coerce")
    df = df.dropna(subset=["api_type", "millis"])

    df["date"]      = df["EventDate"].dt.date
    df["month"]     = df["EventDate"].dt.to_period("M")
    df["month_num"] = df["EventDate"].dt.month
    df["year"]      = df["EventDate"].dt.year
    df["hour"]      = df["EventDate"].dt.hour

    def bucket(h):
        if   0 <= h <  6: return "12AM-6AM"
        elif 6 <= h < 12: return "6AM-12PM"
        elif 12 <= h < 18: return "12PM-6PM"
        else:              return "6PM-12AM"

    df["timeframe"] = df["hour"].apply(bucket)
    return df


# ── Aggregation helpers ───────────────────────────────────────────────────────

def daily_pivot(df: pd.DataFrame, stat: str) -> pd.DataFrame:
    pivot = (
        df.groupby(["date", "api_type"])["millis"]
        .agg(stat)
        .unstack("api_type")
    )
    pivot.index = pd.to_datetime(pivot.index)
    return pivot


def monthly_pivot(df: pd.DataFrame) -> pd.DataFrame:
    pivot = (
        df.groupby(["month", "api_type"])["millis"]
        .median()
        .unstack("api_type")
    )
    pivot.index = pivot.index.to_timestamp()
    return pivot


def yoy_data(df: pd.DataFrame):
    apis  = sorted(df["api_type"].unique())
    years = sorted(df["year"].unique())
    result = {}
    for api in apis:
        sub = df[df["api_type"] == api]
        agg = (
            sub.groupby(["year", "month_num"])["millis"]
            .median()
            .unstack("year")
            .reindex(range(1, 13))
        )
        result[api] = {}
        for yr in years:
            if yr in agg.columns:
                result[api][int(yr)] = [
                    round(v, 1) if pd.notna(v) else None
                    for v in agg[yr].tolist()
                ]
    return result, [int(y) for y in years]


def timeframe_data(df: pd.DataFrame) -> dict:
    """Returns {timeframe: {api: {labels: [...], values: [...]}}}
    All series share the same continuous full date range so lines are
    unbroken — missing days become null (gaps only where data truly absent)."""
    apis = sorted(df["api_type"].unique())

    # Full date spine covering the entire dataset
    all_dates = pd.date_range(df["EventDate"].min().normalize(),
                              df["EventDate"].max().normalize(), freq="D")
    date_labels = [d.strftime("%Y-%m-%d") for d in all_dates]

    result = {tf: {} for tf in TIMEFRAMES}

    for api in apis:
        sub = df[df["api_type"] == api]
        pivot = (
            sub.groupby(["date", "timeframe"])["millis"]
            .median()
            .unstack("timeframe")
            .reindex(columns=TIMEFRAMES)
        )
        pivot.index = pd.to_datetime(pivot.index)
        # Reindex to the full date spine — missing days become NaN → null in JSON
        pivot = pivot.reindex(all_dates)

        for tf in TIMEFRAMES:
            values = (
                pivot[tf].tolist() if tf in pivot.columns
                else [None] * len(all_dates)
            )
            result[tf][api] = {
                "labels": date_labels,
                "values": [round(v, 1) if pd.notna(v) else None for v in values],
            }

    return result


# ── Chart.js dataset builders ─────────────────────────────────────────────────

def pivot_to_chartjs(pivot: pd.DataFrame, api_colors: dict) -> dict:
    labels = [d.strftime("%Y-%m-%d") for d in pivot.index]
    datasets = []
    for col in pivot.columns:
        color = api_colors.get(col, "#aaaaaa")
        datasets.append({
            "label":            col,
            "data":             [round(v, 1) if pd.notna(v) else None for v in pivot[col]],
            "borderColor":      color,
            "backgroundColor":  color + "22",
            "borderWidth":      2,
            "pointRadius":      1,
            "pointHoverRadius": 5,
            "tension":          0.3,
            "spanGaps":         False,
        })
    return {"labels": labels, "datasets": datasets}


def monthly_to_chartjs(pivot: pd.DataFrame, api_colors: dict) -> dict:
    labels = [d.strftime("%b %Y") for d in pivot.index]
    datasets = []
    for col in pivot.columns:
        color = api_colors.get(col, "#aaaaaa")
        datasets.append({
            "label":            col,
            "data":             [round(v, 1) if pd.notna(v) else None for v in pivot[col]],
            "borderColor":      color,
            "backgroundColor":  color + "22",
            "borderWidth":      2.5,
            "pointRadius":      4,
            "pointHoverRadius": 7,
            "tension":          0.3,
            "spanGaps":         False,
        })
    return {"labels": labels, "datasets": datasets}


def build_json(df: pd.DataFrame, api_colors: dict) -> dict:
    yoy, years = yoy_data(df)
    return {
        "api_colors": api_colors,
        "daily": {
            "median": pivot_to_chartjs(daily_pivot(df, "median"), api_colors),
            "min":    pivot_to_chartjs(daily_pivot(df, "min"),    api_colors),
            "max":    pivot_to_chartjs(daily_pivot(df, "max"),    api_colors),
        },
        "monthly":   monthly_to_chartjs(monthly_pivot(df), api_colors),
        "yoy":       yoy,
        "yoy_years": years,
        "timeframe": timeframe_data(df),
    }


# ── HTML template ─────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>API Performance Report</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/hammer.js/2.0.8/hammer.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-zoom/2.0.1/chartjs-plugin-zoom.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&display=swap" rel="stylesheet"/>
<style>
:root{
  --bg:#080b12;--surf:#0e1219;--surf2:#141a24;
  --bdr:#1e2736;--accent:#00e5ff;--accent2:#ff6b6b;
  --text:#cdd6f0;--muted:#5a6882;--head:#eef2ff;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:'DM Mono',monospace;font-size:13px;line-height:1.6}
body::before{content:'';position:fixed;inset:0;opacity:.3;pointer-events:none;z-index:0;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.05'/%3E%3C/svg%3E")}

/* header */
header{position:relative;padding:52px 48px 36px;border-bottom:1px solid var(--bdr);overflow:hidden;z-index:1}
header::after{content:'';position:absolute;top:-80px;right:-80px;width:380px;height:380px;
  background:radial-gradient(circle,rgba(0,229,255,.07) 0%,transparent 70%);pointer-events:none}
.tag{display:inline-block;font-size:10px;letter-spacing:.15em;text-transform:uppercase;
  color:var(--accent);border:1px solid rgba(0,229,255,.3);padding:3px 10px;border-radius:2px;margin-bottom:14px}
h1{font-family:'Syne',sans-serif;font-size:clamp(26px,4vw,50px);font-weight:800;
   color:var(--head);letter-spacing:-.02em;line-height:1.1;margin-bottom:6px}
h1 span{color:var(--accent)}
.sub{color:var(--muted);font-size:12px}

/* meta bar */
.meta{display:flex;gap:40px;flex-wrap:wrap;align-items:center;
  margin:28px 48px;padding:16px 24px;background:var(--surf);
  border:1px solid var(--bdr);border-radius:4px;position:relative;z-index:1}
.st{display:flex;flex-direction:column;gap:2px}
.st-l{color:var(--muted);font-size:10px;letter-spacing:.1em;text-transform:uppercase}
.st-v{color:var(--head);font-size:18px;font-family:'Syne',sans-serif}

/* nav */
nav{display:flex;gap:8px;flex-wrap:wrap;margin:0 48px 28px;position:relative;z-index:1}
.pill{padding:6px 14px;border:1px solid var(--bdr);border-radius:2px;cursor:pointer;
  font-family:'DM Mono',monospace;font-size:11px;color:var(--muted);
  background:var(--surf);transition:all .15s;user-select:none}
.pill:hover{border-color:var(--accent);color:var(--accent)}
.pill.on{border-color:var(--accent);color:var(--accent);background:rgba(0,229,255,.06)}

/* sections */
.sec{display:none;padding:0 48px 56px;position:relative;z-index:1;animation:fu .3s ease both}
.sec.on{display:block}
@keyframes fu{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
.sec-hd{display:flex;align-items:baseline;gap:16px;
  margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--bdr)}
.sec-title{font-family:'Syne',sans-serif;font-size:19px;font-weight:700;color:var(--head)}
.sec-desc{color:var(--muted);font-size:11px}

/* legend */
.legend{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:18px}
.li{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--muted)}
.ld{width:9px;height:9px;border-radius:50%;flex-shrink:0}

/* grid */
.grid{display:grid;gap:20px}
.g1{grid-template-columns:1fr}
.g2{grid-template-columns:repeat(auto-fit,minmax(520px,1fr))}

/* card */
.card{background:var(--surf);border:1px solid var(--bdr);border-radius:4px;
  padding:20px 24px 16px;transition:border-color .2s}
.card:hover{border-color:#2e3a52}
.ct{font-size:11px;letter-spacing:.08em;text-transform:uppercase;
  color:var(--muted);margin-bottom:14px}
.ct span{color:var(--accent)}
.cw{position:relative;height:300px}
.cw.tall{height:340px}
.cw.yoy-cw{position:relative;height:400px;width:100%}

/* sub-tabs */
.stabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:20px}
.stab{padding:4px 12px;border:1px solid var(--bdr);border-radius:2px;cursor:pointer;
  font-size:11px;color:var(--muted);background:transparent;transition:all .15s;user-select:none}
.stab:hover{color:var(--text);border-color:#2e3a52}
.stab.on{color:var(--head);border-color:var(--accent2);background:rgba(255,107,107,.07)}

.hint{color:var(--muted);font-size:10px;margin-top:8px;text-align:right}

/* API filter bar */
#filter-bar{
  display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  margin:0 48px 24px;padding:12px 18px;
  background:var(--surf);border:1px solid var(--bdr);border-radius:4px;
  position:sticky;top:0;z-index:50;backdrop-filter:blur(8px);
}
#filter-bar .fb-label{
  font-size:10px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--muted);white-space:nowrap;margin-right:4px;
}
.api-toggle{
  display:flex;align-items:center;gap:6px;
  padding:4px 12px 4px 8px;border-radius:2px;cursor:pointer;
  border:1px solid var(--bdr);background:transparent;
  font-family:'DM Mono',monospace;font-size:11px;color:var(--text);
  transition:all .15s;user-select:none;
}
.api-toggle:hover{border-color:#3a4560}
.api-toggle.off{opacity:.35;border-color:var(--bdr) !important}
.api-toggle .tog-dot{width:9px;height:9px;border-radius:50%;flex-shrink:0}
.fb-divider{width:1px;height:20px;background:var(--bdr);margin:0 4px}
.fb-action{
  padding:4px 10px;border:1px solid var(--bdr);border-radius:2px;cursor:pointer;
  font-family:'DM Mono',monospace;font-size:10px;color:var(--muted);
  background:transparent;transition:all .15s;white-space:nowrap;
}
.fb-action:hover{color:var(--accent);border-color:var(--accent)}

footer{padding:28px 48px;border-top:1px solid var(--bdr);color:var(--muted);
  font-size:11px;display:flex;justify-content:space-between;position:relative;z-index:1}

::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--bdr);border-radius:3px}
</style>
</head>
<body>

<header>
  <div class="tag">Performance Analytics</div>
  <h1>API <span>Response</span> Times</h1>
  <p class="sub">Generated: __GENERATED_AT__ &nbsp;|&nbsp; Source: __SOURCE__</p>
</header>

<div class="meta">
  <div class="st"><span class="st-l">Records</span><span class="st-v">__RECORDS__</span></div>
  <div class="st"><span class="st-l">API Types</span><span class="st-v">__APIS__</span></div>
  <div class="st"><span class="st-l">Date Range</span><span class="st-v">__RANGE__</span></div>
  <div class="st"><span class="st-l">Span</span><span class="st-v">__SPAN__</span></div>
</div>

<nav>
  <div class="pill on"  data-s="daily">Daily Stats</div>
  <div class="pill"     data-s="monthly">Monthly Median</div>
  <div class="pill"     data-s="yoy">Year-over-Year</div>
  <div class="pill"     data-s="tf">Time Frames</div>
</nav>

<!-- ── API FILTER BAR ── -->
<div id="filter-bar">
  <span class="fb-label">Filter APIs</span>
  <div id="api-toggles"></div>
  <div class="fb-divider"></div>
  <div class="fb-action" id="fb-all">Show all</div>
  <div class="fb-action" id="fb-none">Hide all</div>
</div>

<!-- ── DAILY ── -->
<div class="sec on" id="s-daily">
  <div class="sec-hd">
    <div class="sec-title">Daily Statistics</div>
    <div class="sec-desc">Median · Min · Max per API per day &nbsp;|&nbsp; scroll to zoom, drag to pan</div>
  </div>
  <div class="legend" id="leg-daily"></div>
  <div class="grid g1">
    <div class="card">
      <div class="ct"><span>Median</span> &nbsp;daily response time (ms)</div>
      <div class="cw"><canvas id="c-med"></canvas></div>
    </div>
    <div class="card">
      <div class="ct"><span>Minimum</span> &nbsp;daily response time (ms)</div>
      <div class="cw"><canvas id="c-min"></canvas></div>
    </div>
    <div class="card">
      <div class="ct"><span>Maximum</span> &nbsp;daily response time (ms)</div>
      <div class="cw"><canvas id="c-max"></canvas></div>
    </div>
  </div>
  <p class="hint">Tip: scroll to zoom &nbsp;·&nbsp; drag to pan &nbsp;·&nbsp; double-click to reset</p>
</div>

<!-- ── MONTHLY ── -->
<div class="sec" id="s-monthly">
  <div class="sec-hd">
    <div class="sec-title">Monthly Median</div>
    <div class="sec-desc">Median response time per calendar month</div>
  </div>
  <div class="legend" id="leg-monthly"></div>
  <div class="grid g1">
    <div class="card">
      <div class="ct"><span>Monthly</span> &nbsp;median response time (ms)</div>
      <div class="cw tall"><canvas id="c-monthly"></canvas></div>
    </div>
  </div>
</div>

<!-- ── YoY ── -->
<div class="sec" id="s-yoy">
  <div class="sec-hd">
    <div class="sec-title">Year-over-Year</div>
    <div class="sec-desc">Same month across years — Jan 2023 vs Jan 2024 vs Jan 2025 …</div>
  </div>
  <div class="stabs" id="tabs-yoy"></div>
  <div class="legend" id="leg-yoy"></div>
  <div class="grid g1" id="grid-yoy"></div>
</div>

<!-- ── TIMEFRAME ── -->
<div class="sec" id="s-tf">
  <div class="sec-hd">
    <div class="sec-title">Daily by Time Frame</div>
    <div class="sec-desc">Median response time grouped by 6-hour windows</div>
  </div>
  <div class="stabs" id="tabs-tf"></div>
  <div class="legend" id="leg-tf"></div>
  <div class="grid g1" id="grid-tf"></div>
  <p class="hint">Tip: scroll to zoom &nbsp;·&nbsp; drag to pan &nbsp;·&nbsp; double-click to reset</p>
</div>

<footer>
  <span>API Performance Report</span>
  <span>__RECORDS__ records across __SPAN__</span>
</footer>

<script>
// ── Embedded data ─────────────────────────────────────────────────────────
const D = __JSON_DATA__;
const TF_COLORS = __TF_COLORS__;
const TFS = __TF_ORDER__;

// ── Chart.js global defaults ──────────────────────────────────────────────
Chart.defaults.color       = '#7b82a0';
Chart.defaults.borderColor = '#1e2736';
Chart.defaults.font.family = "'DM Mono',monospace";
Chart.defaults.font.size   = 11;

function msLabel(v) { return v >= 1000 ? (v/1000).toFixed(2)+'s' : v+'ms'; }

function baseOpts(zoom = true) {
  const o = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 500 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#141a24', borderColor: '#1e2736', borderWidth: 1,
        titleColor: '#eef2ff', bodyColor: '#cdd6f0', padding: 10,
        callbacks: { label: c => ` ${c.dataset.label}: ${c.parsed.y != null ? msLabel(c.parsed.y) : 'N/A'}` }
      },
    },
    scales: {
      x: { grid:{color:'#1e2736'}, ticks:{maxTicksLimit:18,maxRotation:40} },
      y: { grid:{color:'#1e2736'}, ticks:{callback: v => msLabel(v)} },
    },
  };
  if (zoom) {
    o.plugins.zoom = {
      pan:  { enabled:true, mode:'x' },
      zoom: { wheel:{enabled:true}, pinch:{enabled:true}, mode:'x' },
    };
  }
  return o;
}


// ── Global API filter state ───────────────────────────────────────────────
const allApis = Object.keys(D.api_colors);
const hidden  = new Set();   // APIs currently hidden
const allCharts = [];        // every Chart instance registered here

function registerChart(ch) { allCharts.push(ch); return ch; }

function applyFilter() {
  allCharts.forEach(ch => {
    ch.data.datasets.forEach(ds => {
      // Match dataset label against hidden set (works for API-labelled datasets)
      ds.hidden = hidden.has(ds.label);
    });
    ch.update('none');
  });
  // Sync toggle button states
  document.querySelectorAll('.api-toggle').forEach(btn => {
    btn.classList.toggle('off', hidden.has(btn.dataset.api));
  });
}

// Build filter bar toggles
(function buildFilterBar() {
  const wrap = document.getElementById('api-toggles');
  wrap.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap';
  allApis.forEach(api => {
    const btn = document.createElement('div');
    btn.className = 'api-toggle';
    btn.dataset.api = api;
    btn.innerHTML = `<div class="tog-dot" style="background:${D.api_colors[api]}"></div>${api}`;
    btn.addEventListener('click', () => {
      if (hidden.has(api)) hidden.delete(api); else hidden.add(api);
      applyFilter();
    });
    wrap.appendChild(btn);
  });

  document.getElementById('fb-all').addEventListener('click', () => {
    hidden.clear(); applyFilter();
  });
  document.getElementById('fb-none').addEventListener('click', () => {
    allApis.forEach(a => hidden.add(a)); applyFilter();
  });
})();

// ── Legend (static, decorative only — filter bar handles interaction) ─────
function legend(elId, items) {
  document.getElementById(elId).innerHTML =
    items.map(([l,c]) => `<div class="li"><div class="ld" style="background:${c}"></div>${l}</div>`).join('');
}

// ── mkChart now registers every chart ────────────────────────────────────
function mkChart(id, data, opts) {
  const ctx = document.getElementById(id).getContext('2d');
  const ch  = new Chart(ctx, { type:'line', data, options: opts });
  document.getElementById(id).addEventListener('dblclick', () => { try { ch.resetZoom(); } catch(e){} });
  registerChart(ch);
  // Apply current filter state immediately in case toggles changed before chart built
  ch.data.datasets.forEach(ds => { ds.hidden = hidden.has(ds.label); });
  ch.update('none');
  return ch;
}
document.querySelectorAll('.pill').forEach(p => {
  p.addEventListener('click', () => {
    document.querySelectorAll('.pill').forEach(x => x.classList.remove('on'));
    document.querySelectorAll('.sec').forEach(x => x.classList.remove('on'));
    p.classList.add('on');
    document.getElementById('s-'+p.dataset.s).classList.add('on');
  });
});

// ── Sub-tabs ──────────────────────────────────────────────────────────────
function makeTabs(containerId, labels, cb) {
  const el = document.getElementById(containerId);
  el.innerHTML = labels.map((l,i) =>
    `<div class="stab ${i===0?'on':''}" data-i="${i}">${l}</div>`).join('');
  el.querySelectorAll('.stab').forEach(t => {
    t.addEventListener('click', () => {
      el.querySelectorAll('.stab').forEach(x => x.classList.remove('on'));
      t.classList.add('on');
      cb(+t.dataset.i);
    });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// 1-3  DAILY
// ══════════════════════════════════════════════════════════════════════════
(function() {
  const apis = Object.keys(D.api_colors);
  legend('leg-daily', apis.map(a => [a, D.api_colors[a]]));
  mkChart('c-med', D.daily.median, baseOpts());
  mkChart('c-min', D.daily.min,    baseOpts());
  mkChart('c-max', D.daily.max,    baseOpts());
})();

// ══════════════════════════════════════════════════════════════════════════
// 4  MONTHLY
// ══════════════════════════════════════════════════════════════════════════
(function() {
  const apis = Object.keys(D.api_colors);
  legend('leg-monthly', apis.map(a => [a, D.api_colors[a]]));
  mkChart('c-monthly', D.monthly, baseOpts(false));
})();

// ══════════════════════════════════════════════════════════════════════════
// 5  YEAR-OVER-YEAR
// ══════════════════════════════════════════════════════════════════════════
(function() {
  const apis  = Object.keys(D.yoy);
  const years = D.yoy_years;
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const YC = ['#f1fa8c','#ffb347','#ff79c6','#bd93f9','#00e5ff','#69ff6e','#ff5555','#8be9fd'];
  const yc = yr => YC[years.indexOf(yr) % YC.length];

  legend('leg-yoy', years.map((y,i) => [String(y), YC[i % YC.length]]));

  const grid = document.getElementById('grid-yoy');
  apis.forEach(api => {
    const safe = api.replace(/ /g,'_');
    const card = document.createElement('div');
    card.className = 'card'; card.id = 'yc-'+safe; card.style.display='none';
    card.innerHTML = `<div class="ct"><span>${api}</span> &nbsp;— month-by-month YoY (median ms)</div>
                      <div class="cw yoy-cw"><canvas id="yv-${safe}"></canvas></div>`;
    grid.appendChild(card);
  });

  function show(idx) {
    apis.forEach((api,i) => {
      const safe = api.replace(/ /g,'_');
      const card = document.getElementById('yc-'+safe);
      card.style.display = i===idx ? 'block' : 'none';
    });
    const api  = apis[idx];
    const safe = api.replace(/ /g,'_');
    const card = document.getElementById('yc-'+safe);
    if (!card.dataset.built) {
      card.dataset.built = '1';
      // Card is already visible — canvas now has correct width
      const datasets = years.map(yr => ({
        label: String(yr),
        data: D.yoy[api][yr] || Array(12).fill(null),
        borderColor: yc(yr), backgroundColor: yc(yr)+'22',
        borderWidth:2.2, pointRadius:5, pointHoverRadius:8, tension:.3, spanGaps:false,
      }));
      const opts = baseOpts(false);
      opts.scales.x.ticks = {};
      mkChart('yv-'+safe, { labels:MONTHS, datasets }, opts);
    }
  }
  makeTabs('tabs-yoy', apis, show);
  show(0);
})();

// ══════════════════════════════════════════════════════════════════════════
// 6  TIME FRAMES  (one chart per time frame, all APIs as lines)
// ══════════════════════════════════════════════════════════════════════════
(function() {
  // Legend shows APIs (not time frames), since each chart contains all APIs
  const apis = Object.keys(D.api_colors);
  legend('leg-tf', apis.map(a => [a, D.api_colors[a]]));

  const grid = document.getElementById('grid-tf');
  TFS.forEach(tf => {
    const safe = tf.replace(/[^a-z0-9]/gi,'_');
    const card = document.createElement('div');
    card.className = 'card'; card.id = 'tc-'+safe; card.style.display='none';
    card.innerHTML = `<div class="ct"><span>${tf}</span> &nbsp;— daily median by API (ms)</div>
                      <div class="cw tall"><canvas id="tv-${safe}"></canvas></div>`;
    grid.appendChild(card);
  });

  function show(idx) {
    TFS.forEach((tf,i) => {
      const safe = tf.replace(/[^a-z0-9]/gi,'_');
      const card = document.getElementById('tc-'+safe);
      card.style.display = i===idx ? 'block' : 'none';
      if (i===idx && !card.dataset.built) {
        card.dataset.built = '1';
        const apiData = D.timeframe[tf] || {};
        // All APIs share the same continuous date spine — just grab labels from first
        const allDates = Object.values(apiData)[0]?.labels || [];
        const datasets = apis.map(api => {
          const s = apiData[api] || {labels:[],values:[]};
          return {
            label: api,
            data: s.values,
            borderColor: D.api_colors[api], backgroundColor: D.api_colors[api]+'22',
            borderWidth:2, pointRadius:1, pointHoverRadius:6, tension:.3, spanGaps:true,
          };
        });
        mkChart('tv-'+safe, { labels:allDates, datasets }, baseOpts(true));
      }
    });
  }
  makeTabs('tabs-tf', TFS, show);
  show(0);
})();
</script>
</body>
</html>
"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python api_chart_chartjs.py <path_to_csv> [output.html]")
        print("  <path_to_csv>  CSV with EventDate and EventComments columns")
        print("  [output.html]  Output file (default: api_report_plotly.html)")
        sys.exit(1)

    csv_path    = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("api_report_plotly.html")

    print(f"\n📂 Loading: {csv_path}")
    df = load_data(str(csv_path))

    apis       = sorted(df["api_type"].unique())
    api_colors = {api: API_PALETTE[i % len(API_PALETTE)] for i, api in enumerate(apis)}

    print(f"   {len(df):,} records  |  APIs: {apis}")
    print(f"   Range: {df['EventDate'].min().date()} → {df['EventDate'].max().date()}")

    print("\n⚙️  Building report data …")
    payload = build_json(df, api_colors)

    span_days = (df["EventDate"].max().date() - df["EventDate"].min().date()).days
    span_str  = (
        f"{span_days // 365}y {(span_days % 365) // 30}m"
        if span_days >= 365 else f"{span_days}d"
    )

    html = (HTML
        .replace("__GENERATED_AT__", datetime.now().strftime("%Y-%m-%d %H:%M"))
        .replace("__SOURCE__",       csv_path.name)
        .replace("__RECORDS__",      f"{len(df):,}")
        .replace("__APIS__",         str(len(apis)))
        .replace("__RANGE__",        f"{df['EventDate'].min().strftime('%b %Y')} – {df['EventDate'].max().strftime('%b %Y')}")
        .replace("__SPAN__",         span_str)
        .replace("__JSON_DATA__",    json.dumps(payload))
        .replace("__TF_COLORS__",    json.dumps(TF_COLORS))
        .replace("__TF_ORDER__",     json.dumps(TIMEFRAMES))
    )

    output_path.write_text(html, encoding="utf-8")
    print(f"\n✅ Report saved: {output_path.resolve()}")
    print("   Open in any browser — fully self-contained, no server needed.")


if __name__ == "__main__":
    main()