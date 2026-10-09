"""Shared fixtures for the Spatio-Temporal Momentum tests."""

from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
    STMModelConfig,
    STMTrainingConfig,
    STMUniverseConfig,
)

ASSETS = ["AAA", "BBB", "CCC", "DDD"]


def synthetic_closes(n_days: int = 1000, assets: List[str] = ASSETS, seed: int = 0,
                     start: str = "2015-01-01") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=n_days)
    rets = rng.normal(0.0003, 0.012, (n_days, len(assets)))
    return pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=dates, columns=assets)


def tiny_config(model_type: str = "tft", tmp_dir: str = None) -> STMConfiguration:
    """Small but structurally complete configuration (fast on CPU)."""
    cfg = STMConfiguration()
    cfg.universe = STMUniverseConfig(name="stm_test_universe", tickers=list(ASSETS))
    cfg.model = STMModelConfig(
        model_type=model_type,
        lookback=12,
        encoder_length=8 if model_type == "tft" else None,
        params={"hidden_dim": 8, "n_heads": 2, "prescale_dim": 4, "emb_dim": 4} if model_type == "tft" else {},
    )
    cfg.training = STMTrainingConfig(
        first_split_start="2016-09-01",
        last_split_start="2017-03-01",
        split_frequency_days=180,
        val_days=90,
        test_days=90,
        n_epochs=3,
        early_stopping_rounds=10,
        batch_size=32,
    )
    cfg.artifact_dir = tmp_dir
    return cfg


def make_factory():
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    return RepositoryFactory(session), session, engine


def seed_closes(session, closes: pd.DataFrame, entity_ids: Dict[str, int]) -> int:
    """Store closes as the raw daily CompanyShare 'close' factor (like IBKR max_import)."""
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    factor = CompanyShareFactorModel(name="close", group="price", subgroup="ohlc", frequency="1d",
                                     data_type="numeric", source="ibkr", definition="close",
                                     factor_type="company_share_factor")
    session.add(factor)
    session.commit()
    rows = []
    for d, row in closes.iterrows():
        for ticker, px in row.items():
            if pd.notna(px):
                rows.append({"factor_id": factor.id, "entity_id": entity_ids[ticker], "entity_type": "CompanyShare",
                             "date": pd.Timestamp(d).to_pydatetime(), "value": repr(float(px))})
    session.bulk_insert_mappings(FactorValueModel, rows)
    session.commit()
    return factor.id


def overwrite_closes_after(session, factor_id: int, entity_ids: Dict[str, int], after, multiplier: float) -> None:
    """Change stored closes strictly after ``after`` (simulates a different future)."""
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    rows = session.query(FactorValueModel).filter(
        FactorValueModel.factor_id == factor_id,
        FactorValueModel.date > pd.Timestamp(after).to_pydatetime(),
    ).all()
    for r in rows:
        r.value = repr(float(r.value) * multiplier)
    session.commit()
