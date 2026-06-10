"""
TradeManager – mechanics of the Order → Transaction → Position persistence pipeline.

Called exclusively by UnifiedPortfolioManager, which orchestrates when and what
to trade. TradeManager only knows *how* to persist the resulting domain entities.
"""

import uuid
from datetime import datetime
from typing import Any, Callable, Dict


class TradeManager:
    """
    Handles the low-level persistence side of a single trade:
      1. Register a domain Order entity
      2. Record a domain Transaction entity (simulated immediate fill)
      3. Upsert the domain Position entity to reflect the new quantity
    """

    def __init__(self, repository_factory, logger=None):
        self.order_repo = repository_factory.order_local_repo
        self.transaction_repo = repository_factory.transaction_local_repo
        self.position_repo = repository_factory.position_local_repo
        self.holding_repo = repository_factory.holding_local_repo
        self.logger = logger
        self._order_ticket_mapping: Dict[str, Any] = {}  # QC order_id → domain order id

    # ------------------------------------------------------------------
    # Public API (called by UnifiedPortfolioManager only)
    # ------------------------------------------------------------------

    def execute_trade(
        self,
        ticker: str,
        order_qty: int,
        price: float,
        portfolio_id: int,
        current_time: datetime,
        submit_order_fn: Callable,
        tag: str = "",
    ) -> bool:
        """
        Full pipeline: submit ticket → register Order → record Transaction → update Position.

        Args:
            ticker:          asset symbol string
            order_qty:       signed quantity (positive = buy, negative = sell)
            price:           fill price
            portfolio_id:    domain portfolio ID
            current_time:    algorithm time used for timestamps
            submit_order_fn: callable(ticker, qty) → OrderTicket
        """
        # 1. In-memory order ticket
        ticket = submit_order_fn(ticker, order_qty, tag=tag or f"set_holdings_{ticker}")
        if not ticket:
            return False

        # 2. Persist domain Order entity
        domain_order = self._register_order(ticket, portfolio_id, ticker, current_time)

        # 3. Persist domain Transaction entity
        if domain_order:
            self._record_fill(ticket, ticker, order_qty, price, current_time, domain_order)

        # 4. Upsert domain Position entity
        self._update_position(ticker, order_qty, portfolio_id)

        if self.logger:
            self.logger.info(
                f"TradeManager: {ticker} qty_Δ={order_qty:+d} @ ${price:.2f}"
            )
        return True

    # ------------------------------------------------------------------
    # Private mechanics
    # ------------------------------------------------------------------

    def _register_order(self, ticket, portfolio_id: int, ticker: str, current_time: datetime):
        """Persist a domain Order entity from the QC OrderTicket."""
        try:
            qty = ticket.quantity

            # Resolve FK dependencies before the INSERT to satisfy NOT NULL constraints
            holding_id = self._resolve_holding_id(ticker, portfolio_id, current_time)
            account_id = self._resolve_account_id(current_time)

            params = {
                "order_type": "MARKET",           # string name avoids enum .upper() error
                "side": "BUY" if qty > 0 else "SELL",
                "quantity": abs(qty),
                "created_at": current_time,       # simulation time, not wall clock
                "status": "FILLED",
                "symbol": ticker,
                "holding_id": holding_id,
                "account_id": account_id,
            }
            domain_order = self.order_repo._create_or_get(
                external_order_id=str(ticket.order_id),
                portfolio_id=portfolio_id,
                **params,
            )
            if domain_order:
                self._order_ticket_mapping[ticket.order_id] = domain_order.id
            return domain_order
        except Exception as e:
            if self.logger:
                self.logger.error(f"TradeManager._register_order failed: {e}")
            return None

    def _resolve_holding_id(self, ticker: str, portfolio_id: int, current_time: datetime):
        """
        Resolve or create the Holding for (portfolio_id, ticker).

        Dependency chain (must be satisfied in order):
          1. Portfolio  — already exists (caller guarantees portfolio_id is valid)
          2. FinancialAsset — looked up by symbol; no holding possible without it
          3. Position — created first (HoldingModel.position_id FK → positions.id)
          4. Holding — created last, references both asset and position
        """
        try:
            from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
            from src.infrastructure.models.finance.holding.holding import HoldingModel
            from src.infrastructure.models.finance.position import PositionModel

            session = self.order_repo.session

            # 1. Look up the financial asset by ticker symbol
            asset = session.query(FinancialAssetModel).filter(
                FinancialAssetModel.symbol == ticker
            ).first()
            asset_id = asset.id if asset else None
            if not asset_id:
                if self.logger:
                    self.logger.warning(
                        f"TradeManager: no financial asset found for '{ticker}' — skipping holding creation"
                    )
                return None

            # 2. Return existing holding if one already exists for this (portfolio, asset)
            existing = session.query(HoldingModel).filter(
                HoldingModel.container_id == portfolio_id,
                HoldingModel.asset_id == asset_id,
            ).first()
            if existing:
                return existing.id

            # 3. Create Position first (Holding.position_id FK → positions.id)
            pos = PositionModel(
                portfolio_id=portfolio_id,
                quantity=0,
                position_type='LONG',  # string name avoids SQLEnum .upper() error
            )
            session.add(pos)
            session.flush()  # assigns pos.id without committing the outer transaction

            # 4. Create Holding referencing the new position — use simulation time
            holding = HoldingModel(
                asset_id=asset_id,
                container_id=portfolio_id,
                start_date=current_time,
                position_id=pos.id,
            )
            session.add(holding)
            session.commit()
            return holding.id

        except Exception as e:
            try:
                self.order_repo.session.rollback()
            except Exception:
                pass
            if self.logger:
                self.logger.error(f"TradeManager._resolve_holding_id failed for {ticker}: {e}")
            return None

    def _resolve_account_id(self, current_time: datetime):
        """Return the PK of the first available account row, creating one if none exists."""
        try:
            from src.infrastructure.models.finance.account import AccountModel
            from src.infrastructure.models.finance.financial_assets.currency import CurrencyModel
            session = self.order_repo.session

            account = session.query(AccountModel).first()
            if account:
                return account.id

            # No account exists — create a minimal default one
            currency = session.query(CurrencyModel).first()
            if not currency:
                if self.logger:
                    self.logger.warning("TradeManager: no currency found — cannot create default account")
                return None

            max_id = session.query(AccountModel.account_id).order_by(AccountModel.account_id.desc()).first()
            next_account_id = (max_id[0] + 1) if max_id else 1

            new_account = AccountModel(
                account_id=next_account_id,
                account_type='CASH',    # string avoids SQLEnum .upper() error
                status='ACTIVE',        # string avoids SQLEnum .upper() error
                currency_id=currency.id,
                created_at=current_time,  # simulation time, not wall clock
            )
            session.add(new_account)
            session.commit()
            if self.logger:
                self.logger.info(f"TradeManager: created default account id={new_account.id}")
            return new_account.id

        except Exception as e:
            try:
                self.order_repo.session.rollback()
            except Exception:
                pass
            if self.logger:
                self.logger.error(f"TradeManager._resolve_account_id failed: {e}")
            return None

    def _record_fill(
        self,
        ticket,
        ticker: str,
        order_qty: int,
        price: float,
        current_time: datetime,
        domain_order,
    ) -> None:
        """Persist a domain Transaction entity for the simulated fill."""
        try:
            trade_date = (
                current_time.date() if hasattr(current_time, "date") else current_time
            )
            params = {
                "date": current_time,
                "transaction_type": "MARKET_ORDER",  # string avoids enum .upper() error
                "account_id": self._resolve_account_id(current_time),
                "trade_date": trade_date,
                "value_date": trade_date,
                "settlement_date": trade_date,
                "status": "EXECUTED",               # string avoids enum .upper() error
                "spread": 0.0,
                "currency_id": 1,
                "exchange_id": 1,
                "side": "BUY" if order_qty > 0 else "SELL",
                "quantity": abs(order_qty),
                "fill_price": price,
                "symbol": ticker,
            }
            txn_id = f"TXN_{ticket.order_id}_{uuid.uuid4().hex[:8]}"
            self.transaction_repo._create_or_get(
                transaction_id=txn_id,
                order_id=int(domain_order.id),
                portfolio_id=int(domain_order.portfolio_id),
                **params,
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"TradeManager._record_fill failed for {ticker}: {e}")

    def _update_position(
        self, ticker: str, order_qty: int, portfolio_id: int
    ) -> None:
        """
        Update the Position quantity linked through the Holding for this ticker.

        Navigation: FinancialAsset → Holding (by container+asset) → Position (via position_id FK)
        PositionModel no longer carries symbol/is_active — the holding is the lookup key.
        """
        try:
            from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
            from src.infrastructure.models.finance.holding.holding import HoldingModel
            from src.infrastructure.models.finance.position import PositionModel

            session = self.order_repo.session

            asset = session.query(FinancialAssetModel).filter(
                FinancialAssetModel.symbol == ticker
            ).first()
            if not asset:
                return

            holding = session.query(HoldingModel).filter(
                HoldingModel.container_id == portfolio_id,
                HoldingModel.asset_id == asset.id,
            ).first()
            if not holding or not holding.position_id:
                return

            pos = session.query(PositionModel).filter(
                PositionModel.id == holding.position_id
            ).first()
            if pos:
                pos.quantity = int(pos.quantity or 0) + order_qty
                session.commit()

        except Exception as e:
            try:
                self.order_repo.session.rollback()
            except Exception:
                pass
            if self.logger:
                self.logger.error(
                    f"TradeManager._update_position failed for {ticker}: {e}"
                )
