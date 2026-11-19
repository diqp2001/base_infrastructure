"""
Universe persistence on SQLite (real CompanyShare / factor rows, so the foreign keys are exercised):
Universe -> UniverseFinancialAsset -> FinancialAsset, Universe -> UniverseFactor -> Factor, InvestmentUniverse as a
child type of Universe, duplicate membership refused by the repositories and by the unique constraints.
"""

from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.universe.investment_universe import InvestmentUniverse
from src.domain.entities.universe.universe import DuplicateMembership, Universe
from src.domain.entities.universe.universe_constituent import UniverseConstituent
from src.domain.entities.universe.universe_factor import UniverseFactor
from src.domain.entities.universe.universe_financial_asset import UniverseFinancialAsset
from src.infrastructure.models import ModelBase
from src.infrastructure.models.factor.factor import CompanyShareFactorModel
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
from src.infrastructure.models.factor.factor import FactorModel
from src.infrastructure.models.universe.universe_financial_asset import UniverseFinancialAssetModel
from src.infrastructure.repositories.repository_factory import RepositoryFactory


@pytest.fixture
def world(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'universe.db'}")
    ModelBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    factory = RepositoryFactory(session)
    shares = {t: factory.company_share_local_repo.add(CompanyShare(id=None, symbol=t, exchange_id=1, company_id=1,
                                                                   currency_id=1, start_date=date(2020, 1, 1)))
              for t in ("JPM", "BAC", "GS")}
    factors = []
    for name in ("close", "volume"):
        row = CompanyShareFactorModel(name=name, group="price", subgroup="TRADES", frequency="1d",
                                      data_type="numeric", source="ibkr", definition=name,
                                      factor_type="company_share_factor")
        session.add(row)
        session.commit()
        factors.append(row.id)
    yield type("W", (), dict(session=session, factory=factory, shares=shares, factors=factors, engine=engine))
    session.close()
    engine.dispose()


def test_a_universe_is_persisted_and_retrieved_with_its_members(world):
    repo = world.factory.universe_local_repo
    u = Universe("US banks", description="banks", version=1)
    u.add_financial_asset(world.shares["JPM"].id)
    u.add_financial_asset(world.shares["BAC"].id, start_date=date(2021, 1, 1), end_date=date(2022, 1, 1))
    u.add_factor(world.factors[0])
    stored = repo.add(u)
    assert stored.id is not None and all(m.id and m.universe_id == stored.id for m in stored.financial_assets)

    world.session.expire_all()
    again = repo.get_by_id(stored.id)
    assert (again.name, again.description, again.universe_type, again.version) == ("US banks", "banks",
                                                                                  "Universe", 1)
    assert again.created_at is not None and again.updated_at is not None
    assert again.financial_asset_ids() == [world.shares["JPM"].id, world.shares["BAC"].id]
    assert again.financial_asset_ids(on=date(2023, 1, 1)) == [world.shares["JPM"].id]
    assert again.factor_ids() == [world.factors[0]]
    assert repo.get_by_name("US banks").id == stored.id


def test_universe_members_resolve_to_the_financial_assets_and_factors(world):
    repo = world.factory.universe_local_repo
    u = repo.add(Universe("mixed"))
    repo.add_financial_asset(u.id, world.shares["GS"].id)
    repo.add_factor(u.id, world.factors[1])
    members = world.factory.universe_financial_asset_local_repo.get_by_universe(u.id)
    assert [world.session.get(FinancialAssetModel, m.financial_asset_id).symbol for m in members] == ["GS"]
    factor_members = world.factory.universe_factor_local_repo.get_by_universe(u.id)
    assert [world.session.get(FactorModel, m.factor_id).name for m in factor_members] == ["volume"]


def test_constituent_management_through_the_repository(world):
    repo = world.factory.universe_local_repo
    u = repo.add(Universe("managed"))
    jpm, bac = world.shares["JPM"].id, world.shares["BAC"].id
    repo.add_financial_asset(u.id, jpm)
    repo.add_financial_asset(u.id, bac)
    with pytest.raises(DuplicateMembership):
        repo.add_financial_asset(u.id, jpm)
    assert repo.remove_financial_asset(u.id, jpm)
    assert repo.get_by_id(u.id).financial_asset_ids() == [bac]
    repo.add_factor(u.id, world.factors[0])
    with pytest.raises(DuplicateMembership):
        repo.add_factor(u.id, world.factors[0])
    assert repo.remove_factor(u.id, world.factors[0]) and repo.get_by_id(u.id).factor_ids() == []
    assert world.session.query(UniverseFinancialAssetModel).count() == 1      # removed member deleted


