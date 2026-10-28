"""
TradeManager – mechanics of the Order → Transaction → Position persistence pipeline.

Called exclusively by UnifiedPortfolioManager, which orchestrates when and what
to trade. TradeManager only knows *how* to persist the resulting domain entities.

Backtest (no order ledger): the order is booked as filled at the submission price.
Live (an OrderLedger attached, P.03): the order intent is stored BEFORE sending, the submission outcome after it,
and nothing is booked at submission — fills, positions and cash move only with the broker's executions
(OrderLedger.on_execution -> book_execution) and commissions (book_commission).
"""

import math
import uuid
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Callable, Dict, Optional


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
        self.ledger = None                  # OrderLedger: live order path (attach_ledger)
        self._submission_probe = None       # () -> the engine order of the last live submission

    def attach_ledger(self, ledger, submission_probe: Optional[Callable[[], Any]] = None) -> None:
        """Live mode: orders go through the durable ledger (intent before sending, no booking at submission).
        `submission_probe` returns the engine order of the last submission (QCAlgorithm.last_submitted_order),
        which the broker annotates with `submission_outcome` / `broker_order_id`."""
        self.ledger = ledger
        self._submission_probe = submission_probe
        if getattr(ledger, "trade_manager", None) is None:
            ledger.trade_manager = self

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
        main_portfolio_id: Optional[int] = None,
    ) -> bool:
        """
        Full pipeline: submit ticket → register Order → record Transaction → update Position.

        Args:
            ticker:            asset symbol string
            order_qty:         signed quantity (positive = buy, negative = sell)
            price:             fill price
            portfolio_id:      domain portfolio ID (may be a sub-portfolio, e.g. CompanySharePortfolio)
            current_time:      algorithm time used for timestamps
            submit_order_fn:   callable(ticker, qty) → OrderTicket
            main_portfolio_id: top-level portfolio id that owns the CurrencyPortfolio; defaults
                               to portfolio_id when the caller does not provide it (i.e. when
                               portfolio_id already is the main portfolio)
        """
        # 0a. Nothing to trade or no valid fill price: refused before anything is sent or written
        #     (a zero-quantity order used to be submitted and booked with a zero cash leg).
        if not order_qty or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            if self.logger:
                self.logger.error(f"TradeManager: {ticker} qty={order_qty} @ {price} refused — order not sent")
            return False

        # 0. The order must be recordable before it is sent: holding (asset + position) and account.
        #    An order that cannot be booked is never submitted and moves no cash.
        holding_id = self._resolve_holding_id(ticker, portfolio_id, current_time)
        account_id = self._resolve_account_id(current_time)
        if holding_id is None or account_id is None:
            if self.logger:
                self.logger.error(f"TradeManager: {ticker} cannot be booked (holding={holding_id}, "
                                  f"account={account_id}) — order not sent")
            return False

        cash_portfolio_id = main_portfolio_id if main_portfolio_id is not None else portfolio_id
        if self.ledger is not None:
            return self._execute_live(ticker, order_qty, price, portfolio_id, cash_portfolio_id, current_time,
                                      submit_order_fn, tag, holding_id, account_id)

        # 1. Order ticket (backtest: in memory)
        ticket = submit_order_fn(ticker, order_qty, tag=tag or f"set_holdings_{ticker}")
        if not ticket:
            return False

        # 2-5. Order, fill, position and cash are booked as ONE database transaction: either all
        # of them are stored or none (a failure in the middle used to leave e.g. cash debited
        # without a position). The order is never re-sent here.
        booked = self._book_atomically(lambda: self._book(ticket, ticker, order_qty, price, portfolio_id,
                                                          cash_portfolio_id, current_time))
        if not booked:
            if self.logger:
                self.logger.critical(
                    f"TradeManager: order {getattr(ticket, 'order_id', '?')} for {ticker} qty={order_qty:+d} was "
                    f"submitted but its booking failed and was rolled back — the books do not reflect it "
                    f"(live: the broker reconciliation will block trading until they match)")
            return False

        if self.logger:
            self.logger.info(
                f"TradeManager: {ticker} qty_Δ={order_qty:+d} @ ${price:.2f}"
            )
        return True

    # ------------------------------------------------------------------
    # Live order path (P.03)
    # ------------------------------------------------------------------

    def _execute_live(self, ticker, order_qty, price, portfolio_id, cash_portfolio_id, current_time,
                      submit_order_fn, tag, holding_id, account_id) -> bool:
        """Intent stored -> order sent -> outcome stored. Returns True only when the broker took the order;
        nothing is booked here (executions do that)."""
        side = "BUY" if order_qty > 0 else "SELL"
        intent = {}

        def record_intent() -> bool:
            order = self.order_repo._create_or_get(
                external_order_id=f"INTENT_{uuid.uuid4().hex[:16]}", portfolio_id=portfolio_id,
                order_type="MARKET", side=side, quantity=abs(order_qty), created_at=current_time,
                status="PENDING", symbol=ticker, holding_id=holding_id, account_id=account_id,
                price=price, filled_quantity=0.0, average_fill_price=None)
            if order is None:
                return False
            intent["bo"] = self.ledger.record_intent(order.id, ticker, side, abs(order_qty), portfolio_id,
                                                     cash_portfolio_id)
            return True

        if not self._book_atomically(record_intent):
            if self.logger:
                self.logger.error(f"TradeManager: {ticker} order intent could not be stored — order not sent")
            return False
        bo = intent["bo"]

        before = self._submission_probe() if self._submission_probe else None
        error = None
        try:
            ticket = submit_order_fn(ticker, order_qty, tag=tag or f"set_holdings_{ticker}")
        except Exception as e:
            ticket, error = None, e
        engine_order = self._submission_probe() if self._submission_probe else None
        if engine_order is before:
            engine_order = None                                   # this call never created an engine order
        outcome = getattr(engine_order, "submission_outcome", None)
        broker_order_id = getattr(engine_order, "broker_order_id", None)
        try:
            if outcome == "unknown" or (self._submission_probe is None and not ticket):
                reason = f"send attempted, outcome unknown ({error!r})" if error else "send attempted, outcome unknown"
                self.ledger.mark_unknown(bo, reason, broker_order_id=broker_order_id)
                return False
            if outcome == "sent" or (ticket and outcome is None):     # the broker has it (whatever came after)
                self.ledger.mark_submitted(bo, broker_order_id, getattr(engine_order, "broker_client_id", None))
                if self.logger:
                    self.logger.info(f"TradeManager: {ticker} {side} {abs(order_qty)} submitted "
                                     f"(order {bo.order_id}, broker order {broker_order_id})")
                return True
            self.ledger.mark_not_sent(bo, f"not sent ({error!r})" if error else "not sent: refused before sending")
            return False
        except Exception as e:
            if self.logger:
                self.logger.critical(f"TradeManager: submission outcome of order {bo.order_id} ({ticker}) could not "
                                     f"be stored ({e!r}) — the intent row stays INTENT; never resent")
            return False

    def book_execution(self, order_id: int, ticker: str, signed_qty: float, price: float, portfolio_id: int,
                       cash_portfolio_id: int, when: datetime, ref: str) -> bool:
        """Book one broker execution: transaction, position and cash (the caller owns the transaction)."""
        qty = int(round(signed_qty)) if abs(signed_qty - round(signed_qty)) < 1e-9 else signed_qty
        self._record_fill(SimpleNamespace(order_id=ref), ticker, qty, price, when,
                          SimpleNamespace(id=order_id, portfolio_id=portfolio_id))
        self._update_position(ticker, qty, portfolio_id)
        self._update_cash_for_trade(qty, price * self.contract_multiplier(ticker), cash_portfolio_id, when)
        return True

    def book_commission(self, amount: float, cash_portfolio_id: int, when: datetime) -> bool:
        """Book a broker commission on the cash position: a debit (a credit when negative, a rebate)."""
        if amount == 0:
            return True
        self._update_cash_for_trade(1 if amount > 0 else -1, abs(amount), cash_portfolio_id, when)
        return True

    # ------------------------------------------------------------------
    # Private mechanics
    # ------------------------------------------------------------------

    def _book(self, ticket, ticker, order_qty, price, portfolio_id, cash_portfolio_id, current_time) -> bool:
        domain_order = self._register_order(ticket, portfolio_id, ticker, current_time, order_qty, price=price)
        if domain_order is None:
            return False
        self._record_fill(ticket, ticker, order_qty, price, current_time, domain_order)
        self._update_position(ticker, order_qty, portfolio_id)
        self._update_cash_for_trade(order_qty, price * self.contract_multiplier(ticker), cash_portfolio_id,
                                    current_time)
        return True

    def contract_multiplier(self, ticker: str) -> float:
        """Units per contract (options: `multiplier`, futures: `contract_size`): the cash leg of a trade is
        price × quantity × multiplier — 2 option contracts at 8.00 on 100 shares cost 1 600, not 16. Assets
        without either attribute (shares, currencies) are 1 unit."""
        from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
        asset = self.order_repo.session.query(FinancialAssetModel).filter(FinancialAssetModel.symbol == ticker).first()
        for attr in ("multiplier", "contract_size"):
            value = getattr(asset, attr, None)
            if value is not None and float(value) > 0:
                return float(value)
        return 1.0

    def _book_atomically(self, book) -> bool:
        """Run `book` as ONE transaction on the shared session (unit_of_work.atomic): the repositories'
        commits only flush, and a failed step, a repository rollback or an exception rolls everything back."""
        from src.infrastructure.database.unit_of_work import TransactionAborted, atomic
        try:
            with atomic(self.order_repo.session) as tx:
                self._booking_tx = tx
                if not book():
                    tx.fail("step failed")
            return True
        except TransactionAborted as e:
            if self.logger:
                self.logger.error(f"TradeManager: booking rolled back ({e})")
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"TradeManager: booking rolled back ({e!r})")
            return False
        finally:
            self._booking_tx = None

    def _step_failed(self, what: str) -> None:
        tx = getattr(self, "_booking_tx", None)
        if tx is not None:
            tx.fail(what)

    def _register_order(self, ticket, portfolio_id: int, ticker: str, current_time: datetime, order_qty: int = 0,
                        price: Optional[float] = None):
        """Persist a domain Order entity from the QC OrderTicket."""
        try:
            # Resolve FK dependencies before the INSERT to satisfy NOT NULL constraints
            holding_id = self._resolve_holding_id(ticker, portfolio_id, current_time)
            account_id = self._resolve_account_id(current_time)

            params = {
                "order_type": "MARKET",           # string name avoids enum .upper() error
                "side": "BUY" if order_qty > 0 else "SELL",
                "quantity": abs(order_qty),
                "created_at": current_time,       # simulation time, not wall clock
                "status": "FILLED",
                "symbol": ticker,
                "holding_id": holding_id,
                "account_id": account_id,
                # fill as booked: executed price and quantity
                "price": price,
                "filled_quantity": abs(order_qty),
                "average_fill_price": price,
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
            self._step_failed(f"fill: {e}")

    def _update_position(
        self, ticker: str, order_qty: int, portfolio_id: int
    ) -> None:
        """
        Update the Position quantity for this ticker.

        CompanyShare tickers live inside a CompanySharePortfolio sub-portfolio, not
        directly under the main portfolio.  Navigation:
          main portfolio
            → CompanySharePortfolioPortfolioHolding (container_id=portfolio_id)
              → CompanySharePortfolio (asset_id)
                → CompanySharePortfolioHolding (container_id=sub_portfolio_id, asset_id=share.id)
                  → Position.quantity += order_qty

        Falls back to a direct HoldingModel lookup for holdings that live directly
        under the main portfolio (e.g. currency holdings).
        """
        try:
            from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
            from src.infrastructure.models.finance.holding.holding import HoldingModel
            from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import (
                CompanySharePortfolioPortfolioHoldingModel,
            )
            from src.infrastructure.models.finance.holding.company_share_portfolio_holding import (
                CompanySharePortfolioHoldingModel,
            )
            from src.infrastructure.models.finance.position import PositionModel

            session = self.order_repo.session

            asset = session.query(FinancialAssetModel).filter(
                FinancialAssetModel.symbol == ticker
            ).first()
            if not asset:
                return

            # Option path: CompanyShareOptionPortfolioHolding keyed by company_share_option_id.
            # The CSO sub-portfolio is NOT linked from the main portfolio via a holding, so we
            # query the option holding table directly rather than traversing from portfolio_id.
            from src.infrastructure.models.finance.holding.company_share_option_portfolio_holding import (
                CompanyShareOptionPortfolioHoldingModel,
            )
            cso_holding = session.query(CompanyShareOptionPortfolioHoldingModel).filter_by(
                company_share_option_id=asset.id,
            ).first()
            if cso_holding and cso_holding.position_id:
                pos = session.query(PositionModel).filter_by(
                    id=cso_holding.position_id,
                ).first()
                if pos:
                    pos.quantity = int(pos.quantity or 0) + order_qty
                    pos.position_type = 'SHORT' if pos.quantity < 0 else 'LONG'
                    session.commit()
                    return

            # Share sub-portfolio path: main portfolio → CompanySharePortfolio → holding
            cs_pp = session.query(CompanySharePortfolioPortfolioHoldingModel).filter_by(
                container_id=portfolio_id
            ).first()
            if cs_pp:
                cs_holding = session.query(CompanySharePortfolioHoldingModel).filter_by(
                    container_id=cs_pp.asset_id,
                    asset_id=asset.id,
                ).first()
                if cs_holding and cs_holding.position_id:
                    pos = session.query(PositionModel).filter_by(
                        id=cs_holding.position_id
                    ).first()
                    if pos:
                        pos.quantity = int(pos.quantity or 0) + order_qty
                        pos.position_type = 'SHORT' if pos.quantity < 0 else 'LONG'
                        session.commit()
                        return

            # Direct fallback for holdings sitting directly under the main portfolio
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
                pos.position_type = 'SHORT' if pos.quantity < 0 else 'LONG'
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
            self._step_failed(f"position: {e}")

    def _update_cash_for_trade(
        self,
        order_qty: int,
        price: float,
        portfolio_id: int,
        current_time: datetime,
    ) -> None:
        """
        Mirror the cash impact of a trade on the CurrencyPortfolio:
          BUY  (order_qty > 0): SELL cash Order + Transaction, reduce Position.quantity
          SELL (order_qty < 0): BUY  cash Order + Transaction, increase Position.quantity

        Navigation: main portfolio → CurrencyPortfolioPortfolioHolding
                                  → CurrencyPortfolio
                                  → CurrencyPortfolioHolding → Position
        """
        try:
            from src.infrastructure.models.finance.holding.currency_portfolio_portfolio_holding import (
                CurrencyPortfolioPortfolioHoldingModel,
            )
            from src.infrastructure.models.finance.holding.currency_portfolio_holding import (
                CurrencyPortfolioHoldingModel,
            )
            from src.infrastructure.models.finance.position import PositionModel

            session = self.order_repo.session

            # 1. Find the CurrencyPortfolio linked to this portfolio
            cp_link = (
                session.query(CurrencyPortfolioPortfolioHoldingModel)
                .filter_by(container_id=portfolio_id)
                .first()
            )
            if not cp_link:
                if self.logger:
                    self.logger.warning(
                        f"_update_cash_for_trade: no CurrencyPortfolio link for portfolio {portfolio_id}"
                    )
                return

            currency_portfolio_id = cp_link.asset_id  # FK → currency_portfolios.id

            # 2. Find the cash holding inside the CurrencyPortfolio
            cash_holding = (
                session.query(CurrencyPortfolioHoldingModel)
                .filter_by(currency_portfolio_id=currency_portfolio_id)
                .first()
            )
            if not cash_holding:
                if self.logger:
                    self.logger.warning(
                        f"_update_cash_for_trade: no CurrencyPortfolioHolding "
                        f"for currency_portfolio {currency_portfolio_id}"
                    )
                return

            # 3. Find the Position linked to the cash holding
            pos = session.query(PositionModel).filter_by(id=cash_holding.position_id).first()
            if not pos:
                if self.logger:
                    self.logger.warning(
                        f"_update_cash_for_trade: no Position for cash holding {cash_holding.id}"
                    )
                return

            # 4. Compute cash delta and order side
            cash_amount = round(abs(order_qty) * price, 2)        # to the cent (positions.quantity is DECIMAL)
            if order_qty > 0:
                cash_qty_delta = -cash_amount  # BUY stock → cash decreases
                cash_side = "SELL"
            else:
                cash_qty_delta = cash_amount   # SELL stock → cash increases
                cash_side = "BUY"

            account_id = self._resolve_account_id(current_time)

            # 5. Order for cash movement (against the CurrencyPortfolio sub-portfolio)
            cash_order = self.order_repo._create_or_get(
                external_order_id=f"CASH_{uuid.uuid4().hex[:12]}",
                portfolio_id=currency_portfolio_id,
                order_type="MARKET",
                side=cash_side,
                quantity=cash_amount,
                created_at=current_time,
                status="FILLED",
                holding_id=cash_holding.id,
                account_id=account_id,
            )

            # 6. Transaction for cash movement
            if cash_order:
                trade_date = (
                    current_time.date() if hasattr(current_time, "date") else current_time
                )
                txn_id = f"CASH_TXN_{uuid.uuid4().hex[:8]}"
                self.transaction_repo._create_or_get(
                    transaction_id=txn_id,
                    order_id=int(cash_order.id),
                    portfolio_id=currency_portfolio_id,
                    date=current_time,
                    transaction_type="MARKET_ORDER",
                    account_id=account_id,
                    trade_date=trade_date,
                    value_date=trade_date,
                    settlement_date=trade_date,
                    status="EXECUTED",
                    spread=0.0,
                    currency_id=1,
                    exchange_id=1,
                    side=cash_side,
                    quantity=cash_amount,
                    fill_price=1.0,
                    symbol="CASH",
                )

            # 7. Update the cash Position quantity
            pos.quantity = round(float(pos.quantity or 0) + cash_qty_delta, 4)
            session.commit()

            if self.logger:
                self.logger.info(
                    f"TradeManager: cash {cash_side} ${cash_amount:,} "
                    f"→ new cash position = {pos.quantity:,}"
                )

        except Exception as e:
            try:
                self.order_repo.session.rollback()
            except Exception:
                pass
            if self.logger:
                self.logger.error(f"TradeManager._update_cash_for_trade failed: {e}")
            self._step_failed(f"cash: {e}")
