"""
/powerbuffet/generate and /powerbuffet/research — factor value generation and factor research.

    GET  /powerbuffet/generate                       form + recent jobs
    POST /powerbuffet/generate/plan                  validation and what would be computed (no write)
    POST /powerbuffet/generate/launch                start a background job (separate process)
    GET  /powerbuffet/generate/jobs/<id>             job status / summary / error report
    GET  /powerbuffet/generate/jobs/<id>/status      JSON (polling)
    POST /powerbuffet/generate/jobs/<id>/stop        ask the job to stop after the current value
    GET  /powerbuffet/research                       configuration + results (run=1)
    GET  /powerbuffet/research/csv?part=...          CSV export of a research table
    GET  /powerbuffet/research/pair.png?a=&b=        scatter of a factor pair (pooled observations)
    POST /powerbuffet/research/save-long-short       store the primary factor's long-short return as a custom factor

The routes only parse requests and render; the computations are application services (research.*).
"""

from __future__ import annotations

import base64
import io

from flask import Blueprint, Response, abort, flash, jsonify, redirect, render_template, request, url_for

from src.interfaces.flask.web.controllers.factor_analysis_controller import services

factor_research_bp = Blueprint("factor_research", __name__, url_prefix="/powerbuffet")


def _frequencies():
    from src.domain.entities.factor.factor import Factor
    return [(k, v["label"]) for k, v in Factor.FREQUENCIES.items()]


@factor_research_bp.route("/api/date-range")
def date_range():
    """First and last day with stored values of the selected factors (for the universe's shares): the calendar
    pickers' limits."""
    ids = [int(x) for x in request.args.get("factor_ids", "").split(",") if x.strip().isdigit()]
    universe = request.args.get("universe_id", "")
    if request.args.get("inputs") == "1":           # generation: the stored raw closes the factors are computed from
        close_id = services().data.close_factor_id(request.args.get("frequency", ""))
        ids = [close_id] if close_id is not None else []
    if not ids:
        return jsonify({"first": None, "last": None})
    return jsonify(services().data.date_range(ids, int(universe) if universe.isdigit() else None))


# ── generation ───────────────────────────────────────────────────────────────────────────────────────────────────

def _generation_request(form):
    from src.application.services.research.factor_generation import GenerationRequest
    ids = []
    for v in form.getlist("factor_ids"):
        try:
            ids.append(int(v))
        except ValueError:
            pass
    try:
        universe_id = int(form.get("universe_id", ""))
    except ValueError:
        universe_id = -1
    return GenerationRequest(universe_id=universe_id, start=form.get("start", ""), end=form.get("end", ""),
                             frequency=form.get("frequency", ""), factor_ids=ids,
                             all_eligible=form.get("all_eligible") == "on")


@factor_research_bp.route("/generate")
def generate():
    s = services()
    calculated = [f for f in s.data.factors() if f["source"] == "calculated"]
    return render_template("factor_generation.html", universes=s.data.universes(), factors=calculated,
                           frequencies=_frequencies(), jobs=s.jobs.list()[:20], plan=None, form={})


@factor_research_bp.route("/generate/plan", methods=["POST"])
def generate_plan():
    s = services()
    req = _generation_request(request.form)
    plan = s.generation.plan(req)
    calculated = [f for f in s.data.factors() if f["source"] == "calculated"]
    return render_template("factor_generation.html", universes=s.data.universes(), factors=calculated,
                           frequencies=_frequencies(), jobs=s.jobs.list()[:20], plan=plan, form=request.form,
                           selected=[int(x) for x in request.form.getlist("factor_ids") if x.isdigit()])


@factor_research_bp.route("/generate/launch", methods=["POST"])
def generate_launch():
    s = services()
    req = _generation_request(request.form)
    plan = s.generation.plan(req)
    if plan["errors"]:
        flash("Not launched: " + "; ".join(plan["errors"]), "danger")
        return redirect(url_for("factor_research.generate"))
    try:
        job = s.jobs.launch(req)
    except RuntimeError as e:
        flash(str(e), "warning")
        return redirect(url_for("factor_research.generate"))
    flash(f"Job {job['id']} started ({plan['calculations']} calculations).", "success")
    return redirect(url_for("factor_research.job", job_id=job["id"]))


@factor_research_bp.route("/generate/jobs/<job_id>")
def job(job_id):
    try:
        j = services().jobs.read(job_id)
    except (LookupError, ValueError):
        abort(404)
    return render_template("factor_generation_job.html", job=j)


@factor_research_bp.route("/generate/jobs/<job_id>/status")
def job_status(job_id):
    try:
        return jsonify(services().jobs.read(job_id))
    except (LookupError, ValueError):
        abort(404)


@factor_research_bp.route("/generate/jobs/<job_id>/stop", methods=["POST"])
def job_stop(job_id):
    try:
        services().jobs.stop(job_id)
        flash("Stop requested: the job ends after the current value.", "info")
    except (LookupError, ValueError):
        abort(404)
    return redirect(url_for("factor_research.job", job_id=job_id))


# ── research ─────────────────────────────────────────────────────────────────────────────────────────────────────

