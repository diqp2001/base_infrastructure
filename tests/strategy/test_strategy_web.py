"""Flask /strategies: the workflow end to end through the application services (file-based SQLite in a temp dir,
a new session per request, a fake worker runner; no IBKR, no SQL Server, no real process)."""

import re
from types import SimpleNamespace

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.application.services.strategy.experiment_worker import run_experiment
from src.application.services.strategy.strategy_services import StrategyServices


class FakeRunner:
    def __init__(self):
        self.started = []

    def start(self, experiment):
        self.started.append(experiment.id)
        return 31337


@pytest.fixture
def web(tmp_path, monkeypatch):
    from src.infrastructure.models import ModelBase
    from src.interfaces.flask.app import FlaskApp
    monkeypatch.setenv("MONITOR_STATE_DIR", str(tmp_path / "monitor"))
    engine = create_engine(f"sqlite:///{tmp_path / 'web.db'}")
    ModelBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    runner = FakeRunner()

    def services():
        return StrategyServices(factory(), runner=runner, session_factory=factory, results_root=tmp_path / "results",
                                is_alive=lambda pid: False, host="web-test")

    app = FlaskApp().get_app()
    app.config.update(STRATEGY_SERVICES_FACTORY=services, TESTING=True)
    yield SimpleNamespace(client=app.test_client(), services=services, runner=runner, tmp=tmp_path)
    engine.dispose()


def _create(web, name="csm web", project="cross_sectional"):
    r = web.client.post("/strategies/new", data={"name": name, "project_key": project, "description": "test"})
    assert r.status_code == 302
    return int(re.search(r"/strategies/(\d+)/edit", r.headers["Location"]).group(1))


def _form(web, cid):
    """The edit form as the browser would post it (current values of every field)."""
    s = web.services()
    c = s.configurations.get(cid)
    schema = s.registry.get(c.project_key).schema()
    data = {}
    for section in schema.sections:
        values = c.section(section.name)
        for f in section.fields:
            v = values.get(f.name, f.default)
            key = f"{section.name}.{f.name}"
            if f.kind == "bool":
                if v:
                    data[key] = "on"
            elif f.kind == "choice_list":
                data[key] = list(v or [])
            elif f.kind in ("str_list", "int_list"):
                data[key] = ", ".join(str(x) for x in v or [])
            elif f.kind == "int_pair_list":
                data[key] = "; ".join(",".join(str(x) for x in p) for p in v or [])
            else:
                data[key] = "" if v is None else str(v)
    s.session.close()
    return data


def test_the_dashboard_lists_the_three_projects_and_what_they_do_not_support(web):
    html = web.client.get("/strategies/").get_data(as_text=True)
    for key in ("cross_sectional", "stm_reference", "stm_paper"):
        assert key in html
    assert "Not supported" in html


def test_each_project_shows_only_its_own_parameters(web):
    csm = web.client.get(f"/strategies/{_create(web)}/edit").get_data(as_text=True)
    stm = web.client.get(f"/strategies/{_create(web, 'stm web', 'stm_reference')}/edit").get_data(as_text=True)
    assert 'name="model.n_trials"' in csm and 'name="model.hidden_dim"' not in csm
    assert 'name="model.hidden_dim"' in stm and 'name="model.n_trials"' not in stm
    schema = web.client.get("/strategies/projects/stm_paper").get_json()
    assert schema["capabilities"]["output_contract"] == "position_signal"
    assert {s["name"] for s in schema["schema"]["sections"]} >= {"universe", "model", "training", "portfolio"}


def test_the_server_validates_what_is_posted(web):
    cid = _create(web)
    data = _form(web, cid)
    data["model.n_trials"] = "0"                                       # below the minimum
    data["model.dropout"] = "0.5"                                      # not a cross-sectional parameter
    r = web.client.post(f"/strategies/{cid}/edit", data=data)
    assert r.status_code == 200 and "must be &gt;= 1" in r.get_data(as_text=True)
    c = web.services().configurations.get(cid)
    assert c.status == "draft" and "dropout" not in c.section("model")
    data["model.n_trials"] = "25"
    r = web.client.post(f"/strategies/{cid}/edit", data=data)
    assert r.status_code == 302
    c = web.services().configurations.get(cid)
    assert (c.status, c.section("model")["n_trials"]) == ("validated", 25)
    preview = web.client.get(f"/strategies/{cid}/preview").get_json()
    assert {"section": "model", "field": "n_trials", "before": 40, "after": 25} in preview["changes"]
    assert preview["native_config"]["retrain_every_days"] == 21


