"""
/strategies — create, configure, validate, version, launch and compare strategy experiments.

Every route goes through the application services (StrategyServices): no repository, ORM model or business rule
here. The forms are generated from the selected project's schema, so only the parameters that project supports
appear; the server parses and validates every submission. Launching starts a separate worker process and returns
at once; only backtests can be launched (no paper / live trading from this interface).

    GET  /strategies/                          dashboard: projects, configurations, experiments
    GET  /strategies/new  POST /strategies/new create a draft (project + name)
    GET  /strategies/<id>                       configuration: sections, status, issues, actions, experiments
    GET  /strategies/<id>/edit  POST            edit a draft (fields of the project's schema)
    POST /strategies/<id>/validate | revise | clone | archive | launch
    GET  /strategies/<id>/preview               JSON: content, changes vs parent / defaults, native config, issues
    GET  /strategies/projects/<key>             JSON: capabilities + configuration schema
    GET  /strategies/experiments/<id>           status, log, metrics, provenance, artifacts
    GET  /strategies/experiments/<id>/status    JSON (polling)
    GET  /strategies/experiments/<id>/report    the project's own report of the run (+ .pdf)
    GET  /strategies/compare?ids=1,2            side by side, with comparability warnings
"""

from __future__ import annotations

import io

from flask import (Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, send_file,
                   url_for)

strategies_bp = Blueprint("strategies", __name__, url_prefix="/strategies")


# -- services: one database session per request ------------------------------------------------------------------

def _default_factory():
    from sqlalchemy.orm import sessionmaker

    from src.application.services.database_service.database_service import DatabaseService
    from src.application.services.strategy.strategy_services import StrategyServices
    database_service = DatabaseService("sql_server")          # creates missing tables (strategy_*) on connection
    database_service.set_ext_db()
    session_factory = sessionmaker(bind=database_service.session.get_bind())
    return lambda: StrategyServices(session_factory(), session_factory=session_factory)


def services():
    if "strategy_services" not in g:
        factory = current_app.config.get("STRATEGY_SERVICES_FACTORY")
        if factory is None:
            factory = _default_factory()
            current_app.config["STRATEGY_SERVICES_FACTORY"] = factory
        g.strategy_services = factory()
    return g.strategy_services


@strategies_bp.teardown_app_request
def _close_session(_exc):
    s = g.pop("strategy_services", None)
    if s is not None and getattr(s, "session", None) is not None and not current_app.config.get("STRATEGY_KEEP_SESSION"):
        s.session.close()


def _configuration_or_404(configuration_id: int):
    try:
        return services().configurations.get(configuration_id)
    except LookupError:
        abort(404)


def _experiment_or_404(experiment_id: int):
    try:
        return services().experiments.get(experiment_id)
    except LookupError:
        abort(404)


# -- pages --------------------------------------------------------------------------------------------------------

@strategies_bp.route("/")
def dashboard():
    s = services()
    configurations = s.configurations.list()
    experiments = sorted(s.experiments.list(), key=lambda e: e.id, reverse=True)
    names = {c.id: f"{c.name} v{c.version}" for c in configurations}
    return render_template("strategies_dashboard.html", projects=s.registry.capabilities(),
                           configurations=sorted(configurations, key=lambda c: (c.name, c.version)),
                           experiments=experiments, names=names)


@strategies_bp.route("/new", methods=["GET", "POST"])
def new():
    s = services()
    if request.method == "POST":
        try:
            c = s.configurations.create(request.form.get("name", ""), request.form.get("project_key", ""),
                                        description=request.form.get("description", ""))
        except (ValueError, KeyError) as e:
            flash(str(e), "danger")
            return render_template("strategies_new.html", projects=s.registry.capabilities(), form=request.form), 400
        flash(f"Draft '{c.name}' created from the project's defaults (today's configuration).", "success")
        return redirect(url_for("strategies.edit", configuration_id=c.id))
    return render_template("strategies_new.html", projects=s.registry.capabilities(), form={})


@strategies_bp.route("/<int:configuration_id>")
def view(configuration_id: int):
    s = services()
    c = _configuration_or_404(configuration_id)
    _, issues = s.configurations.check(c)
    adapter = s.registry.get(c.project_key)
    return render_template("strategies_view.html", c=c, issues=issues, schema=adapter.schema(),
                           capabilities=adapter.capabilities(), versions=s.configurations.versions(c.name),
                           experiments=s.experiments.list(configuration_id=c.id))


@strategies_bp.route("/<int:configuration_id>/edit", methods=["GET", "POST"])
def edit(configuration_id: int):
    from src.domain.entities.strategy.strategy_configuration import ConfigurationLocked
    s = services()
    c = _configuration_or_404(configuration_id)
    adapter = s.registry.get(c.project_key)
    issues = []
    if request.method == "POST":
        form = {k: (request.form.getlist(k) if len(request.form.getlist(k)) > 1 or k.startswith("factors.exclude")
                    else request.form.get(k)) for k in request.form}
        try:
            c, issues = s.configurations.update_from_form(configuration_id, form,
                                                          description=request.form.get("description"))
        except ConfigurationLocked as e:
            flash(f"{e}. Use 'New version'.", "warning")
            return redirect(url_for("strategies.view", configuration_id=configuration_id))
        if not issues:
            c, issues = s.configurations.validate(configuration_id)
        if not [i for i in issues if i.severity == "error"]:
            flash("Saved and validated." if c.status == "validated" else "Saved.", "success")
            return redirect(url_for("strategies.view", configuration_id=configuration_id))
        flash("Saved as a draft; fix the issues below before it can be launched.", "warning")
    elif not c.is_editable:
        flash(f"Version {c.version} is {c.status}: it cannot change. Create a new version to edit.", "warning")
        return redirect(url_for("strategies.view", configuration_id=configuration_id))
    return render_template("strategies_edit.html", c=c, schema=adapter.schema(), capabilities=adapter.capabilities(),
                           issues=issues)


