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
import json
from types import SimpleNamespace

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
    rows = s.design.overview()
    experiments = sorted(s.experiments.list(), key=lambda e: e.id, reverse=True)
    names = {r["strategy"].id: f"{r['strategy'].name} v{r['strategy'].version}" for r in rows}
    return render_template("strategies/dashboard.html", projects=s.registry.capabilities(), rows=rows,
                           configurations=[r["strategy"] for r in rows], experiments=experiments, names=names,
                           registry_keys=set(s.registry.keys()))


@strategies_bp.route("/<int:configuration_id>/derive", methods=["POST"])
def derive(configuration_id: int):
    """A new draft from this strategy (its own copy of the universe), then the design page."""
    s = services()
    _configuration_or_404(configuration_id)
    try:
        c = s.design.derive(configuration_id, name=request.form.get("name", ""),
                            description=request.form.get("description") or None)
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("strategies.view", configuration_id=configuration_id))
    flash(f"Draft '{c.name}' v{c.version} created from strategy #{configuration_id}: change what differs.", "success")
    return redirect(url_for("strategies.design", configuration_id=c.id))


@strategies_bp.route("/<int:configuration_id>/design", methods=["GET", "POST"])
def design(configuration_id: int):
    """Edit a draft's definition: trading / training frequency, model, financial-asset and factor universe,
    parameter sections. Each form posts one part."""
    from src.domain.entities.strategy.strategy import StrategyLocked
    s = services()
    c = _configuration_or_404(configuration_id)
    if request.method == "POST":
        part = request.form.get("part", "")
        try:
            if part == "definition":
                s.design.update_definition(configuration_id, request.form.to_dict(),
                                           description=request.form.get("description"))
                flash("Definition saved (draft).", "success")
            elif part == "assets":
                text = request.form.get("instruments")
                if text is None:                                   # ticked boxes 'Type:SYMBOL'
                    text = _instruments_text(request.form.getlist("asset"))
                _, unknown = s.design.set_financial_assets(configuration_id, text)
                if unknown:
                    flash("Universe saved. Not stored as financial assets yet (kept in the request, added when a run "
                          "creates them): " + "; ".join(f"{t}: {', '.join(v)}" for t, v in unknown.items()), "warning")
                else:
                    flash("Financial-asset universe saved.", "success")
            elif part == "factors":
                s.design.set_factors(configuration_id, request.form.getlist("factor_id"))
                flash("Factor universe saved.", "success")
            elif part == "factor_universe":                       # the ticked factors as a reusable universe
                u = s.design.save_factor_universe(request.form.get("factor_universe_name", ""),
                                                  request.form.getlist("factor_id"))
                flash(f"Factor universe '{u.name}' v{u.version} saved ({len(u.factor_ids())} factors): it can be "
                      f"loaded in any strategy.", "success")
                part = "factors"
            elif part == "params":                                 # a section's dropdowns / checkboxes
                from src.application.services.strategy.parameter_choices import apply_choices
                name = request.form.get("section", "")
                values = apply_choices(name, c.section(name), request.form, locked=_locked(c))
                s.design.set_section(configuration_id, name, json.dumps(values))
                flash(f"Section '{name}' saved.", "success")
            elif part == "section":
                s.design.set_section(configuration_id, request.form.get("section", ""), request.form.get("json", ""))
                flash(f"Section '{request.form.get('section')}' saved.", "success")
            elif part == "validate":
                c, issues = s.design.validate(configuration_id, registry=s.registry)
                errors = [i for i in issues if i.severity == "error"]
                if errors:
                    flash(f"{len(errors)} issue(s): " + "; ".join(str(i) for i in errors), "danger")
                else:
                    flash("Validated.", "success")
                    return redirect(url_for("strategies.view", configuration_id=configuration_id))
            else:
                abort(400)
        except StrategyLocked as e:
            flash(str(e), "warning")
            return redirect(url_for("strategies.view", configuration_id=configuration_id))
        except (ValueError, LookupError) as e:
            flash(str(e), "danger")
        return redirect(url_for("strategies.design", configuration_id=configuration_id) + f"#{part}")
    if not c.is_editable:
        flash(f"Version {c.version} is {c.status}: create a new strategy from it to change it.", "warning")
        return redirect(url_for("strategies.view", configuration_id=configuration_id))
    from src.domain.entities.strategy.configuration_schema import SECTIONS
    from src.application.services.strategy.model_catalog import model_label
    has_form = s.registry.has_form(c.strategy_type)
    trading = c.section("trading").get("config_interval") or {}
    return render_template("strategies/design.html", c=c, detail=s.design.universe_detail(c),
                           catalog=s.design.factor_catalog(), sections=[x for x in SECTIONS if x != "universe"],
                           has_schema=has_form, models=[(m, model_label(m)) for m in s.design.model_choices(c)],
                           decision_minutes=trading.get("custom_interval_minutes") if isinstance(trading, dict)
                           else None, schedule=_schedule(c), param_fields=_param_fields(c),
                           choices=_definition_choices(c), assets=s.design.asset_choices(c, s.registry),
                           factor_universes=s.design.factor_universes())


