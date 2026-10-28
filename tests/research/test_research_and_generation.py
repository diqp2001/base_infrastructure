"""Factor research, factor value generation and the research web pages, on a file-based SQLite database with the
real repositories and resolution service (temp dirs; no IBKR, no SQL Server, no worker process)."""

import re
from datetime import date
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.application.services.research.factor_generation import (
    FactorGenerationService,
    GenerationJobs,
    GenerationRequest,
    decision_times,
    run_job,
)
from src.application.services.research.factor_research import (
    ResearchConfig,
    analyse_panels,
    membership_mask,
    to_bars,
)

SESSIONS = pd.bdate_range("2026-03-02", periods=40)
TICKERS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]


@pytest.fixture
def db(tmp_path, monkeypatch):
    from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
    from src.domain.entities.universe.universe import Universe
    from src.domain.entities.universe.universe_constituent import UniverseConstituent
    from src.infrastructure.models import ModelBase
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    monkeypatch.setenv("MONITOR_STATE_DIR", str(tmp_path / "monitor"))
    engine = create_engine(f"sqlite:///{tmp_path / 'research.db'}")
    ModelBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    factory = RepositoryFactory(session)
    ids = {}
    for t in TICKERS:
        share = factory.company_share_local_repo.add(CompanyShare(id=None, symbol=t, exchange_id=1, company_id=1,
                                                                  currency_id=1, start_date=date(2020, 1, 1)))
        ids[t] = share.id
    rng = np.random.default_rng(5)
    close = CompanyShareFactorModel(name="close", group="price", subgroup="TRADES", frequency="1d",
                                    data_type="numeric", source="ibkr", definition="close",
                                    factor_type="company_share_factor")
    session.add(close)
    session.commit()
    prices = {t: 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(SESSIONS)))) for t in TICKERS}
    session.add_all([FactorValueModel(factor_id=close.id, entity_id=ids[t], entity_type="CompanyShare",
                                      date=d.to_pydatetime(), value=repr(float(prices[t][i])))
                     for t in TICKERS for i, d in enumerate(SESSIONS)])
    session.commit()
    universe = factory.investment_universe_local_repo._create_or_get(Universe, "test_u", entity_type="CompanyShare")
    for t in TICKERS:
        end = date(2026, 3, 20) if t == "FFF" else None                      # FFF leaves the universe
        factory.universe_constituent_local_repo.add(UniverseConstituent(
            universe_id=universe.id, entity_id=ids[t], entity_type="CompanyShare", start_date=date(2026, 1, 1),
            end_date=end))
    calc = {}
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_return_factors import (
        CompanyShareReturn1DFactor, CompanyShareReturn5DFactor,
    )
    for cls in (CompanyShareReturn1DFactor, CompanyShareReturn5DFactor):
        repo = factory.get_local_repository(cls.__name__)
        o = cls()
        f = repo._create_or_get(cls, o.name, group=o.group, subgroup=o.subgroup, frequency="1d",
                                data_type="numeric", source="calculated")
        calc[o.name] = f.id
    yield SimpleNamespace(session=session, Session=Session, factory=factory, ids=ids, universe=universe,
                          close_id=close.id, calc=calc, prices=prices, tmp=tmp_path)
    session.close()
    engine.dispose()


# ── research on panels (no database) ─────────────────────────────────────────────────────────────────────────────

def test_point_in_time_membership_masks_values_outside_membership():
    idx = pd.DatetimeIndex(["2026-03-02", "2026-03-20", "2026-03-23"])
    mask = membership_mask(idx, [1, 2], [(1, date(2026, 1, 1), date(2026, 3, 20)), (2, date(2026, 3, 3), None)])
    assert mask[1].tolist() == [True, False, False]               # end date excluded
    assert mask[2].tolist() == [False, True, True]                # not yet a member on 03-02


def test_values_are_mapped_to_their_bar_and_paired_with_the_return_after_it():
    raw = pd.DataFrame({1: [1.0, 2.0, 3.0]}, index=pd.DatetimeIndex(["2026-03-02 00:00", "2026-03-02 16:00",
                                                                        "2026-03-03 16:00"]))
    bars = to_bars(raw, "1d")
    assert list(bars.index) == [pd.Timestamp("2026-03-02"), pd.Timestamp("2026-03-03")] and bars.iloc[0, 0] == 2.0
    tenm = to_bars(pd.DataFrame({1: [5.0]}, index=pd.DatetimeIndex(["2026-03-02 10:13"])), "10m")
    assert tenm.index[0] == pd.Timestamp("2026-03-02 10:10")