@strategies_bp.route("/<int:configuration_id>/<action>", methods=["POST"])
def act(configuration_id: int, action: str):
    from src.application.services.strategy.configuration_service import ConfigurationInvalid
    from src.application.services.strategy.experiment_service import ExperimentConflict
    s = services()
    c = _configuration_or_404(configuration_id)
    try:
        if action == "validate":
            c, issues = s.configurations.validate(configuration_id)
            errors = [i for i in issues if i.severity == "error"]
            flash("Valid." if not errors else f"{len(errors)} issue(s): " + "; ".join(str(i) for i in errors),
                  "success" if not errors else "danger")
        elif action == "revise":
            c = s.configurations.revise(configuration_id)
            flash(f"Version {c.version} created (draft).", "success")
            return redirect(url_for("strategies.edit", configuration_id=c.id))
        elif action == "clone":
            c = s.configurations.clone(configuration_id, request.form.get("name", ""))
            flash(f"Cloned into '{c.name}'.", "success")
            return redirect(url_for("strategies.edit", configuration_id=c.id))
        elif action == "archive":
            s.configurations.archive(configuration_id)
            flash("Archived.", "info")
        elif action == "launch":
            if request.form.get("confirm") != "yes":
                flash("Tick the confirmation to launch the backtest.", "warning")
                return redirect(url_for("strategies.view", configuration_id=configuration_id))
            e = s.experiments.launch(configuration_id)
            flash(f"Experiment {e.id} launched (worker process {e.pid}).", "success")
            return redirect(url_for("strategies.experiment", experiment_id=e.id))
        else:
            abort(404)
    except ConfigurationInvalid as e:
        flash("Cannot launch: " + "; ".join(str(i) for i in e.issues), "danger")
    except ExperimentConflict as e:
        flash(str(e), "warning")
    except (ValueError, LookupError) as e:
        flash(str(e), "danger")
    return redirect(url_for("strategies.view", configuration_id=c.id))


@strategies_bp.route("/<int:configuration_id>/preview")
def preview(configuration_id: int):
    s = services()
    _configuration_or_404(configuration_id)
    out = s.configurations.preview(configuration_id)
    c = s.configurations.get(configuration_id)
    try:
        native = s.configurations.native_config(c)
        out["native_config"] = {k: v for k, v in native.items() if isinstance(v, (str, int, float, bool))}
    except Exception as e:                                   # invalid: the issues already say why
        out["native_config"] = {"error": str(e)}
    return jsonify(out)


@strategies_bp.route("/projects/<key>")
def project(key: str):
    s = services()
    try:
        adapter = s.registry.get(key)
    except KeyError:
        abort(404)
    return jsonify({"capabilities": adapter.capabilities().to_dict(), "schema": adapter.schema().to_dict()})


@strategies_bp.route("/experiments/<int:experiment_id>")
def experiment(experiment_id: int):
    s = services()
    s.experiments.recover()
    e = _experiment_or_404(experiment_id)
    c = s.configurations.get(e.configuration_id)
    return render_template("strategies_experiment.html", e=e, c=c, log=s.experiments.log_tail(experiment_id),
                           artifacts=s.experiments.artifacts(experiment_id))


@strategies_bp.route("/experiments/<int:experiment_id>/status")
def experiment_status(experiment_id: int):
    s = services()
    s.experiments.recover()
    e = _experiment_or_404(experiment_id)
    d = e.to_dict()
    d["log_tail"] = s.experiments.log_tail(experiment_id, lines=40)
    return jsonify(d)


@strategies_bp.route("/experiments/<int:experiment_id>/report")
def experiment_report(experiment_id: int):
    s = services()
    _experiment_or_404(experiment_id)
    e, report, renderer = s.experiments.report(experiment_id)
    if report is None:
        return render_template("strategies_report.html", e=e, report=None, sections=[]), 404
    tables = {key: (title, renderer.table_html(df)) for key, title, df in renderer.tables(report) if df is not None}
    order = getattr(renderer, "ORDER", None) or (list(tables) + list(renderer.FIGURES))
    sections = []
    for key in order:
        if key in tables:
            sections.append({"kind": "table", "title": tables[key][0], "html": tables[key][1]})
        elif key in renderer.FIGURES:
            sections.append({"kind": "figure", "title": renderer.FIGURES[key][0],
                             "png": renderer.figure_base64(report, key)})
    return render_template("strategies_report.html", e=e, report=report, sections=sections)


@strategies_bp.route("/experiments/<int:experiment_id>/report.pdf")
def experiment_report_pdf(experiment_id: int):
    s = services()
    _experiment_or_404(experiment_id)
    e, report, renderer = s.experiments.report(experiment_id)
    if report is None:
        abort(404)
    return send_file(io.BytesIO(renderer.build_pdf(report)), mimetype="application/pdf", as_attachment=True,
                     download_name=f"experiment_{e.id}_report.pdf")


@strategies_bp.route("/compare")
def compare():
    s = services()
    try:
        ids = [int(x) for x in request.args.get("ids", "").split(",") if x.strip()]
    except ValueError:
        abort(400)
    if len(ids) < 2:
        flash("Select at least two experiments to compare.", "warning")
        return redirect(url_for("strategies.dashboard"))
    try:
        result = s.experiments.compare(ids)
    except LookupError:
        abort(404)
    return render_template("strategies_compare.html", result=result)