def _schedule(strategy):
    from src.application.services.strategy.strategy_schedule import schedule
    return schedule(strategy)


def _locked(strategy):
    """Section keys the designer sets elsewhere (shown in the parameter lists, not editable there)."""
    from src.application.services.strategy.strategy_schedule import schedule
    locked = {"rebalance_every": "set with Trading frequency above",
              "retrain_every_rebalances": "set with Training frequency above",
              "custom_interval_minutes": "set with Trading frequency above",
              "custom_interval_days": "set with Trading frequency above",
              "model_type": "set with Model above"}
    if "rebalance_every" in schedule(strategy)["trading"]["stored_in"]:
        locked["annualisation"] = "follows the trading frequency (rebalances a year)"
    return locked


def _param_fields(strategy):
    from src.application.services.strategy.parameter_choices import field_tree
    from src.domain.entities.strategy.configuration_schema import SECTIONS
    locked = _locked(strategy)
    return {name: field_tree(name, strategy.section(name), locked) for name in SECTIONS if name != "universe"}


def _definition_choices(strategy):
    from src.application.services.strategy.parameter_choices import BAR_FREQUENCIES, IBKR_BAR_SIZES, int_choices

    def with_current(options, current):
        options = list(options)
        return options if current in (None, "") or current in options else [current] + options
    return {"bar_frequency": with_current(BAR_FREQUENCIES, strategy.bar_frequency),
            "bar_size": with_current(IBKR_BAR_SIZES, strategy.bar_size),
            "prediction_horizon": int_choices(strategy.prediction_horizon),
            "training_window": int_choices(strategy.training_window)}


def _instruments_text(ticked):
    """'CompanyShare:AAPL' boxes -> the universe text ('CompanyShare: AAPL, MSFT' per type)."""
    by_type = {}
    for item in ticked:
        asset_type, _, symbol = item.partition(":")
        if symbol:
            by_type.setdefault(asset_type, []).append(symbol)
    return "\n".join(f"{t}: {', '.join(symbols)}" for t, symbols in by_type.items())


@strategies_bp.route("/new", methods=["GET", "POST"])
def new():
    """A draft from a project's defaults: a project with a web form (edited in its form), or any other backtest
    project folder (e.g. stm_monthly_decile_project: edited in the strategy designer)."""
    s = services()
    projects, folders = s.registry.capabilities(), s.registry.folder_capabilities()
    if request.method == "POST":
        try:
            c = s.configurations.create(request.form.get("name", ""), request.form.get("project_key", ""),
                                        description=request.form.get("description", ""))
        except (ValueError, KeyError) as e:
            flash(str(e), "danger")
            return render_template("strategies/new.html", projects=projects, folders=folders, form=request.form), 400
        flash(f"Draft '{c.name}' created from the project's defaults (today's configuration).", "success")
        target = "strategies.edit" if s.registry.has_form(c.strategy_type) else "strategies.design"
        return redirect(url_for(target, configuration_id=c.id))
    return render_template("strategies/new.html", projects=projects, folders=folders, form={})