def test_analyse_panels_separates_the_correlation_notions_and_forms_quantiles():
    rng = np.random.default_rng(2)
    idx = pd.bdate_range("2026-01-02", periods=60)
    cols = list(range(10))
    a = pd.DataFrame(rng.normal(size=(60, 10)), index=idx, columns=cols)
    b = a * 2 + rng.normal(0, 0.1, (60, 10))
    closes = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (61, 10)), axis=0)),
                          index=pd.bdate_range("2026-01-02", periods=61), columns=cols)
    mask = pd.DataFrame(True, index=closes.index, columns=cols)
    cfg = ResearchConfig(universe_id=1, start="2026-01-02", end="2026-03-31", frequency="1d", primary_factor_id=1,
                         comparison_factor_ids=[2], method="spearman", horizons=[1, 5])
    r = analyse_panels(cfg, {1: a, 2: b}, {1: "A", 2: "B"}, closes, mask)
    assert r.pooled[2].value > 0.95 and r.pooled[2].n == 600
    assert r.cross_sectional[2].summary["mean"] > 0.95 and r.cross_sectional[2].summary["dates_with_value"] == 60
    assert r.matrix.loc["A", "B"] == pytest.approx(r.pooled[2].value)
    assert list(r.quantiles.returns.columns)[-1] == "Q5 - Q1" and set(r.ic_by_horizon) == {1, 5}
    assert r.quantile_performance["Q5 - Q1"]["observations"] == 60      # last row has a forward return (61 closes)
    with pytest.raises(ValueError):
        analyse_panels(cfg, {1: pd.DataFrame(), 2: b}, {1: "A", 2: "B"}, closes, mask)


# ── research and generation on the database ─────────────────────────────────────────────────────────────────────

def _seed_calculated(db, name, values_by_ticker):
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    db.session.add_all([FactorValueModel(factor_id=db.calc[name], entity_id=db.ids[t], entity_type="CompanyShare",
                                         date=(d + pd.Timedelta(hours=16)).to_pydatetime(), value=repr(float(v)))
                        for t, series in values_by_ticker.items() for d, v in zip(SESSIONS, series)])
    db.session.commit()


def test_research_reads_stored_values_with_point_in_time_membership(db):
    from src.application.services.research.factor_research import FactorResearchData, FactorResearchService
    rng = np.random.default_rng(3)
    _seed_calculated(db, "return_1d", {t: rng.normal(size=len(SESSIONS)) for t in TICKERS})
    _seed_calculated(db, "return_5d", {t: rng.normal(size=len(SESSIONS)) for t in TICKERS})
    service = FactorResearchService(FactorResearchData(db.factory))
    cfg = ResearchConfig(universe_id=db.universe.id, start="2026-03-01", end="2026-04-30", frequency="1d",
                         primary_factor_id=db.calc["return_1d"], comparison_factor_ids=[db.calc["return_5d"]],
                         min_assets=3, n_quantiles=3)
    r = service.run(cfg)
    assert r.securities == 6
    after = [t for t in r.primary_profile.index if t >= pd.Timestamp("2026-03-20")]
    assert all(r.primary_profile.loc[t, "count"] == 5 for t in after)  # FFF dropped from its end date
    assert r.quantiles is not None and r.matrix_counts.iloc[0, 1] > 0
    assert any("point-in-time" in n for n in r.notes)


def test_generation_plan_refuses_other_frequencies_and_raw_series(db):
    gen = FactorGenerationService(db.factory)
    plan = gen.plan(GenerationRequest(db.universe.id, "2026-03-16", "2026-03-27", "1h",
                                      factor_ids=[db.calc["return_1d"], db.close_id]))
    assert "defined at 1d, not 1h" in plan["refused"][db.calc["return_1d"]]
    assert "imported" in plan["refused"][db.close_id] and plan["errors"]
    ok = gen.plan(GenerationRequest(db.universe.id, "2026-03-16", "2026-03-27", "1d", all_eligible=True))
    assert not ok["errors"] and ok["timestamps"] == 10
    assert ok["constituent_timestamps"] == 10 * 5 + 4                  # FFF a member on 03-16..03-19 only
    assert ok["calculations"] == ok["constituent_timestamps"] * 2


