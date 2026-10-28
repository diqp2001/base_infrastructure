"""Every project results page carries the shared Factor Analysis section, pointed at its own results source."""

import pathlib

import pytest

TEMPLATES = pathlib.Path(__file__).resolve().parents[2] / "src" / "interfaces" / "flask" / "web" / "templates"


@pytest.mark.parametrize("template,source", [
    ("stm_results.html", "'stm:' ~ project"),
    ("csm_results.html", "'csm:' ~ project"),
    ("spx_v2_results.html", "'spx_v2'"),
    ("strategies_report.html", "'experiment:' ~ e.id"),
])
def test_each_results_page_includes_the_factor_analysis_section(template, source):
    text = (TEMPLATES / template).read_text(encoding="utf-8")
    assert f"{{% set fa_source = {source} %}}{{% include \"_factor_analysis_section.html\" %}}" in text


def test_the_section_embeds_the_shared_page_for_its_source():
    from src.interfaces.flask.app import FlaskApp
    app = FlaskApp().get_app()
    with app.test_request_context():
        html = app.jinja_env.get_template("_factor_analysis_section.html").render(fa_source="stm:10m")
    assert "/factor-analysis/?source=stm%3A10m&embedded=1" in html and "Factor Analysis" in html


def test_every_project_results_source_is_registered():
    from src.application.services.research.project_returns import PROJECT_SOURCES
    keys = {s.key for s in PROJECT_SOURCES}
    assert {"stm:daily", "stm:full", "stm:10m", "csm:cross_sectional", "csm:csm_10m", "spx_v2"} <= keys
    for s in PROJECT_SOURCES:
        assert s.results_dir(), s.key                      # every project config resolves its results folder