def test_universe_update_and_delete(world):
    repo = world.factory.universe_local_repo
    u = repo.add(Universe("to change"))
    u.description = "changed"
    u.add_factor(world.factors[0])
    repo.update(u)
    assert repo.get_by_id(u.id).description == "changed"
    assert repo.delete(u.id) and repo.get_by_id(u.id) is None
    assert world.factory.universe_factor_local_repo.get_by_universe(u.id) == []     # members go with it


def test_membership_repositories_refuse_duplicates(world):
    u = world.factory.universe_local_repo.add(Universe("rows"))
    assets = world.factory.universe_financial_asset_local_repo
    first = assets.add(UniverseFinancialAsset(u.id, world.shares["JPM"].id, start_date=date(2020, 1, 1),
                                              end_date=date(2021, 1, 1)))
    assert first.id is not None
    assets.add(UniverseFinancialAsset(u.id, world.shares["JPM"].id, start_date=date(2021, 1, 1)))   # adjacent
    with pytest.raises(DuplicateMembership):
        assets.add(UniverseFinancialAsset(u.id, world.shares["JPM"].id, start_date=date(2020, 6, 1),
                                          end_date=date(2020, 7, 1)))
    assert [m.start_date for m in assets.get_by_universe(u.id, on=date(2020, 3, 1))] == [date(2020, 1, 1)]
    factors = world.factory.universe_factor_local_repo
    factors.add(UniverseFactor(u.id, world.factors[0]))
    with pytest.raises(DuplicateMembership):
        factors.add(UniverseFactor(u.id, world.factors[0]))


def test_the_database_constraints_back_up_the_rules(world):
    u = world.factory.universe_local_repo.add(Universe("constraints"))
    sql = "INSERT INTO universe_factors (universe_id, factor_id) VALUES (:u, :f)"
    world.session.execute(text(sql), {"u": u.id, "f": world.factors[0]})
    world.session.commit()
    with pytest.raises(IntegrityError):                                     # UNIQUE(universe_id, factor_id)
        world.session.execute(text(sql), {"u": u.id, "f": world.factors[0]})
    world.session.rollback()
    world.session.execute(text("PRAGMA foreign_keys = ON"))               # SQLite checks FKs only when asked
    with pytest.raises(IntegrityError):                                     # FK onto financial_assets
        world.session.execute(text("INSERT INTO universe_financial_assets (universe_id, financial_asset_id) "
                                   "VALUES (:u, 999999)"), {"u": u.id})
    world.session.rollback()
    for column in ("weight", "rank"):
        for table in ("universe_financial_assets", "universe_factors"):
            assert column not in {c.name for c in ModelBase.metadata.tables[table].columns}


def test_an_investment_universe_is_a_child_of_universe(world):
    investment = world.factory.investment_universe_local_repo._create_or_get(
        InvestmentUniverse, "DIA holdings", entity_type="CompanyShare", currency_id=1)
    assert isinstance(investment, InvestmentUniverse) and investment.universe_type == "InvestmentUniverse"
    # same id in both tables
    assert world.session.execute(text("SELECT universe_type FROM universes WHERE id = :i"),
                                 {"i": investment.id}).scalar() == "InvestmentUniverse"
    assert world.session.execute(text("SELECT entity_type FROM investment_universes WHERE id = :i"),
                                 {"i": investment.id}).scalar() == "CompanyShare"
    # its dated / weighted history stays in universe_constituents
    world.factory.universe_constituent_local_repo.add(UniverseConstituent(
        universe_id=investment.id, entity_id=world.shares["JPM"].id, entity_type="CompanyShare",
        start_date=date(2025, 1, 1), weight=0.1))
    # the generic Universe repository reads it as its own type, and it can hold plain members too
    generic = world.factory.universe_local_repo.get_by_id(investment.id)
    assert isinstance(generic, InvestmentUniverse) and generic.entity_type == "CompanyShare"
    world.factory.universe_local_repo.add_financial_asset(investment.id, world.shares["GS"].id)
    assert world.factory.investment_universe_local_repo.get_by_name("DIA holdings").financial_asset_ids() == [
        world.shares["GS"].id]
    assert [u.name for u in world.factory.universe_local_repo.get_by_type("InvestmentUniverse")] == ["DIA holdings"]


def test_universe_versions(world):
    repo = world.factory.universe_local_repo
    repo.add(Universe("versioned", version=1))
    repo.add(Universe("versioned", version=2, description="v2"))
    assert repo.latest_version_number("versioned") == 2
    assert repo.get_by_name("versioned").description == "v2"
    assert repo.get_by_name("versioned", version=1).version == 1
    with pytest.raises(IntegrityError):
        repo.add(Universe("versioned", version=2))
