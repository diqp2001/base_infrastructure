"""
/dispersion-stm/ - progress and results of the monthly model-filtered dispersion backtest (etf_dispersion_stm_project).
Read-only: it reads results/etf_dispersion_stm/status.json and the run folder's trades.csv / summary.json. The page
refreshes itself every 30 s; /dispersion-stm/status.json serves the raw status.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Optional

import pandas as pd
from flask import Blueprint, jsonify, render_template_string

from src.application.services.dispersion.dispersion_progress import read_status

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="30"><title>DIA dispersion backtest</title>
<style>
:root{--bg:#f4f5f7;--fg:#212529;--mut:#6c757d;--line:#e6e8eb;--card:#ffffff;--a:#2a78d6;--b:#eb6834;--pos:#13795b;--neg:#b42318}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:0 0 4px} .mut{color:var(--mut)} .row{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;min-width:140px;flex:1}
.card b{display:block;font-size:20px;font-variant-numeric:tabular-nums}
.bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:var(--a)}
.state{display:inline-block;padding:1px 8px;border-radius:9px;font-size:12px;border:1px solid var(--line)}
.running{color:var(--a)}.done{color:var(--pos)}.failed{color:var(--neg)}
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:13px}
th,td{padding:5px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left} th{color:var(--mut);font-weight:600}
.pos{color:var(--pos)}.neg{color:var(--neg)} pre{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:10px;overflow-x:auto;font-size:12px;white-space:pre-wrap}
.hub-bar{background:#23272f;padding:10px 16px}.hub-bar a{color:#fff;text-decoration:none;font-weight:600}</style></head><body><div class="hub-bar"><a href="/dashboard">Trading Hub</a></div><main>
<h1>DIA dispersion: original (A) vs STM-filtered (B)</h1>
<div class="mut">Monthly, same N short DIA calls; premiums MODELLED (Black-Scholes, realised vol). Refreshes every 30 s.</div>
{% if not st %}<p>No run yet.</p>{% else %}
<p><span class="state {{st.state}}">{{st.state}}</span> step <b>{{st.step}}</b> &middot; {{st.message or ''}}
<span class="mut">&middot; started {{st.started_at}} &middot; updated {{st.updated_at}}</span></p>
{% if st.months_total %}<div class="bar"><i style="width:{{ (100*st.months_done/st.months_total)|round(1) }}%"></i></div>
<div class="mut">{{st.months_done}} / {{st.months_total}} months &middot; last {{st.last_month}}</div>{% endif %}
<div class="row">
<div class="card"><span class="mut">Trades settled</span><b>{{st.settled or 0}}</b></div>
<div class="card"><span class="mut">Cumulative P&amp;L A</span><b class="{{cls(st.cumulative_pnl_original)}}">{{money(st.cumulative_pnl_original)}}</b></div>
<div class="card"><span class="mut">Cumulative P&amp;L B</span><b class="{{cls(st.cumulative_pnl_filtered)}}">{{money(st.cumulative_pnl_filtered)}}</b></div>
<div class="card"><span class="mut">B &minus; A</span><b class="{{cls(diff)}}">{{money(diff)}}</b></div>
</div>
{% if summary %}<h2 style="font-size:16px">Summary</h2><div class="tbl"><table>
<tr><th>statistic</th><th>A original</th><th>B filtered</th><th>B &minus; A</th></tr>
{% for k in stat_keys %}<tr><td>{{k}}</td>{% for s in ('original','model_filtered','incremental') %}<td>{{num(summary.get(s,{}).get(k))}}</td>{% endfor %}</tr>{% endfor %}
</table></div>{% endif %}
{% if trades %}<h2 style="font-size:16px">Trades (latest first)</h2><div class="tbl"><table><tr>{% for h in cols %}<th>{{h}}</th>{% endfor %}</tr>
{% for t in trades %}<tr>{% for h in cols %}<td class="{{cls(t[h]) if h.endswith('pnl') else ''}}">{{num(t[h])}}</td>{% endfor %}</tr>{% endfor %}
</table></div>{% endif %}
{% if st.log_tail %}<h2 style="font-size:16px">Log</h2><pre>{{ st.log_tail|reverse|join('\\n') }}</pre>{% endif %}
<p class="mut">Run folder: {{st.run_folder or '-'}}</p>{% endif %}
</main></body></html>"""

COLUMNS = ["opened", "expiry", "etf_contracts_short", "n_selected", "n_constituents", "short_premium",
           "full_basket_premium", "selected_basket_premium", "unused_premium", "original_pnl", "filtered_pnl",
           "incremental_pnl", "problem"]
STAT_KEYS = ["trades", "total_pnl", "average_pnl", "median_pnl", "sharpe_annualised", "max_drawdown", "win_rate"]


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)


def _money(x) -> str:
    return f"{x:,.0f}" if _finite(x) else "-"


def _num(x) -> str:
    if isinstance(x, float):
        if not math.isfinite(x):
            return ""
        return f"{x:,.2f}" if abs(x) < 10 else f"{x:,.0f}"
    return "" if x is None else str(x)


def _cls(x) -> str:
    return ("pos" if x > 0 else "neg" if x < 0 else "") if _finite(x) else ""


def create_dispersion_stm_blueprint(results_dir: Optional[str] = None) -> Blueprint:
    if results_dir is None:
        from src.application.managers.project_managers.etf_dispersion_stm_project import config
        results_dir = config.get_config()["results_dir"]
    bp = Blueprint("dispersion_stm", __name__, url_prefix="/dispersion-stm")

    def _trades(folder: Optional[str]) -> List[Dict[str, Any]]:
        path = os.path.join(folder or "", "trades.csv")
        if not folder or not os.path.exists(path):
            return []
        try:
            df = pd.read_csv(path)
        except (OSError, ValueError, pd.errors.EmptyDataError):
            return []
        for col in COLUMNS:
            if col not in df:
                df[col] = None
        df = df[COLUMNS].iloc[::-1]
        return [{k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
                for r in df.to_dict("records")]

    def _summary(folder: Optional[str]) -> Optional[Dict[str, Any]]:
        try:
            with open(os.path.join(folder or "", "summary.json"), encoding="utf-8") as f:
                s = json.load(f)
            return s if s.get("trades_settled") else None
        except (OSError, ValueError):
            return None

    @bp.get("/")
    def page():
        st = read_status(results_dir)
        folder = (st or {}).get("run_folder")
        a, b = (st or {}).get("cumulative_pnl_original"), (st or {}).get("cumulative_pnl_filtered")
        diff = b - a if _finite(a) and _finite(b) else None
        return render_template_string(PAGE, st=st, trades=_trades(folder), cols=COLUMNS, summary=_summary(folder),
                                      stat_keys=STAT_KEYS, diff=diff, money=_money, num=_num, cls=_cls)

    @bp.get("/status.json")
    def status():
        return jsonify(read_status(results_dir) or {})

    return bp
