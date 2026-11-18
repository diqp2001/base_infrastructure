"""
/stm-deciles/ - progress and results of the monthly STM decile backtest (stm_monthly_decile_project).

Read-only: it reads results/stm_monthly_deciles/status.json and the run folder's summary.json,
decile_returns_gross.csv and deciles_cumulative.png. The page refreshes itself every 30 s;
/stm-deciles/status.json serves the raw status and /stm-deciles/chart.png the latest chart.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Optional

import pandas as pd
from flask import Blueprint, abort, jsonify, render_template_string, send_file

from src.application.services.dispersion.dispersion_progress import read_status

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="30"><title>STM monthly deciles</title>
<style>
:root{--bg:#fff;--fg:#1d1d1f;--mut:#6b6b70;--line:#e3e3e6;--card:#f6f6f8;--a:#5b6ee1;--pos:#2e7d32;--neg:#c62828}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--fg:#ececef;--mut:#9a9aa2;--line:#2b2b30;--card:#1c1c20;--pos:#66bb6a;--neg:#ef5350}}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:0 0 4px} h2{font-size:16px;margin:20px 0 8px} .mut{color:var(--mut)}
.row{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;min-width:140px;flex:1}
.card b{display:block;font-size:20px;font-variant-numeric:tabular-nums}
.bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:var(--a)}
.state{display:inline-block;padding:1px 8px;border-radius:9px;font-size:12px;border:1px solid var(--line)}
.running{color:var(--a)}.done{color:var(--pos)}.failed{color:var(--neg)}
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:13px}
th,td{padding:5px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left} th{color:var(--mut);font-weight:600}
.pos{color:var(--pos)}.neg{color:var(--neg)} img{max-width:100%;border:1px solid var(--line);border-radius:10px;background:#fff}
pre{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px;overflow-x:auto;font-size:12px;white-space:pre-wrap}
</style></head><body><main>
<h1>STM monthly deciles on the Dow: model A (prices) vs B (+ Eulerpool fundamentals)</h1>
<div class="mut">Monthly retrained STM ranks the point-in-time members into D1..D10; the engine trades D10 &minus; D1.
Refreshes every 30 s.</div>
{% if not st %}<p>No run yet.</p>{% else %}
<p><span class="state {{st.state}}">{{st.state}}</span> step <b>{{st.step}}</b> &middot; {{st.message or ''}}
<span class="mut">&middot; started {{st.started_at}} &middot; updated {{st.updated_at}}</span></p>
{% if st.months_total %}<div class="bar"><i style="width:{{ [100, (100*(st.months_done or 0)/st.months_total)]|min|round(1) }}%"></i></div>
<div class="mut">{{st.months_done or 0}} / {{st.months_total}} rebalances &middot; last {{st.last_month or '-'}}
&middot; window {{st.start}} &rarr; {{st.end}}</div>{% endif %}
<div class="row">
{% for v in variants %}<div class="card"><span class="mut">Cumulative D10 &minus; D1, {{v}} (gross)</span>
<b class="{{cls(st.get('cumulative_ls_' ~ v))}}">{{pct(st.get('cumulative_ls_' ~ v))}}</b></div>{% endfor %}
<div class="card"><span class="mut">Engine portfolio value</span><b>{{money(st.portfolio_value)}}</b></div>
</div>
{% if has_chart %}<h2>Cumulative return of every decile</h2><img src="chart.png?t={{st.updated_at}}" alt="Cumulative return of deciles D1 to D10 and D10 minus D1, per model">{% endif %}
{% if comparison %}<h2>D10 &minus; D1: A vs B (gross)</h2><div class="tbl"><table>
<tr><th>statistic</th>{% for v in comparison %}<th>{{v}}</th>{% endfor %}</tr>
{% for k in cmp_keys %}<tr><td>{{k}}</td>{% for v in comparison %}<td>{{fmt(k, comparison[v].get(k))}}</td>{% endfor %}</tr>{% endfor %}
</table></div>{% endif %}
{% for v, stats in decile_stats.items() %}<h2>Model {{v}}: statistics per decile (gross)</h2><div class="tbl"><table>
<tr><th>statistic</th>{% for c in stats %}<th>{{c}}</th>{% endfor %}</tr>
{% for k in stat_keys %}<tr><td>{{k}}</td>{% for c in stats %}<td class="{{cls(stats[c].get(k)) if k in signed else ''}}">{{fmt(k, stats[c].get(k))}}</td>{% endfor %}</tr>{% endfor %}
</table></div>{% endfor %}
{% if recent %}<h2>Monthly decile returns, latest first (gross)</h2><div class="tbl"><table>
<tr>{% for h in recent_cols %}<th>{{h}}</th>{% endfor %}</tr>
{% for r in recent %}<tr>{% for h in recent_cols %}<td class="{{cls(r[h]) if h not in ('period_end','variant') else ''}}">{{pct(r[h]) if h not in ('period_end','variant') else r[h]}}</td>{% endfor %}</tr>{% endfor %}
</table></div>{% endif %}
{% if st.log_tail %}<h2>Log</h2><pre>{{ st.log_tail|reverse|join('\\n') }}</pre>{% endif %}
<p class="mut">Run folder: {{st.run_folder or '-'}}</p>{% endif %}
</main></body></html>"""

