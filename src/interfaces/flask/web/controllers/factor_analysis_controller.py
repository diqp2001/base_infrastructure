"""
/factor-analysis — Fama-French-style factor analysis of any project's results (shared by every results page).

    GET  /factor-analysis/?source=stm:10m        configuration form + results (embedded by every results page)
    GET  /factor-analysis/csv?source=...&part=coefficients|series|rolling|comparison   CSV export
    POST /factor-analysis/factor-returns/french  import a Kenneth R. French daily dataset (ff3_daily, ff5_daily)
    POST /factor-analysis/factor-returns/upload  import a factor return CSV
    GET  /factor-analysis/factor-returns         JSON list of the available factor return series

Every computation is in application services (research.factor_regression, project_returns, factor_returns);
this module parses requests, calls them and renders.
"""

from __future__ import annotations

import io

from flask import (Blueprint, Response, current_app, flash, g, jsonify, redirect, render_template, request,
                   url_for)

factor_analysis_bp = Blueprint("factor_analysis", __name__, url_prefix="/factor-analysis")


def _default_factory():
    from sqlalchemy.orm import sessionmaker

    from src.application.services.database_service.database_service import DatabaseService
    from src.application.services.research.research_services import ResearchServices
    database_service = DatabaseService("sql_server")
    database_service.set_ext_db()
    session_factory = sessionmaker(bind=database_service.session.get_bind())
    return lambda: ResearchServices(session_factory())


def services():
    if "research_services" not in g:
        factory = current_app.config.get("RESEARCH_SERVICES_FACTORY")
        if factory is None:
            factory = _default_factory()
            current_app.config["RESEARCH_SERVICES_FACTORY"] = factory
        g.research_services = factory()
    return g.research_services


@factor_analysis_bp.teardown_app_request
def _close(_exc):
    s = g.pop("research_services", None)
    if s is not None and getattr(s, "session", None) is not None:
        s.session.close()


def _config_from(args):
    from src.application.services.research.factor_regression import FactorAnalysisConfig

    def num(key, cast):
        v = (args.get(key) or "").strip()
        return cast(v) if v else None

    return FactorAnalysisConfig(
        model=args.get("model", "capm"),
        factors=[f.strip() for v in args.getlist("factors") for f in v.split(",") if f.strip()] or None,
        frequency=args.get("frequency", "D"), start=args.get("start") or None, end=args.get("end") or None,
        convention=args.get("convention") or None, rolling_window=num("rolling_window", int),
        hac=args.get("hac", "on") != "off", hac_lags=num("hac_lags", int),
        confidence=num("confidence", float) or 0.95)


def _run(args):
    """(context for the template) — every failure becomes a message, never a fabricated result."""
    from src.application.services.research import research_renderer as rr
    from src.application.services.research.factor_regression import FactorDataMissing, analyse, compare
    s = services()
    key = args.get("source", "")
    ctx = {"source_key": key, "args": args, "sources": s.returns.sources(), "embedded": args.get("embedded") == "1",
           "factor_sets": s.factor_returns.available(), "result": None, "error": None, "comparison": None}
    try:
        source, report, strategies, primary = s.returns.strategies(key)
    except LookupError as e:
        ctx["error"] = str(e)
        return ctx
    ctx.update(source=source, strategies=strategies, primary=primary)
    if not strategies:
        ctx["error"] = f"No stored results for {source.label} yet: run the project first."
        return ctx
    if args.get("run") != "1":
        return ctx
    name = args.get("strategy") or primary
    if name not in strategies:
        ctx["error"] = f"unknown strategy '{name}'"
        return ctx
    series_name = args.get("factor_set") or "local_market"
    cfg = _config_from(args)
    try:
        frame = s.factor_returns.load(series_name)
        result = analyse(strategies[name], frame, cfg)
    except (FactorDataMissing, LookupError, ValueError) as e:
        ctx["error"] = str(e)
        return ctx
    ctx.update(result=result, figures=rr.factor_analysis_figures(result), cfg=cfg, factor_set=series_name,
               coef_html=rr.table_html(rr.coefficient_frame(result)),
               outliers_html=rr.table_html(result.outliers.to_frame("residual")))
    others = [strategies[n] for n in args.getlist("compare") if n in strategies]
    if others:
        out = compare([strategies[name]] + [o for o in others if o.name != name], frame, cfg)
        ctx["comparison"] = out
        ctx["comparison_html"] = rr.table_html(out["rows"])
    return ctx


@factor_analysis_bp.route("/")
def page():
    ctx = _run(request.args)
    return render_template("factor_analysis.html", **ctx)


@factor_analysis_bp.route("/csv")
def csv():
    from src.application.services.research.factor_regression import FactorDataMissing, analyse, compare
    s = services()
    args = request.args
    try:
        _, _, strategies, primary = s.returns.strategies(args.get("source", ""))
        name = args.get("strategy") or primary
        frame = s.factor_returns.load(args.get("factor_set") or "local_market")
        cfg = _config_from(args)
        result = analyse(strategies[name], frame, cfg)
    except (FactorDataMissing, LookupError, ValueError, KeyError) as e:
        return Response(f"error,{str(e)!r}\n", status=400, mimetype="text/csv")
    part = args.get("part", "coefficients")
    if part == "coefficients":
        df = result.coefficient_table()
    elif part == "series":
        df = result.series
    elif part == "rolling":
        if result.rolling is None:
            return Response("error,no rolling window requested\n", status=400, mimetype="text/csv")
        df = result.rolling
    elif part == "comparison":
        df = compare([strategies[n] for n in strategies], frame, cfg)["rows"]
    else:
        return Response("error,unknown part\n", status=400, mimetype="text/csv")
    buf = io.StringIO()
    df.to_csv(buf)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=factor_analysis_{part}.csv"})


@factor_analysis_bp.route("/factor-returns")
def factor_returns():
    return jsonify(services().factor_returns.available())


@factor_analysis_bp.route("/factor-returns/french", methods=["POST"])
def import_french():
    back = request.form.get("back") or url_for("factor_analysis.page")
    try:
        meta = services().importer.import_dataset(request.form.get("dataset", ""))
        flash(f"Imported {meta['name']}: {meta['rows']} rows, {meta['first']} .. {meta['last']}.", "success")
    except Exception as e:                                 # network, format: say why, import nothing
        flash(f"Import failed: {e}", "danger")
    return redirect(back)


@factor_analysis_bp.route("/factor-returns/upload", methods=["POST"])
def upload():
    back = request.form.get("back") or url_for("factor_analysis.page")
    f = request.files.get("file")
    try:
        if f is None or not f.filename:
            raise ValueError("choose a CSV file")
        meta = services().importer.import_csv(request.form.get("name", "").strip(), f.read().decode("utf-8-sig"),
                                              frequency=request.form.get("frequency", "D"),
                                              unit=request.form.get("unit", "percent"))
        flash(f"Imported {meta['name']}: {meta['rows']} rows ({', '.join(meta['factors'])}).", "success")
    except Exception as e:
        flash(f"Import failed: {e}", "danger")
    return redirect(back)