def test_generation_computes_through_the_resolver_and_is_idempotent(db):
    gen = FactorGenerationService(db.factory)
    req = GenerationRequest(db.universe.id, "2026-03-16", "2026-03-20", "1d", factor_ids=[db.calc["return_5d"]])
    first = gen.run(req)
    assert first["generated"] > 0 and first["failed"] == 0, first["report"][:3]
    assert first["generated"] + first["missing_input"] == first["calculations"]
    v = db.factory.factor_value_local_repo.get_by_factor_entity_date(
        db.calc["return_5d"], db.ids["AAA"], "2026-03-18 16:00:00", "CompanyShare")
    p = db.prices["AAA"]
    i = list(SESSIONS).index(pd.Timestamp("2026-03-17"))               # closed bars at 03-18 16:00: up to 03-17
    assert float(v.value) == pytest.approx(p[i] / p[i - 5] - 1.0, rel=1e-6)   # no look-ahead
    again = gen.run(req)
    assert again["generated"] == 0 and again["existing"] == first["generated"] and again["updated"] == 0


def test_decision_times_are_bar_closes_of_the_exchange_calendar():
    daily = decision_times("2026-07-02", "2026-07-07", "1d")
    assert list(daily) == [pd.Timestamp("2026-07-02 16:00"), pd.Timestamp("2026-07-06 16:00"),
                           pd.Timestamp("2026-07-07 16:00")]                 # 07-03 holiday
    ten = decision_times("2026-10-05", "2026-10-05", "10m")
    assert ten[0] == pd.Timestamp("2026-10-05 09:40") and ten[-1] == pd.Timestamp("2026-10-05 16:00") and len(ten) == 39


def test_generation_jobs_record_status_and_refuse_a_duplicate_scope(db, tmp_path):
    jobs = GenerationJobs(root=tmp_path / "jobs", starter=lambda job: 4242, is_alive=lambda pid: True)
    req = GenerationRequest(db.universe.id, "2026-03-16", "2026-03-17", "1d", factor_ids=[db.calc["return_1d"]])
    job = jobs.launch(req)
    assert job["status"] == "queued" and job["pid"] == 4242
    with pytest.raises(RuntimeError):
        jobs.launch(req)
    done = run_job(job["id"], jobs, FactorGenerationService(db.factory))
    assert done["status"] == "completed" and done["summary"]["generated"] > 0
    dead = GenerationJobs(root=tmp_path / "jobs2", starter=lambda job: 1, is_alive=lambda pid: False)
    j = dead.launch(req)
    j2 = dead.read(j["id"])
    j2["status"] = "running"
    dead.write(j2)
    assert dead.read(j["id"])["status"] == "interrupted"


# ── web ──────────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def web(db, tmp_path):
    from src.application.services.research.project_returns import ProjectReturnsService, ResultSource
    from src.application.services.research.research_services import ResearchServices
    from src.application.services.data.entities.factor.spatio_temporal_momentum import stm_report_store
    from src.infrastructure.research.factor_return_files import FactorReturnFileStore
    from src.interfaces.flask.app import FlaskApp
    rng = np.random.default_rng(8)
    idx = pd.bdate_range("2026-01-02", periods=120)
    mkt = rng.normal(0.0004, 0.01, len(idx))
    store = FactorReturnFileStore(tmp_path / "factor_returns")
    store.save("ff3_test", pd.DataFrame({"MKT_RF": mkt, "SMB": rng.normal(0, 0.005, len(idx)),
                                         "HML": rng.normal(0, 0.005, len(idx)), "RF": 0.0001}, index=idx),
               kind="external", frequency="D", source="test")
    model = 0.9 * pd.Series(mkt, index=idx).shift(-1) + rng.normal(0, 0.001, len(idx))   # decision-stamped
    report = SimpleNamespace(model_name="MODEL", returns=pd.DataFrame({"MODEL": model, "Long Only (EW)": model + 0.0001},
                                                                      index=idx).dropna())
    stm_report_store.save_report(report, str(tmp_path / "csm"), render_pdf=False)
    returns = ProjectReturnsService(sources=[ResultSource("csm:test", "Test project", "csm", lambda: str(tmp_path / "csm"))])

    def factory():
        s = ResearchServices(db.Session(), factor_return_store=store, returns_service=returns)
        s.jobs = GenerationJobs(root=tmp_path / "web_jobs", starter=lambda job: 777, is_alive=lambda pid: True)
        return s

    app = FlaskApp().get_app()
    app.config.update(RESEARCH_SERVICES_FACTORY=factory, TESTING=True)
    return SimpleNamespace(client=app.test_client(), db=db)


