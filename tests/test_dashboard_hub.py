"""
The /dashboard hub: every main page grouped with a link, live numbers from /dashboard/summary.json (fake services
stand for the database), one failing source reported without hiding the others, and the factor pages keeping their
own services next to the research registry's.
"""

from types import SimpleNamespace

import pytest

from src.interfaces.flask.app import FlaskApp


def _strategy(i, name, version=1):
    return SimpleNamespace(id=i, name=name, version=version, project_key="cross_sectional")


@pytest.fixture
def app():
    rows = [{"strategy": _strategy(1, "csm"), "assets": 30, "factors": 24},
            {"strategy": _strategy(2, "csm", 2), "assets": 31, "factors": 24},
            {"strategy": _strategy(3, "stm"), "assets": 10, "factors": 5}]
    strategies = SimpleNamespace(design=SimpleNamespace(overview=lambda: rows),
                                 experiments=SimpleNamespace(list=lambda: [1, 2]), session=None)
    books = [{"portfolio_id": 10, "name": "Demo_Portfolio", "first": "2026-06-01", "last": "2026-06-05",
              "final_value": 1_030_000.0, "total_return": 0.03, "live": False, "strategy": {"name": "csm"}}]
    research = SimpleNamespace(list_runs=lambda limit=200: [{}, {}], books=SimpleNamespace(books=lambda: books),
                               session=None)
    a = FlaskApp().get_app()
    a.config.update(STRATEGY_SERVICES_FACTORY=lambda: strategies, RESEARCH_SERVICES_FACTORY=lambda: research,
                    TESTING=True)
    return a


def test_the_hub_links_every_main_page(app):
    html = app.test_client().get("/dashboard").get_data(as_text=True)
    for path in ("/strategies/", "/research/backtests", "/research/", "/stm/", "/csm/", "/dispersion/",
                 "/powerbuffet/generate", "/factor-analysis/", "/powerbuffet", "/entity-upload", "/monitor/"):
        assert f'href="{path}"' in html, path
    assert "Legacy tools" in html


def test_the_summary_counts_strategies_and_backtests(app):
    d = app.test_client().get("/dashboard/summary.json").get_json()
    assert d["strategies"]["count"] == 2 and d["strategies"]["versions"] == 3 and d["strategies"]["experiments"] == 2
    assert [s["id"] for s in d["strategies"]["latest"]] == [3, 2, 1]
    assert d["backtests"]["count"] == 1 and d["backtests"]["latest"][0]["strategy"] == "csm"
    assert d["runs"]["count"] == 2 and d["errors"] == {}


def test_one_failing_source_leaves_the_others(app):
    def broken():
        raise RuntimeError("database down")
    app.config["STRATEGY_SERVICES_FACTORY"] = broken
    d = app.test_client().get("/dashboard/summary.json").get_json()
    assert "strategies" not in d and "database down" in d["errors"]["strategies"]
    assert d["backtests"]["count"] == 1


def test_factor_pages_do_not_take_the_research_registry_services(app):
    """Both used to share RESEARCH_SERVICES_FACTORY: whichever page came first broke the other."""
    app.config["FACTOR_SERVICES_FACTORY"] = lambda: SimpleNamespace(session=None)
    client = app.test_client()
    client.get("/dashboard/summary.json")
    from src.interfaces.flask.web.controllers import factor_analysis_controller as fa
    with app.test_request_context("/factor-analysis/"):
        assert fa.services() is not None and not hasattr(fa.services(), "books")