@strategies_bp.route("/<int:configuration_id>")
def view(configuration_id: int):
    s = services()
    c = _configuration_or_404(configuration_id)
    common = dict(c=c, detail=s.design.universe_detail(c), versions=s.configurations.versions(c.name),
                  experiments=s.experiments.list(configuration_id=c.id))
    try:
        adapter = s.registry.get(c.strategy_type)
    except KeyError:                       # a type no project implements any more: shown as stored, read-only
        return render_template("strategies/view.html", issues=[], schema=_stored_schema(c), has_schema=False,
                               launchable=False, capabilities=SimpleNamespace(
                                   label=f"{c.strategy_type} (no project implements it)", unsupported=[]), **common)
    has_form = s.registry.has_form(c.strategy_type)
    _, issues = s.configurations.check(c)
    capabilities = adapter.capabilities() if has_form else SimpleNamespace(
        label=f"project {c.strategy_type} (applied onto the project's own config)", unsupported=[])
    return render_template("strategies/view.html", issues=issues, has_schema=has_form,
                           schema=adapter.schema() if has_form else _stored_schema(c),
                           launchable=getattr(adapter, "launchable", True), capabilities=capabilities,
                           window_default=s.experiments.default_window(c.id) if c.status in ("validated", "locked")
                           else None, **common)


def _stored_schema(c):
    """A display schema of a strategy's stored sections (no project adapter: every value shown as stored)."""
    from src.domain.entities.strategy.configuration_schema import ConfigurationSchema, FieldSpec, SectionSchema
    sections = tuple(SectionSchema(name, tuple(FieldSpec(key, "str", default=value) for key, value in values.items()))
                     for name, values in c.sections.items() if values)
    return ConfigurationSchema(c.strategy_type, sections)


@strategies_bp.route("/<int:configuration_id>/edit", methods=["GET", "POST"])
def edit(configuration_id: int):
    from src.domain.entities.strategy.strategy import StrategyLocked as ConfigurationLocked
    s = services()
    c = _configuration_or_404(configuration_id)
    adapter = s.registry.get(c.strategy_type)
    issues = []
    if request.method == "POST":
        form = _project_form(adapter.schema(), request.form)
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
    return render_template("strategies/edit.html", c=c, schema=adapter.schema(), capabilities=adapter.capabilities(),
                           issues=issues, options=_project_options(adapter.schema(), c))


def _project_form(schema, posted):
    """The project form as update_from_form reads it: ticked list boxes joined back into the field's text form
    (an empty hidden value keeps a list present when nothing is ticked)."""
    kinds = {f"{s.name}.{f.name}": f.kind for s in schema.sections for f in s.fields}
    form = {}
    for key in posted:
        values = [v for v in posted.getlist(key) if v != ""]
        kind = kinds.get(key)
        if kind == "int_list":
            form[key] = ",".join(values)
        elif kind == "int_pair_list":
            form[key] = ";".join(values)
        elif kind == "str_list":                    # ticked boxes, or one 'A, B' text value
            form[key] = [x.strip() for v in values for x in v.replace("\n", ",").split(",") if x.strip()]
        elif kind == "choice_list" or key.startswith("factors.exclude"):
            form[key] = values
        else:
            form[key] = values[0] if len(values) == 1 else (values or posted.get(key))
    return form