def test_factor_analysis_page_runs_a_regression_on_a_projects_returns(web):
    c = web.client
    html = c.get("/factor-analysis/?source=csm:test").get_data(as_text=True)
    assert "Run factor analysis" in html and "MODEL" in html
    q = "source=csm:test&run=1&strategy=MODEL&factor_set=ff3_test&model=ff3&frequency=D&rolling_window=40&compare=Long+Only+(EW)"
    html = c.get(f"/factor-analysis/?{q}").get_data(as_text=True)
    assert "A. Exposures" in html and "MKT_RF" in html and "E. Strategy comparison" in html
    csv = c.get(f"/factor-analysis/csv?{q}&part=coefficients").get_data(as_text=True)
    beta = float([l for l in csv.splitlines() if l.startswith("MKT_RF")][0].split(",")[1])
    assert beta == pytest.approx(0.9, abs=0.05)                    # the decision-stamped return was re-stamped
    assert c.get(f"/factor-analysis/csv?{q}&part=rolling").status_code == 200
    bad = c.get("/factor-analysis/?source=csm:test&run=1&factor_set=ff3_test&model=ff5").get_data(as_text=True)
    assert "has no" in bad and "RMW" in bad                         # FF5 without RMW/CMA data: refused


def test_research_and_generation_pages(web):
    db = web.db
    c = web.client
    assert c.get("/powerbuffet/research").status_code == 200
    gen = c.get("/powerbuffet/generate").get_data(as_text=True)
    assert "return_5d" in gen and "test_u" in gen
    form = {"universe_id": str(db.universe.id), "frequency": "1d", "start": "2026-03-16", "end": "2026-03-18",
            "factor_ids": [str(db.calc["return_5d"])]}
    plan = c.post("/powerbuffet/generate/plan", data=form).get_data(as_text=True)
    assert "calculations" in plan and "Launch" in plan
    r = c.post("/powerbuffet/generate/launch", data=form)
    assert r.status_code == 302 and "/powerbuffet/generate/jobs/" in r.headers["Location"]
    job_id = re.search(r"jobs/([^/?]+)", r.headers["Location"]).group(1)
    assert c.get(f"/powerbuffet/generate/jobs/{job_id}/status").get_json()["status"] == "queued"
    rng = np.random.default_rng(4)
    _seed_calculated(db, "return_1d", {t: rng.normal(size=len(SESSIONS)) for t in TICKERS})
    q = (f"run=1&universe_id={db.universe.id}&frequency=1d&start=2026-03-01&end=2026-04-30&method=spearman"
         f"&n_quantiles=3&horizons=1&primary_factor_id={db.calc['return_1d']}")
    html = c.get(f"/powerbuffet/research?{q}").get_data(as_text=True)
    assert "A. Correlation matrix" in html and "D. Quantile portfolios" in html
    assert c.get(f"/powerbuffet/research/csv?{q}&part=quantiles").status_code == 200
    saved = c.post("/powerbuffet/research/save-long-short", data={**dict(pair.split("=") for pair in q.split("&")),
                                                                   "name": "r1d_ls", "query": q})
    assert saved.status_code == 302
    sets = c.get("/factor-analysis/factor-returns").get_json()
    assert any(s["name"] == "r1d_ls" and s["kind"] == "mimicking_portfolio" for s in sets)


def test_calendar_pickers_are_limited_to_the_dates_with_stored_data(web):
    from src.application.services.research.factor_research import inclusive_end
    db = web.db
    c = web.client
    inputs = c.get(f"/powerbuffet/api/date-range?inputs=1&universe_id={db.universe.id}&frequency=1d").get_json()
    assert inputs == {"first": str(SESSIONS[0].date()), "last": str(SESSIONS[-1].date())}
    assert c.get(f"/powerbuffet/api/date-range?inputs=1&universe_id={db.universe.id}&frequency=1h").get_json() == \
        {"first": None, "last": None}                                     # no hourly closes stored
    empty = c.get(f"/powerbuffet/api/date-range?universe_id={db.universe.id}&factor_ids={db.calc['return_5d']}")
    assert empty.get_json() == {"first": None, "last": None}             # nothing generated yet
    for page in ("/powerbuffet/generate", "/powerbuffet/research", "/factor-analysis/?source=csm:test"):
        assert 'type="date"' in c.get(page).get_data(as_text=True), page
    assert 'data-first="' in c.get("/factor-analysis/?source=csm:test").get_data(as_text=True)
    assert inclusive_end("2026-03-20") == pd.Timestamp("2026-03-20 23:59:59.999999")
    assert inclusive_end("2026-03-20 10:00") == pd.Timestamp("2026-03-20 10:00")
