"""
/powerbuffet/model-evaluation on fake repositories: the page renders every section for a 5-class and a binary
model, the probability selector and the run API work, CSV exports carry the evaluation's numbers.
"""

from types import SimpleNamespace

import pytest

from src.application.services.model_evaluation.classifier_evaluation_service import ClassifierEvaluationService
from src.application.services.model_evaluation.classifier_sources import CSMObservationSource
from tests.model_evaluation.test_classifier_sources import CSM_KEY, _csm_world, _lgbm_source, _lgbm_world


@pytest.fixture
def client():
    from src.interfaces.flask.app import FlaskApp
    lgbm_source, _ = _lgbm_source(_lgbm_world())
    csm_factory, csm_data, _, _ = _csm_world()
    service = ClassifierEvaluationService([lgbm_source, CSMObservationSource(csm_factory, csm_data)])
    fake = SimpleNamespace(session=None, model_evaluation=service,
                           data=SimpleNamespace(universes=lambda: [{"id": 1, "name": "test universe"}]))
    app = FlaskApp().get_app()
    app.config.update(FACTOR_SERVICES_FACTORY=lambda: fake, TESTING=True)
    return app.test_client()


Q5 = "/powerbuffet/model-evaluation?run=1&model=lgbm_quintile:3&universe_id=1&start=2024-01-01&end=2024-03-20"


def test_the_page_lists_models_and_evaluates_a_five_class_model(client):
    html = client.get("/powerbuffet/model-evaluation").get_data(as_text=True)
    assert "lgbm_mom_abc" in html and "csm_lightgbm_x" in html and "Evaluate" in html
    html = client.get(Q5).get_data(as_text=True)
    for section in ("1. Classification", "Balanced accuracy", "Macro F1", "Log loss", "Confusion matrix",
                    "2. Probability quintiles", "3. Cumulative returns", "4. Correlation", "monotonicity"):
        assert section in html, section
    # confusion x2, binary x2, quintile x2, cumulative, correlation
    assert html.count("data:image/png;base64,") == 8
    assert "1b. Binary and quintile confusion matrices" in html and "expected class" in html
    assert "P(Q5) quintiles" in html
    html = client.get(Q5 + "&prob_class=1").get_data(as_text=True)
    assert "P(Q1) quintiles" in html


def test_the_page_evaluates_a_binary_model_and_one_run(client):
    html = client.get(f"/powerbuffet/model-evaluation?run=1&model={CSM_KEY}&run_id=2002&universe_id=1"
                      "&start=2024-01-01&end=2024-03-28").get_data(as_text=True)
    assert "P(class 1) quintiles" in html and "1. Classification" in html
    assert client.get(f"/powerbuffet/model-evaluation/api/runs?model={CSM_KEY}").get_json()[1]["run_id"] == 2002


def test_csv_exports_and_errors(client):
    obs = client.get(Q5.replace("model-evaluation?", "model-evaluation/csv?") + "&part=observations")
    head = obs.get_data(as_text=True).splitlines()[0]
    assert obs.status_code == 200 and all(c in head for c in ("true_class", "predicted_class", "forward_return",
                                                                "p_1", "p_5", "run_id"))
    conf = client.get(Q5.replace("model-evaluation?", "model-evaluation/csv?") + "&part=confusion")
    assert conf.get_data(as_text=True).splitlines()[0] == ",pred Q1,pred Q2,pred Q3,pred Q4,pred Q5"
    assert client.get(Q5.replace("model-evaluation?", "model-evaluation/csv?") + "&part=nope").status_code == 400
    binary = client.get(Q5.replace("model-evaluation?", "model-evaluation/csv?") + "&part=binary")
    assert binary.get_data(as_text=True).splitlines()[0] == ",pred below median,pred above median"
    quint = client.get(Q5.replace("model-evaluation?", "model-evaluation/csv?") + "&part=quintile")
    assert quint.get_data(as_text=True).splitlines()[0] == ",pred Q1,pred Q2,pred Q3,pred Q4,pred Q5"
    html = client.get(Q5.replace("lgbm_quintile:3", "lgbm_quintile:999")).get_data(as_text=True)
    assert "unknown classifier model" in html