def _project_options(schema, strategy):
    """{section.field: [choices]} of the project form's numbers and lists (the current value always included)."""
    from src.application.services.strategy.parameter_choices import (
        HORIZONS, MACD_PAIRS, float_choices, int_choices,
    )
    out = {}
    for section in schema.sections:
        values = strategy.section(section.name)
        for f in section.fields:
            key = f"{section.name}.{f.name}"
            v = values.get(f.name, f.default)

            def bounded(options):
                return [o for o in options if (f.minimum is None or o >= f.minimum)
                        and (f.maximum is None or o <= f.maximum)]
            if f.kind == "int":
                out[key] = sorted(set(bounded(int_choices(v if isinstance(v, int) else None)))
                                  | ({v} if isinstance(v, int) else set()))
            elif f.kind == "float":
                out[key] = sorted(set(bounded(float_choices(float(v) if v is not None else 0.0)))
                                  | ({float(v)} if v is not None else set()))
            elif f.kind == "int_list":
                out[key] = sorted(set(bounded(HORIZONS)) | set(v or []))
            elif f.kind == "int_pair_list":
                pairs = [list(p) for p in MACD_PAIRS]
                out[key] = pairs + [list(p) for p in (v or []) if list(p) not in pairs]
            elif f.kind == "str_list":
                try:
                    stored = services().design.universes.stored_symbols("CompanyShare")
                except Exception:
                    stored = []
                out[key] = sorted(set(stored) | set(v or []) | set(f.default or []))
    return out


@strategies_bp.route("/<int:configuration_id>/<action>", methods=["POST"])
def act(configuration_id: int, action: str):
    from src.application.services.strategy.strategy_service import ConfigurationInvalid
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
            from src.application.services.strategy.backtest_window import BacktestWindow
            window = (BacktestWindow.parse(request.form.get("backtest_start"), request.form.get("backtest_end"),
                                           request.form.get("initial_capital"))
                      if request.form.get("backtest_start") else None)
            e = s.experiments.launch(configuration_id, window=window)
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
    c = s.configurations.get(e.strategy_id)
    return render_template("strategies/experiment.html", e=e, c=c, log=s.experiments.log_tail(experiment_id),
                           artifacts=s.experiments.artifacts(experiment_id))


@strategies_bp.route("/experiments/<int:experiment_id>/retry", methods=["POST"])
def experiment_retry(experiment_id: int):
    """A failed / interrupted experiment launched again (same strategy, window and capital) as a new experiment."""
    from src.application.services.strategy.experiment_service import ExperimentConflict
    from src.application.services.strategy.strategy_service import ConfigurationInvalid
    s = services()
    _experiment_or_404(experiment_id)
    try:
        e = s.experiments.retry(experiment_id)
    except ConfigurationInvalid as e:
        flash("Cannot retry: " + "; ".join(str(i) for i in e.issues), "danger")
    except ExperimentConflict as e:
        flash(str(e), "warning")
    except (ValueError, LookupError) as e:
        flash(str(e), "danger")
    else:
        flash(f"Experiment {experiment_id} retried as experiment {e.id} (worker process {e.pid}).", "success")
        return redirect(url_for("strategies.experiment", experiment_id=e.id))
    return redirect(url_for("strategies.experiment", experiment_id=experiment_id))


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
        return render_template("strategies/report.html", e=e, report=None, sections=[]), 404
    tables = {key: (title, renderer.table_html(df)) for key, title, df in renderer.tables(report) if df is not None}
    order = getattr(renderer, "ORDER", None) or (list(tables) + list(renderer.FIGURES))
    sections = []
    for key in order:
        if key in tables:
            sections.append({"kind": "table", "title": tables[key][0], "html": tables[key][1]})
        elif key in renderer.FIGURES:
            sections.append({"kind": "figure", "title": renderer.FIGURES[key][0],
                             "png": renderer.figure_base64(report, key)})
    return render_template("strategies/report.html", e=e, report=report, sections=sections)


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
    return render_template("strategies/compare.html", result=result)