CMP_KEYS = ["cumulative_return", "annualized_return", "sharpe_ratio", "max_drawdown", "win_rate", "average_spread",
            "spearman_decile_vs_average_return"]
STAT_KEYS = ["periods", "cumulative_return", "annualized_return", "annualized_volatility", "sharpe_ratio",
             "max_drawdown", "win_rate", "average_return", "worst_period", "best_period", "average_turnover"]
SIGNED = {"cumulative_return", "annualized_return", "average_return", "average_spread"}
RATIOS = {"sharpe_ratio", "calmar_ratio", "spearman_decile_vs_average_return", "periods"}
RECENT_ROWS = 24


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _pct(x) -> str:
    return f"{100 * x:+.2f}%" if _finite(x) else "-"


def _money(x) -> str:
    return f"{x:,.0f}" if _finite(x) else "-"


def _fmt(key: str, x) -> str:
    if not _finite(x):
        return "-"
    if key == "periods":
        return str(int(x))
    return f"{x:.2f}" if key in RATIOS else _pct(x)


def _cls(x) -> str:
    return ("pos" if x > 0 else "neg" if x < 0 else "") if _finite(x) else ""


def create_stm_deciles_blueprint(results_dir: Optional[str] = None) -> Blueprint:
    if results_dir is None:
        from src.application.managers.project_managers.stm_monthly_decile_project import config
        results_dir = config.get_config()["results_dir"]
    bp = Blueprint("stm_deciles", __name__, url_prefix="/stm-deciles")

    def _folder(st: Optional[Dict[str, Any]]) -> Optional[str]:
        """The run folder, looked up under results_dir by name (the run may have written a path of another OS)."""
        run = (st or {}).get("run_folder")
        if not run:
            return None
        name = run.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
        path = os.path.join(results_dir, name)
        return path if os.path.isdir(path) else None

    def _summary(folder: Optional[str]) -> Dict[str, Any]:
        try:
            with open(os.path.join(folder or "", "summary.json"), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _recent(folder: Optional[str]) -> List[Dict[str, Any]]:
        path = os.path.join(folder or "", "decile_returns_gross.csv")
        if not folder or not os.path.exists(path):
            return []
        try:
            df = pd.read_csv(path)
        except (OSError, ValueError, pd.errors.EmptyDataError):
            return []
        df = df.sort_values(["period_end", "variant"], ascending=[False, True]).head(RECENT_ROWS)
        return [{k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
                for r in df.to_dict("records")]

    @bp.get("/")
    def page():
        st = read_status(results_dir)
        folder = _folder(st)
        summary = _summary(folder)
        variants = (st or {}).get("variants") or list(summary.get("variants", {})) or ["A"]
        decile_stats = {v: s.get("gross", {}).get("statistics", {}) for v, s in summary.get("variants", {}).items()
                        if s.get("gross", {}).get("statistics")}
        recent = _recent(folder)
        cols = ["period_end", "variant"] + [c for c in (recent[0].keys() if recent else [])
                                            if c not in ("period_end", "variant")]
        return render_template_string(
            PAGE, st=st, variants=variants, comparison=summary.get("long_short_comparison") or {},
            cmp_keys=CMP_KEYS, decile_stats=decile_stats, stat_keys=STAT_KEYS, signed=SIGNED, recent=recent,
            recent_cols=cols, has_chart=bool(folder and os.path.exists(os.path.join(folder, "deciles_cumulative.png"))),
            pct=_pct, money=_money, fmt=_fmt, cls=_cls)

    @bp.get("/chart.png")
    def chart():
        folder = _folder(read_status(results_dir))
        path = os.path.join(folder or "", "deciles_cumulative.png")
        if not folder or not os.path.exists(path):
            abort(404)
        return send_file(path, mimetype="image/png", max_age=0)

    @bp.get("/status.json")
    def status():
        return jsonify(read_status(results_dir) or {})

    return bp
