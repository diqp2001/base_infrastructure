"""
/powerbuffet/model-evaluation — classifier model evaluation (CompanyShare classifiers), read only.

    GET /powerbuffet/model-evaluation                       selectors; with run=1 the evaluation
    GET /powerbuffet/model-evaluation/api/runs?model=KEY    the model's runs (JSON, for the run selector)
    GET /powerbuffet/model-evaluation/csv?part=...          CSV: observations | per_class | confusion | quintiles |
                                                            cumulative | correlation (same query as the page)

The routes only parse the request and render; the evaluation is ClassifierEvaluationService
(application/services/model_evaluation), built on the PowerBuffet ResearchServices' factory and data.
"""

from __future__ import annotations

import io
from datetime import date

from flask import Blueprint, Response, g, jsonify, render_template, request

from src.interfaces.flask.web.controllers.factor_analysis_controller import services

model_evaluation_bp = Blueprint("model_evaluation", __name__, url_prefix="/powerbuffet")


def evaluation_service():
    """The request's ClassifierEvaluationService: the one the services carry (tests inject it), else built once per
    request on their factory and data."""
    s = services()
    if getattr(s, "model_evaluation", None) is not None:
        return s.model_evaluation
    if "model_evaluation" not in g:
        from src.application.services.model_evaluation import build_classifier_evaluation_service
        g.model_evaluation = build_classifier_evaluation_service(s.factory, s.data)
    return g.model_evaluation


def _request(args):
    from src.application.services.model_evaluation.classifier_evaluation_service import EvaluationRequest
    run = (args.get("run_id") or "").strip()
    universe = (args.get("universe_id") or "").strip()
    horizon = (args.get("horizon") or "").strip()
    return EvaluationRequest(model_key=args.get("model", ""), run_id=int(run) if run.isdigit() else None,
                             universe_id=int(universe) if universe.isdigit() else None,
                             start=date.fromisoformat(args.get("start", "")[:10]),
                             end=date.fromisoformat(args.get("end", "")[:10]),
                             horizon=int(horizon) if horizon.isdigit() and int(horizon) > 0 else None)


def _evaluate(args):
    try:
        return evaluation_service().evaluate(_request(args)), None
    except (ValueError, KeyError, TypeError) as e:
        return None, str(e)


def _target_class(evaluation, args):
    raw = (args.get("prob_class") or "").strip()
    if raw.lstrip("-").isdigit() and int(raw) in evaluation.classes:
        return int(raw)
    return evaluation.classes[-1]                       # the best-performance class by default


@model_evaluation_bp.route("/model-evaluation")
def classifier_evaluation():
    from src.application.services.model_evaluation import evaluation_renderer as er
    from src.application.services.research import research_renderer as rr
    s = services()
    models = evaluation_service().models()
    selected = request.args.get("model") or (models[0].key if models else "")
    try:
        runs = evaluation_service().runs(selected) if selected else []
    except KeyError as e:
        return render_template("model_evaluation/classifier.html", models=models, selected_model="", runs=[],
                               universes=s.data.universes(), args=request.args, evaluation=None, error=str(e))
    ctx = {"models": models, "selected_model": selected, "runs": runs, "universes": s.data.universes(),
           "args": request.args, "evaluation": None, "error": None}
    if request.args.get("run") == "1" and selected:
        evaluation, error = _evaluate(request.args)
        ctx.update(evaluation=evaluation, error=error)
        if evaluation is not None:
            target = _target_class(evaluation, request.args)
            analysis = evaluation.probability_quintiles.get(target)
            ctx.update(
                target=target, analysis=analysis, figures=er.figures(evaluation, target), table=rr.table_html,
                per_class=er.per_class_table(evaluation.classification),
                confusion_counts=er.confusion_table(evaluation.classification),
                confusion_share=er.confusion_table(evaluation.classification, normalised=True),
                overview=er.probability_overview(evaluation), label=er.class_label)
    return render_template("model_evaluation/classifier.html", **ctx)


@model_evaluation_bp.route("/model-evaluation/api/runs")
def classifier_runs():
    key = request.args.get("model", "")
    try:
        runs = evaluation_service().runs(key)
    except KeyError:
        return jsonify([])
    return jsonify([{"run_id": r.run_id, "label": r.label,
                     "valid_from": r.valid_from.isoformat() if r.valid_from else None,
                     "valid_until": r.valid_until.isoformat() if r.valid_until else None} for r in runs])


def _view_table(er, evaluation, view):
    result = evaluation.cross_sectional.get(view)
    return er.confusion_table(result, labels=er.view_labels(view, result)) if result is not None else None


@model_evaluation_bp.route("/model-evaluation/csv")
def classifier_csv():
    from src.application.services.model_evaluation import evaluation_renderer as er
    evaluation, error = _evaluate(request.args)
    if evaluation is None:
        return Response(f"error,{error!r}\n", status=400, mimetype="text/csv")
    part = request.args.get("part", "observations")
    analysis = evaluation.probability_quintiles.get(_target_class(evaluation, request.args))
    frames = {
        "observations": lambda: evaluation.observations,
        "per_class": lambda: er.per_class_table(evaluation.classification),
        "confusion": lambda: er.confusion_table(evaluation.classification),
        "binary": lambda: _view_table(er, evaluation, "binary"),
        "quintile": lambda: _view_table(er, evaluation, "quintile"),
        "quintiles": lambda: analysis.mean_returns if analysis is not None else None,
        "cumulative": lambda: analysis.cumulative if analysis is not None else None,
        "correlation": lambda: analysis.correlation if analysis is not None else None,
    }
    if part not in frames or frames[part]() is None:
        return Response("error,unknown or unavailable part\n", status=400, mimetype="text/csv")
    buf = io.StringIO()
    frames[part]().to_csv(buf)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=classifier_evaluation_{part}.csv"})
