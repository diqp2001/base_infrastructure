"""BI-011: the single-value resolver (FactorValueResolutionService) detects dependency cycles. No DB."""

import logging
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from src.application.services.data.entities.factor.factor_value_resolution_service import (
    FactorValueResolutionService,
)

T = datetime(2026, 10, 20, 16, 0)


class CompanyShare(SimpleNamespace):
    pass


def service():
    return FactorValueResolutionService(factory=None, logger=logging.getLogger("cycle-guard-test"))


def test_a_value_that_needs_itself_is_a_cycle_not_a_recursion_error(caplog):
    svc, calls = service(), []
    a, b, share = SimpleNamespace(id=1, name="a"), SimpleNamespace(id=2, name="b"), CompanyShare(id=7)

    def resolve(factor, entity, when, **kwargs):              # a needs b, b needs a (same entity, same date)
        calls.append(factor.name)
        other = b if factor is a else a
        return svc.resolve_factor_value(other, entity, when)

    with patch.object(svc, "_resolve_factor_value", side_effect=resolve), caplog.at_level(logging.ERROR):
        assert svc.resolve_factor_value(a, share, T) is None
    assert calls == ["a", "b"]
    assert "Dependency cycle" in caplog.text and "1:CompanyShare:7 -> 2:CompanyShare:7 -> 1:CompanyShare:7" in caplog.text
    assert svc._resolving == []                                 # the stack unwinds


def test_the_same_factor_at_an_earlier_date_is_not_a_cycle():
    svc = service()
    a, share = SimpleNamespace(id=1, name="a"), CompanyShare(id=7)

    def resolve(factor, entity, when, **kwargs):              # value at t needs the value at t - 1 day (a lag)
        if when <= T - timedelta(days=3):
            return SimpleNamespace(id=None, value="1")
        return svc.resolve_factor_value(factor, entity, when - timedelta(days=1))

    with patch.object(svc, "_resolve_factor_value", side_effect=resolve):
        assert svc.resolve_factor_value(a, share, T).value == "1"


def test_repeated_requests_after_a_cycle_still_resolve():
    svc = service()
    a, share = SimpleNamespace(id=1, name="a"), CompanyShare(id=7)
    with patch.object(svc, "_resolve_factor_value", side_effect=lambda f, e, w, **k: svc.resolve_factor_value(f, e, w)):
        assert svc.resolve_factor_value(a, share, T) is None
    with patch.object(svc, "_resolve_factor_value", return_value=SimpleNamespace(id=None, value="2")):
        assert svc.resolve_factor_value(a, share, T).value == "2"