def test_a_launch_needs_confirmation_locks_the_configuration_and_returns_at_once(web):
    cid = _create(web)
    web.client.post(f"/strategies/{cid}/edit", data=_form(web, cid))
    r = web.client.post(f"/strategies/{cid}/launch", data={})
    assert r.status_code == 302 and web.runner.started == []           # not confirmed: nothing launched
    r = web.client.post(f"/strategies/{cid}/launch", data={"confirm": "yes"})
    assert r.status_code == 302 and web.runner.started == [1]
    assert "/strategies/experiments/1" in r.headers["Location"]
    assert web.services().configurations.get(cid).status == "locked"
    r = web.client.get(f"/strategies/{cid}/edit")                      # locked: no edit form
    assert r.status_code == 302
    page = web.client.get("/strategies/experiments/1").get_data(as_text=True)
    assert "Experiment #1" in page
    assert web.client.get("/strategies/experiments/1/status").get_json()["status"] in ("queued", "interrupted")
    r = web.client.post(f"/strategies/{cid}/revise")
    assert r.status_code == 302 and web.services().configurations.get(cid + 1).version == 2


class FakeManager:
    def __init__(self, sharpe):
        self.sharpe = sharpe
        cycle = SimpleNamespace(ticker_to_entity={"JPM": 1}, universe_id=1)
        self.runner = SimpleNamespace(algorithm_instance=SimpleNamespace(cycle=cycle, cycle_results=[]))

    def run(self):
        table = pd.DataFrame({"Sharpe": [self.sharpe]}, index=["M"])
        return {"report": SimpleNamespace(model_name="M", period=("a", "b"), n_sessions=3, table_performance=table)}


def _finished_experiment(web, name, sharpe, **sections):
    cid = _create(web, name)
    s = web.services()
    s.configurations.update(cid, sections)
    e = s.experiments.launch(cid)
    run_experiment(e.id, s.experiment_repository, s.configuration_repository,
                   manager_factory=lambda a, n, d: FakeManager(sharpe))
    s.session.close()
    return e.id


def test_experiments_are_compared_side_by_side_with_comparability_warnings(web):
    a = _finished_experiment(web, "a", 1.1)
    b = _finished_experiment(web, "b", 0.7, model={"n_trials": 10},
                             evaluation={"backtest_end": "2026-08-31 16:00:00"})
    html = web.client.get(f"/strategies/compare?ids={a},{b}").get_data(as_text=True)
    assert "1.1000" in html and "0.7000" in html
    assert "n_trials" in html and "different backtest periods" in html
    assert web.client.get(f"/strategies/experiments/{a}/report").status_code == 404     # no stored report


def test_the_experiment_report_is_the_projects_own_report(web):
    from src.application.managers.project_managers.cross_sectionnal_project.backtesting.synthetic_demo import (
        run_synthetic_demo,
    )
    from src.application.services.data.entities.factor.spatio_temporal_momentum import stm_report_store
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import (
        STMProgressTracker,
    )
    eid = _finished_experiment(web, "with report", 0.9)
    tracker = STMProgressTracker(persist_path=None)
    tracker.start("demo")
    report = run_synthetic_demo(tracker, backtest_sessions=4, n_trials=3, training_window=60,
                                tickers=[f"T{i}" for i in range(6)])
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_report_renderer import build_pdf
    stm_report_store.save_report(report, web.services().experiments.get(eid).results_dir, pdf_builder=build_pdf)
    html = web.client.get(f"/strategies/experiments/{eid}/report").get_data(as_text=True)
    assert "Performance per Score Quintile" in html and "data:image/png;base64," in html
    assert web.client.get(f"/strategies/experiments/{eid}/report.pdf").data.startswith(b"%PDF")
