"""BI-005: IBKR settings are validated up front, and the connected account must match the mode. No TWS."""

from unittest.mock import patch

import pytest

from src.application.services.misbuffet.brokers.ibkr.ibkr_settings import (
    AccountModeMismatch, account_kind, resolve_endpoint, validate_environment, verify_connected_accounts,
)

CLEAN = {name: "" for name in ("IBKR_HOST", "IBKR_PORT", "IBKR_CLIENT_ID", "IBKR_ACCOUNT_MODE", "IBKR_ALLOW_LIVE",
                               "IBKR_CONNECT_RETRIES", "IBKR_CONNECT_RETRY_DELAY")}


def env(**values):
    return patch.dict("os.environ", {**CLEAN, **values})


def test_no_variables_is_valid_and_paper():
    with env():
        validate_environment()
        assert resolve_endpoint("127.0.0.1", 7497, 1).account_mode == "paper"


def test_every_problem_is_reported_at_once():
    with env(IBKR_PORT="abc", IBKR_CLIENT_ID="-1", IBKR_CONNECT_RETRY_DELAY="soon", IBKR_ACCOUNT_MODE="real"):
        with pytest.raises(ValueError) as error:
            resolve_endpoint("127.0.0.1", 7497, 1)
    message = str(error.value)
    for part in ("IBKR_PORT must be an integer", "IBKR_CLIENT_ID must be >= 0", "IBKR_CONNECT_RETRY_DELAY must be a number",
                 "IBKR_ACCOUNT_MODE must be one of"):
        assert part in message


def test_live_mode_still_needs_the_explicit_allow():
    with env(IBKR_ACCOUNT_MODE="live"), pytest.raises(ValueError, match="IBKR_ALLOW_LIVE=yes"):
        validate_environment()
    with env(IBKR_ACCOUNT_MODE="live", IBKR_ALLOW_LIVE="yes"):
        assert resolve_endpoint("127.0.0.1", 7496, 1).account_mode == "live"


@pytest.mark.parametrize("account, kind", [("DU1234567", "paper"), ("DF123", "paper"), ("du1234567", "paper"),
                                           ("U1234567", "live"), ("F7654321", "live")])
def test_account_kind(account, kind):
    assert account_kind(account) == kind


@pytest.mark.parametrize("accounts, order_account, mode", [
    ([], "", "paper"),                              # TWS reported no account: fail closed
    (["U1234567"], "", "paper"),
    (["DU1234567"], "", "live"),
    (["DU1234567"], "DU9999999", "paper"),          # not managed by this login
    (["DU1234567", "U1234567"], "", "paper"),       # default account ambiguous
])
def test_mismatches_are_refused(accounts, order_account, mode):
    with pytest.raises(AccountModeMismatch):
        verify_connected_accounts(accounts, order_account, mode=mode)


def test_matching_accounts_pass():
    verify_connected_accounts(["DU1234567"], mode="paper")
    verify_connected_accounts(["DU1234567", "U1234567"], "DU1234567", mode="paper")
    verify_connected_accounts([" U1234567 "], mode="live")