def _research_config(args):
    from src.application.services.research.factor_research import ResearchConfig

    def ints(key):
        out = []
        for v in args.getlist(key):
            for x in str(v).split(","):
                x = x.strip()
                if x.isdigit():
                    out.append(int(x))
        return out

    primary = ints("primary_factor_id")
    return ResearchConfig(universe_id=int(args.get("universe_id")), start=args.get("start"), end=args.get("end"),
                          frequency=args.get("frequency"), primary_factor_id=primary[0] if primary else -1,
                          comparison_factor_ids=ints("comparison_factor_ids"), method=args.get("method", "pearson"),
                          n_quantiles=int(args.get("n_quantiles") or 5), horizons=ints("horizons") or [1])


def _run_research(args):
    s = services()
    try:
        return s.research.run(_research_config(args)), None
    except (ValueError, TypeError, KeyError) as e:
        return None, str(e)


@factor_research_bp.route("/research")
def research():
    from src.application.services.research import research_renderer as rr
    s = services()
    ctx = {"universes": s.data.universes(), "factors": s.data.factors(), "frequencies": _frequencies(),
           "args": request.args, "result": None, "error": None}
    if request.args.get("run") == "1":
        result, error = _run_research(request.args)
        ctx.update(result=result, error=error)
        if result is not None:
            figs = {"distribution": rr.png(rr.fig_distribution(result.primary_values, "Distribution of the primary factor")),
                    "profile": rr.png(rr.fig_profile(result.primary_profile, "Cross-sectional evolution of the primary factor"))}
            if result.cross_sectional:
                import pandas as pd
                xs = pd.DataFrame({result.names[f]: x.by_date for f, x in result.cross_sectional.items()})
                figs["cross_sectional"] = rr.png(rr.fig_series(xs, "Per-timestamp cross-sectional correlation with the primary factor"))
            if result.quantiles is not None:
                cum = (1 + result.quantiles.returns.fillna(0)).cumprod() - 1
                figs["quantiles"] = rr.png(rr.fig_series(cum, "Cumulative return per quantile (equal weight, held one bar)"))
            ctx.update(figures=figs, cells=rr.correlation_cells(result.matrix, result.matrix_counts, result.matrix_notes),
                       table=rr.table_html)
    return render_template("factor_research.html", **ctx)


@factor_research_bp.route("/research/csv")
def research_csv():
    import pandas as pd
    result, error = _run_research(request.args)
    if result is None:
        return Response(f"error,{error!r}\n", status=400, mimetype="text/csv")
    part = request.args.get("part", "matrix")
    if part == "matrix":
        df = result.matrix
    elif part == "counts":
        df = result.matrix_counts
    elif part == "primary_stats":
        df = pd.Series(result.primary_stats).to_frame("value")
    elif part == "cross_sectional":
        df = pd.DataFrame({result.names[f]: x.by_date for f, x in result.cross_sectional.items()})
    elif part == "quantiles" and result.quantiles is not None:
        df = result.quantiles.returns
    elif part == "quantile_counts" and result.quantiles is not None:
        df = result.quantiles.counts
    else:
        return Response("error,unknown or unavailable part\n", status=400, mimetype="text/csv")
    buf = io.StringIO()
    df.to_csv(buf)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=factor_research_{part}.csv"})


@factor_research_bp.route("/research/pair.png")
def research_pair():
    from src.application.services.research import research_renderer as rr
    s = services()
    try:
        cfg = _research_config(request.args)
        a, b = int(request.args.get("a")), int(request.args.get("b"))
        membership = s.data.membership(cfg.universe_id)
        ids = sorted({m[0] for m in membership})
        from src.application.services.research.factor_research import membership_mask, to_bars
        pa = to_bars(s.data.panel(a, ids, cfg.start, cfg.end), cfg.frequency)
        pb = to_bars(s.data.panel(b, ids, cfg.start, cfg.end), cfg.frequency)
        pa = pa.where(membership_mask(pa.index, pa.columns, membership))
        pb = pb.where(membership_mask(pb.index, pb.columns, membership))
        idx, cols = pa.index.intersection(pb.index), pa.columns.intersection(pb.columns)
        names = {f["id"]: f["name"] for f in s.data.factors()}
        png = rr.png(rr.fig_scatter(pa.loc[idx, cols].to_numpy().ravel(), pb.loc[idx, cols].to_numpy().ravel(),
                                    names.get(a, str(a)), names.get(b, str(b))))
    except (ValueError, TypeError, KeyError):
        abort(400)
    return Response(base64.b64decode(png), mimetype="image/png")


@factor_research_bp.route("/research/save-long-short", methods=["POST"])
def research_save_long_short():
    s = services()
    result, error = _run_research(request.form)
    back = url_for("factor_research.research") + "?" + request.form.get("query", "")
    if result is None or result.quantiles is None:
        flash(f"Nothing saved: {error or 'no quantile portfolio (no stored closes at this frequency)'}", "danger")
        return redirect(back)
    name = (request.form.get("name") or "").strip()
    try:
        meta = s.save_mimicking_portfolio(name, result.quantiles.returns.iloc[:, -1], result.config.frequency,
                                          f"factor research: {result.names[result.config.primary_factor_id]} "
                                          f"quantile long-short, universe {result.config.universe_id}")
        flash(f"Saved custom factor return '{meta['name']}' ({meta['rows']} returns): use it in the Factor "
              f"Analysis with the custom model and factor {', '.join(meta['factors'])}.", "success")
    except ValueError as e:
        flash(f"Nothing saved: {e}", "danger")
    return redirect(back)
