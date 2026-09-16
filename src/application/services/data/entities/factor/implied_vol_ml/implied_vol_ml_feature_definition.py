import hashlib
import json
import math
from typing import List, Optional


class ImpliedVolMlFeatureDefinition:
    """
    Defines the six-dimensional feature vector used to predict implied volatility.

    Features (in order):
      0. moneyness          = stock_price / strike_price
      1. log_moneyness      = log(moneyness)
      2. time_to_expiry     = calendar days to expiry / 365
      3. risk_free_rate     = annualised risk-free rate (decimal)
      4. norm_option_price  = option_price / stock_price
      5. is_call            = 1.0 for call, 0.0 for put
    """

    FEATURE_NAMES: List[str] = [
        "moneyness",
        "log_moneyness",
        "time_to_expiry",
        "risk_free_rate",
        "norm_option_price",
        "is_call",
    ]
    VERSION: int = 1

    def hash(self) -> str:
        canonical = {"features": self.FEATURE_NAMES, "version": self.VERSION}
        return hashlib.sha256(
            json.dumps(canonical, sort_keys=True).encode()
        ).hexdigest()

    def extract(self, dependencies: dict, entity, target_date) -> Optional[List[float]]:
        """
        Extract feature vector from Branch-A resolution dependencies.

        Returns None when any required input is unavailable (graceful degradation).
        """
        # --- option market price ---
        raw_opt = dependencies.get("CompanyShareOptionValueFactor")
        if raw_opt is None:
            return None
        opt_vals = raw_opt if isinstance(raw_opt, list) else [raw_opt]
        opt_vals = [float(v) for v in opt_vals if v is not None and float(v) > 0]
        if not opt_vals:
            return None
        option_price = sum(opt_vals) / len(opt_vals)

        # --- underlying stock price ---
        raw_s = dependencies.get("CompanyShareValueFactor")
        if raw_s is None:
            return None
        s_vals = raw_s if isinstance(raw_s, list) else [raw_s]
        s_vals = [float(v) for v in s_vals if v is not None and float(v) > 0]
        if not s_vals:
            return None
        stock_price = sum(s_vals) / len(s_vals)

        # --- strike price (from entity) ---
        strike = getattr(entity, "strike_price", None)
        if strike is None:
            return None
        strike = float(strike)
        if strike <= 0:
            return None

        # --- time to expiry ---
        expiry_date = getattr(entity, "end_date", None)
        if expiry_date is None:
            expiry_str = getattr(entity, "expiry", None)
            if expiry_str:
                from datetime import datetime as _dt
                expiry_date = _dt.strptime(str(expiry_str), "%Y%m%d").date()
        if expiry_date is None:
            return None
        ref_date = target_date.date() if hasattr(target_date, "date") else target_date
        if hasattr(expiry_date, "date"):
            expiry_date = expiry_date.date()
        days = (expiry_date - ref_date).days
        if days <= 0:
            return None
        tte = days / 365.0

        # --- risk-free rate ---
        raw_r = dependencies.get("CompanyShareOptionRFYieldFactor")
        if raw_r is None:
            return None
        r_vals = raw_r if isinstance(raw_r, list) else [raw_r]
        r_vals = [float(v) for v in r_vals if v is not None]
        if not r_vals:
            return None
        rf_rate = sum(r_vals) / len(r_vals)

        # --- option type ---
        option_type = getattr(entity, "option_type", "call") or "call"
        is_call = 1.0 if option_type.lower() == "call" else 0.0

        # --- derived features ---
        moneyness = stock_price / strike
        try:
            log_moneyness = math.log(moneyness)
        except (ValueError, ZeroDivisionError):
            return None
        norm_option_price = option_price / stock_price if stock_price > 0 else None
        if norm_option_price is None:
            return None

        return [moneyness, log_moneyness, tte, rf_rate, norm_option_price, is_call]
