"""
ShareOption Repository for local database operations: everything common to options on a share
(CompanyShareOption, ETFShareOption). A subclass names its mapper, the underlying's ORM model and the factory key
of the underlying's repository.
"""

import logging
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.options_repository import OptionsRepository

logger = logging.getLogger(__name__)


class ShareOptionRepository(OptionsRepository):
    """Repository for options written on a share."""

    mapper_class = None              # a ShareOptionMapper subclass
    underlying_model = None          # ORM model of the underlying share
    underlying_repository_key = None # factory key of the underlying's local repository

    def __init__(self, session: Session, factory):
        super().__init__(session, factory)
        self.mapper = self.mapper_class()

    @property
    def model_class(self):
        return self.mapper.model_class

    @property
    def entity_class(self):
        return self.mapper.entity_class

    @property
    def _label(self) -> str:
        return self.mapper.discriminator

    def _create_or_get(self, ticker: str = None, name: str = None, symbol: str = None,
                      currency_code: str = "USD", option_type: str = None,
                      underlying_asset_id: int = None, strike_price=None, expiry: str = None,
                      multiplier=None, exchange_id: int = None, start_date: date = None):
        """
        Get or create an option with dependency resolution.

        Args:
            ticker: Option ticker or OCC symbol (optional). When called via
                    EntityService the entity class is passed here; we detect
                    that and fall through to the ``name``/``symbol`` lookup.
            name: Option name or OCC symbol (optional)
            symbol: Option symbol (optional)
            currency_code: Currency ISO code (default: USD)
            option_type: Type of option (CALL/PUT)
            underlying_asset_id: ID of the underlying share
            strike_price, expiry (YYYYMMDD), multiplier: contract terms
            exchange_id: listing exchange (default: the underlying's exchange)
            start_date: first day the option is known (default: today)

        Returns:
            Domain option entity or None if creation failed
        """
        try:
            # EntityService calls _create_or_get(entity_cls, occ_symbol).
            # entity_cls is a class, not a string → skip ticker lookup and use
            # the name/symbol argument as the OCC symbol identifier instead.
            if ticker is not None and not isinstance(ticker, str):
                symbol = symbol or name
                ticker = None

            # First try to get existing option by ticker or symbol.
            # get_by_symbol searches the `symbol` column on financial_assets.
            # Creation always stores the value in the `symbol` column.
            if ticker:
                existing = self.get_by_symbol(ticker)
                if existing:
                    return existing
            if symbol:
                existing = self.get_by_symbol(symbol)
                if existing:
                    return existing

            # Validate the underlying exists and has the right type if provided
            if underlying_asset_id:
                underlying = self.session.query(self.underlying_model).filter(
                    self.underlying_model.id == underlying_asset_id
                ).first()

                if not underlying:
                    logger.error(f"Underlying {self.underlying_repository_key} with ID {underlying_asset_id} does not exist")
                    return None
                if exchange_id is None:
                    exchange_id = underlying.exchange_id

            # Get or create currency dependency
            currency_local_repo = self.factory.currency_local_repo
            currency = currency_local_repo._create_or_get(currency_code)

            new_option = self.entity_class(
                id=None,
                name=name or f"{self._label} {ticker or symbol}",
                symbol=symbol or ticker,
                currency_id=currency.id if currency else None,
                underlying_asset_id=underlying_asset_id,
                exchange_id=exchange_id,
                option_type=option_type or "call",
                start_date=start_date or date.today(),
                strike_price=strike_price,
                multiplier=multiplier,
                expiry=expiry,
            )

            return self.add(new_option)

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error in get_or_create for {self._label} {ticker or symbol}: {e}")
            return None

    def add(self, option):
        """
        Add a single option to the database.

        :param option: Domain option entity to add
        :return: The saved option entity with assigned ID
        :raises: IntegrityError if option already exists
        """
        try:
            orm_option = self.mapper.to_orm(option)
            self.session.add(orm_option)
            self.session.flush()
            self.session.commit()
            return self.mapper.to_domain(orm_option)

        except IntegrityError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding option {option}: {e}")
            raise

    def get_by_symbol(self, symbol: str):
        """This repository's option with this symbol (OptionsRepository searches every option type)."""
        orm_option = self.session.query(self.model_class).filter(self.model_class.symbol == symbol).first()
        return self.mapper.to_domain(orm_option) if orm_option else None

    def get_by_underlying_id(self, underlying_asset_id: int) -> list:
        """Options written on one underlying share."""
        try:
            orm_options = self.session.query(self.model_class).filter(
                self.model_class.underlying_asset_id == underlying_asset_id
            ).all()
            return [self.mapper.to_domain(orm_option) for orm_option in orm_options]

        except Exception as e:
            logger.error(f"Error retrieving {self._label} by underlying ID {underlying_asset_id}: {e}")
            raise

    def get_by_option_type(self, option_type: str) -> list:
        """Options of one type (call / put)."""
        try:
            orm_options = self.session.query(self.model_class).filter(
                self.model_class.option_type == option_type.lower()
            ).all()
            return [self.mapper.to_domain(orm_option) for orm_option in orm_options]

        except Exception as e:
            logger.error(f"Error retrieving {self._label} by option type {option_type}: {e}")
            raise

    def get_active_options(self) -> list:
        """Options whose end_date is None or in the future."""
        try:
            current_date = date.today()
            orm_options = self.session.query(self.model_class).filter(
                (self.model_class.end_date.is_(None)) |
                (self.model_class.end_date > current_date)
            ).all()
            return [self.mapper.to_domain(orm_option) for orm_option in orm_options]

        except Exception as e:
            logger.error(f"Error retrieving active {self._label}: {e}")
            raise

    def get_related_entities(self, option_id: int) -> list:
        """Return the underlying share and settlement Currency for this option.

        The resolution service uses these to route calculate_dependencies:
        - the underlying's value factor  → the underlying share (underlying price)
        - the option's RF yield / implied vol factors → the option itself
          (appended by _get_resolution_entities after this call)
        - CurrencyYieldFactor chain (via stored DB deps) → Currency
        """
        if not self.factory:
            return []
        try:
            orm_option = (
                self.session.query(self.model_class)
                .filter(self.model_class.id == option_id)
                .one_or_none()
            )
            if not orm_option:
                return []

            result = []

            if orm_option.underlying_asset_id:
                share_repo = self.factory.get_local_repository(self.underlying_repository_key)
                if share_repo:
                    underlying = share_repo.get_by_id(orm_option.underlying_asset_id)
                    if underlying:
                        result.append(underlying)

            if orm_option.currency_id:
                currency_repo = self.factory.get_local_repository('Currency')
                if currency_repo:
                    currency = currency_repo.get_by_id(orm_option.currency_id)
                    if currency:
                        result.append(currency)

            return result
        except Exception as e:
            logger.error(f"Error getting related entities for {self._label} (option_id={option_id}): {e}")
            return []
