"""
Project adapters: each existing project folder declares its capabilities and configuration schema, and translates
a Strategy into the native config dict its own project manager already understands. The project's
manager, cycle, model and portfolio rule then run unchanged.

Invariant (regression-tested): ``native_config(default_sections())`` equals the project's own ``get_config()``, so
the default configuration reproduces today's runs exactly.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from src.domain.entities.strategy.configuration_schema import (
    ERROR,
    WARNING,
    ConfigurationSchema,
    FieldSpec,
    SectionSchema,
    ValidationIssue,
    validate_sections,
)
from src.domain.entities.strategy.project_capabilities import (
    POSITION_SIGNAL,
    PROBABILITY_ABOVE_MEDIAN,
    ProjectCapabilities,
)

Sections = Dict[str, Dict[str, Any]]

# options the task lists that no project implements yet (shown as unavailable, rejected by validation)
COMMON_UNSUPPORTED: Tuple[str, ...] = (
    "long-only, long-and-cash, top-N / bottom-N selection",
    "maximum asset weight, net exposure, concentration and turnover limits",
    "short availability / borrow constraints",
    "separate signal, rebalance and execution frequencies (one clock: the decision bar)",
    "order types other than market orders at the decision bar; slippage model",
    "benchmark choice (fixed: equal-weight long-only and 20-session momentum long/short)",
    "training without a backtest (models are trained inside the run as the clock advances)",
    "paper and live trading from the strategy interface",
)


def _bdays(start, end) -> int:
    """Sessions (business days) in [start, end)."""
    return max(0, len(pd.bdate_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize())) - 1)


from src.application.services.strategy.strategy_definition import (  # noqa: E402,F401  re-exported
    bar_frequency,
    strategy_definition,
)


class ProjectAdapter:
    """Base: schema validation + common evaluation checks. Subclasses declare the schema and the translation."""

    key: str = ""
    config_module: str = ""
    manager_path: str = ""          # 'module:ClassName'
    report_renderer: str = ""       # module with FIGURES, tables(), table_html(), figure_base64(), build_pdf()

    # -- declared by subclasses -----------------------------------------------------------------------------------
    def capabilities(self) -> ProjectCapabilities:
        raise NotImplementedError

    def schema(self) -> ConfigurationSchema:
        raise NotImplementedError

    def default_sections(self) -> Sections:
        raise NotImplementedError

    def _apply(self, config: Dict[str, Any], sections: Sections) -> None:
        """Write the sections into a deep copy of the project's own config (in place)."""
        raise NotImplementedError

    def _project_checks(self, sections: Sections) -> List[ValidationIssue]:
        return []

    # -- shared -----------------------------------------------------------------------------------------------
    def module(self):
        return importlib.import_module(self.config_module)

    def base_config(self) -> Dict[str, Any]:
        return copy.deepcopy(self.module().DEFAULT_CONFIG)

    def renderer(self):
        return importlib.import_module(self.report_renderer)

    def manager_class(self):
        module, cls = self.manager_path.split(":")
        return getattr(importlib.import_module(module), cls)

    def validate(self, sections: Sections) -> Tuple[Sections, List[ValidationIssue]]:
        normalised, issues = validate_sections(self.schema(), sections)
        if any(i.severity == ERROR for i in issues):
            return normalised, issues
        ev = normalised.get("evaluation", {})
        start, end = pd.Timestamp(ev["backtest_start"]), pd.Timestamp(ev["backtest_end"])
        if end <= start:
            issues.append(ValidationIssue("evaluation", "backtest_end", "must be after backtest_start"))
        if pd.Timestamp(ev["price_history_start"]) >= start:
            issues.append(ValidationIssue("evaluation", "price_history_start", "must be before backtest_start"))
        if not any(i.severity == ERROR for i in issues):
            issues += self._project_checks(normalised)
        return normalised, issues

    def native_config(self, sections: Sections, results_dir: Optional[str] = None,
                      portfolio_name: Optional[str] = None) -> Dict[str, Any]:
        """The project's config dict for these (validated) sections; ``results_dir`` / ``portfolio_name`` keep an
        experiment's outputs and book apart from other runs."""
        config = self.base_config()
        self._apply(config, sections)
        ev = sections["evaluation"]
        config["backtest_start"] = ev["backtest_start"]
        config["backtest_end"] = ev["backtest_end"]
        config["price_history_start"] = ev["price_history_start"]
        config["initial_capital"] = ev["initial_capital"]
        config["Portfolio"]["initial_cash"] = ev["initial_capital"]
        if results_dir:
            config["results_dir"] = results_dir
        if portfolio_name:
            config["Portfolio"]["name"] = portfolio_name
        return config

    def definition(self, sections: Sections) -> Dict[str, Any]:
        """The Strategy's typed definition for these (validated) sections, read from the native config."""
        return strategy_definition(self.native_config(sections))

    @staticmethod
    def _evaluation_section(config: Dict[str, Any], history_help: str) -> SectionSchema:
        return SectionSchema("evaluation", label="Backtest and evaluation", fields=(
            FieldSpec("backtest_start", "datetime", config["backtest_start"], "Backtest start",
                      "First decision time (the engine clock)"),
            FieldSpec("backtest_end", "datetime", config["backtest_end"], "Backtest end"),
            FieldSpec("price_history_start", "date", config["price_history_start"], "Price history start",
                      history_help),
            FieldSpec("initial_capital", "float", float(config["initial_capital"]), "Initial capital",
                      minimum=1000.0),
        ))


# ======================================================================================================================
# Cross-sectional momentum (LightGBM classifier + Optuna TPE)
# ======================================================================================================================

class CrossSectionalAdapter(ProjectAdapter):
    key = "cross_sectional"
    config_module = "src.application.managers.project_managers.cross_sectionnal_project.config"
    manager_path = ("src.application.managers.project_managers.cross_sectionnal_project.project_manager:"
                    "CrossSectionalMomentumProjectManager")
    report_renderer = "src.application.services.data.entities.factor.cross_sectional_momentum.csm_report_renderer"

    def capabilities(self) -> ProjectCapabilities:
        return ProjectCapabilities(
            key=self.key, label="Cross-sectional momentum (LightGBM + Optuna TPE)",
            strategy_type="cross_sectional_classifier",
            description="Per-asset LightGBM classifier of next-session return above the cross-sectional median; "
                        "Optuna TPE selects the features and hyper-parameters at every retraining.",
            folder="project_managers/cross_sectionnal_project",
            model_families=("lightgbm_classifier",), output_contract=PROBABILITY_ABOVE_MEDIAN,
            portfolio_rules=("quantile_long_short_inverse_vol",), long_short=True, long_only=False,
            decision_frequencies=("1 day",), universe_modes=("explicit",), lifecycle=("backtest",),
            trains_inside_backtest=True,
            unsupported=COMMON_UNSUPPORTED + ("regression target; expanding training window; LightGBM search-space "
                                              "bounds (fixed in CSMOptimizationConfig)",),
        )

    def _candidates(self) -> List[str]:
        from src.application.services.data.entities.factor.cross_sectional_momentum.csm_feature_definition import (
            CSMFeatureDefinition,
        )
        return list(CSMFeatureDefinition.FEATURE_NAMES)

    def schema(self) -> ConfigurationSchema:
        c = self.base_config()
        m = self.module()
        csm = c["csm"]
        opt, tr = csm["optimization"], csm["training"]
        return ConfigurationSchema(self.key, sections=(
            SectionSchema("universe", label="Universe", fields=(
                FieldSpec("name", "str", csm["universe"]["name"], "Universe name",
                          "A different constituent list needs its own name (constituents of a name are point-in-time "
                          "records)", required=True),
                FieldSpec("tickers", "str_list", list(m.CSM_TICKERS), "Constituents",
                          "Explicit list of CompanyShare tickers (no silent replacement of missing names)",
                          required=True),
            )),
            SectionSchema("factors", label="Candidate features", help="The 48 CSMFeatureDefinition factors; Optuna "
                          "selects the subset each model uses", fields=(
                FieldSpec("exclude", "choice_list", list(csm["features"]["exclude"]), "Excluded candidates",
                          choices=tuple(self._candidates())),
                FieldSpec("cross_sectional_ranks", "bool", csm["features"]["cross_sectional_ranks"],
                          "Add cross-sectional percentile ranks"),
            )),
            SectionSchema("model", label="LightGBM classifier and Optuna TPE study", fields=(
                FieldSpec("n_trials", "int", opt["n_trials"], "Optuna trials", minimum=1, maximum=1000),
                FieldSpec("n_startup_trials", "int", opt["n_startup_trials"], "Random start-up trials", minimum=0),
                FieldSpec("n_folds", "int", opt["n_folds"], "Purged walk-forward folds", minimum=2, maximum=10),
                FieldSpec("metric", "choice", opt["metric"], "Validation objective",
                          choices=("auc", "long_short_sharpe")),
                FieldSpec("min_features", "int", opt["min_features"], "Minimum features per trial", minimum=1),
                FieldSpec("timeout_seconds", "int", opt["timeout_seconds"], "Study time limit (s)", minimum=1,
                          nullable=True),
                FieldSpec("top_trial_fraction", "float", opt["top_trial_fraction"], "Top-trial fraction",
                          minimum=0.01, maximum=1.0),
                FieldSpec("seed", "int", opt["seed"], "Random seed"),
            )),
            SectionSchema("training", label="Training", fields=(
                FieldSpec("training_window_rows", "int", tr["training_window_rows"], "Rolling training window "
                          "(sessions)", minimum=20),
                FieldSpec("retrain_every_days", "int", c["retrain_every_days"], "Retrain every (calendar days)",
                          minimum=1),
                FieldSpec("label_horizon", "int", csm["label"]["horizon"], "Label horizon (sessions)", minimum=1,
                          maximum=20),
            )),
            SectionSchema("portfolio", label="Portfolio construction", fields=(
                FieldSpec("rule", "choice", "quantile_long_short_inverse_vol", "Rule",
                          choices=("quantile_long_short_inverse_vol",)),
                FieldSpec("long_short_quantile", "float", tr["long_short_quantile"], "Quantile per side",
                          "Long the top, short the bottom fraction of the probabilities", minimum=0.01, maximum=0.5),
                FieldSpec("gross_exposure", "float", tr["gross_exposure"], "Gross exposure", minimum=0.01,
                          maximum=2.0),
                FieldSpec("vol_span", "int", csm["features"]["vol_span"], "Sizing volatility EWM span (sessions)",
                          minimum=2),
            )),
            SectionSchema("trading", label="Trading", fields=(
                FieldSpec("decision_frequency", "choice", c["bar_size_setting"], "Decision / rebalance / execution",
                          "One clock: a decision, a rebalance and its orders at each session",
                          choices=(c["bar_size_setting"],)),
            )),
            self._evaluation_section(c, "Daily history imported before the first decision: training window + "
                                        "feature warm-up (128 sessions) + label horizon"),
            SectionSchema("data_policy", label="Data", fields=(
                FieldSpec("preload_data", "bool", c["preload_data"], "Preload every series before the first bar"),
                FieldSpec("persist_features", "bool", csm.get("persist_features", False),
                          "Store every decision's feature values", "~2 300 factor values per session; makes each "
                          "decision auditable from the database"),
            )),
        ))

    def default_sections(self) -> Sections:
        return self.schema().defaults()

    def _project_checks(self, s: Sections) -> List[ValidationIssue]:
        issues = []
        m, f = s["model"], s["factors"]
        if m["n_startup_trials"] > m["n_trials"]:
            issues.append(ValidationIssue("model", "n_startup_trials", "cannot exceed n_trials"))
        left = len(self._candidates()) - len(f["exclude"])
        if m["min_features"] > left:
            issues.append(ValidationIssue("model", "min_features", f"only {left} candidates are left"))
        if not s["universe"]["tickers"]:
            issues.append(ValidationIssue("universe", "tickers", "at least one ticker is required"))
        elif len(s["universe"]["tickers"]) < 5:
            issues.append(ValidationIssue("universe", "tickers", "a quantile long/short book needs at least 5 "
                                                                 "assets per side to be meaningful", WARNING))
        default = self.schema().section("universe")
        if (s["universe"]["name"] == default.field("name").default
                and s["universe"]["tickers"] != default.field("tickers").default):
            issues.append(ValidationIssue("universe", "name", "a different constituent list needs its own universe "
                                                              "name (the default name holds the default list)"))
        from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
            CSMFeatureConfig,
        )
        needed = (s["training"]["training_window_rows"] + CSMFeatureConfig().warmup_rows()
                  + s["training"]["label_horizon"])
        have = _bdays(s["evaluation"]["price_history_start"], s["evaluation"]["backtest_start"])
        if have < needed:
            issues.append(ValidationIssue("evaluation", "price_history_start",
                                          f"{have} sessions before backtest_start; the first model needs {needed} "
                                          f"(training window + 128-session feature warm-up + label horizon)"))
        return issues

    def _apply(self, c: Dict[str, Any], s: Sections) -> None:
        from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
        csm = c["csm"]
        tickers = list(s["universe"]["tickers"])
        default_tickers = list(self.module().CSM_TICKERS)
        c["universe"] = {CompanyShare: tickers}
        csm["universe"]["name"] = s["universe"]["name"]
        csm["universe"]["tickers"] = None if tickers == default_tickers else tickers
        csm["features"]["exclude"] = tuple(s["factors"]["exclude"])
        csm["features"]["cross_sectional_ranks"] = s["factors"]["cross_sectional_ranks"]
        csm["features"]["vol_span"] = s["portfolio"]["vol_span"]
        for k in ("n_trials", "n_startup_trials", "n_folds", "metric", "min_features", "timeout_seconds",
                  "top_trial_fraction", "seed"):
            csm["optimization"][k] = s["model"][k]
        csm["training"]["training_window_rows"] = s["training"]["training_window_rows"]
        csm["training"]["long_short_quantile"] = s["portfolio"]["long_short_quantile"]
        csm["training"]["gross_exposure"] = s["portfolio"]["gross_exposure"]
        csm["label"]["horizon"] = s["training"]["label_horizon"]
        c["retrain_every_days"] = s["training"]["retrain_every_days"]
        c["preload_data"] = s["data_policy"]["preload_data"]
        csm["persist_features"] = s["data_policy"]["persist_features"]


# ======================================================================================================================
# Spatio-Temporal Momentum (joint-universe network trained on the Sharpe ratio)
# ======================================================================================================================

class STMAdapter(ProjectAdapter):
    """The two STM folders run the same code; they differ by their universe definition (and names)."""

    def __init__(self, key: str, folder: str, manager_class: str, label: str, universe_modes: Tuple[str, ...]):
        self.key = key
        self.folder = folder
        self.config_module = f"src.application.managers.project_managers.{folder}.config"
        self.manager_path = f"src.application.managers.project_managers.{folder}.project_manager:{manager_class}"
        self.label = label
        self.universe_modes = universe_modes
        self.report_renderer = ("src.application.services.data.entities.factor.spatio_temporal_momentum."
                                "stm_report_renderer")

    def capabilities(self) -> ProjectCapabilities:
        return ProjectCapabilities(
            key=self.key, label=self.label, strategy_type="spatio_temporal_momentum",
            description="One network over the whole universe (TFT) outputs a position signal per asset, trained "
                        "to maximise the Sharpe ratio of its vol-scaled positions.",
            folder=f"project_managers/{self.folder}",
            model_families=("tft",), output_contract=POSITION_SIGNAL, portfolio_rules=("vol_scaled_signal",),
            long_short=True, long_only=False, decision_frequencies=("1 day",), universe_modes=self.universe_modes,
            lifecycle=("backtest",), trains_inside_backtest=True,
            unsupported=COMMON_UNSUPPORTED + (
                "model types lstm / slp / mlp / conv (forward-pass tested only, not run end to end in the engine)",
                "expanding training window in the engine (rolling only)", "classification target",
            ),
        )

    def _universe_defaults(self, c: Dict[str, Any]) -> Dict[str, Any]:
        m, u = self.module(), c["stm"]["universe"]
        mode = "sector_sample" if u.get("n_per_sector") else "explicit"
        return {"mode": mode, "name": u["name"], "tickers": list(m.STM_TICKERS),
                "n_per_sector": u.get("n_per_sector") or 2, "seed": u.get("seed") if u.get("seed") is not None
                else 42}

    def schema(self) -> ConfigurationSchema:
        c = self.base_config()
        stm = c["stm"]
        f, mdl, tr = stm["features"], stm["model"], stm["training"]
        p = mdl["params"]
        u = self._universe_defaults(c)
        return ConfigurationSchema(self.key, sections=(
            SectionSchema("universe", label="Universe", fields=(
                FieldSpec("mode", "choice", u["mode"], "Selection", choices=self.universe_modes),
                FieldSpec("name", "str", u["name"], "Universe name", required=True),
                FieldSpec("tickers", "str_list", u["tickers"], "Constituents (explicit mode)"),
                FieldSpec("n_per_sector", "int", u["n_per_sector"], "Stocks per sector (sector sample)", minimum=1),
                FieldSpec("seed", "int", u["seed"], "Sampling seed (sector sample)"),
            )),
            SectionSchema("factors", label="Features (windows in sessions)", fields=(
                FieldSpec("return_horizons", "int_list", list(f["return_horizons"]), "Normalised return horizons",
                          minimum=1),
                FieldSpec("vol_lookback", "int", f["vol_lookback"], "Volatility EWM span", minimum=2),
                FieldSpec("macd_combinations", "int_pair_list", [list(x) for x in f["macd_combinations"]],
                          "MACD (short, long) pairs"),
                FieldSpec("macd_price_std_window", "int", f["macd_price_std_window"], "MACD price std window",
                          minimum=2),
                FieldSpec("macd_signal_std_window", "int", f["macd_signal_std_window"], "MACD signal std window",
                          minimum=2),
                FieldSpec("winsorise_halflife", "int", f["winsorise_halflife"], "Winsorisation half-life",
                          minimum=1),
                FieldSpec("winsorise_threshold", "float", f["winsorise_threshold"], "Winsorisation threshold (sd)",
                          minimum=0.5),
            )),
            SectionSchema("model", label="Model (TFT parameters apply to the TFT only)", fields=(
                FieldSpec("model_type", "choice", mdl["model_type"], "Model", choices=_stm_model_choices(),
                          help="tft = Temporal Fusion Transformer, lstm, mlp, slp = single-layer perceptron, "
                               "conv = temporal convolution"),
                FieldSpec("lookback", "int", mdl["lookback"], "Input window (sessions)", minimum=2),
                FieldSpec("encoder_length", "int", mdl["encoder_length"], "Encoder steps", minimum=1),
                FieldSpec("emb_dim", "int", p["emb_dim"], "Embedding size", minimum=1),
                FieldSpec("prescale_dim", "int", p["prescale_dim"], "Prescale size", minimum=1),
                FieldSpec("hidden_dim", "int", p["hidden_dim"], "Hidden size", minimum=1),
                FieldSpec("n_heads", "int", p["n_heads"], "Attention heads", minimum=1),
                FieldSpec("dropout", "float", p["dropout"], "Dropout", minimum=0.0, maximum=0.9),
            )),
            SectionSchema("training", label="Training (Sharpe loss)", fields=(
                FieldSpec("training_window", "int", c["training_window"], "Rolling training window (sessions)",
                          minimum=10),
                FieldSpec("retrain_every_days", "int", c["retrain_every_days"], "Retrain every (calendar days)",
                          "Also retrains when a model's assets are no longer all eligible", minimum=1),
                FieldSpec("val_days", "int", tr["val_days"], "Validation sessions (latest)", minimum=1),
                FieldSpec("purge_days", "int", tr["purge_days"], "Purge between train and validation", minimum=0),
                FieldSpec("n_epochs", "int", tr["n_epochs"], "Maximum epochs", minimum=1),
                FieldSpec("early_stopping_rounds", "int", tr["early_stopping_rounds"], "Early stopping patience",
                          minimum=1),
                FieldSpec("batch_size", "int", tr["batch_size"], "Batch size", minimum=1),
                FieldSpec("lr", "float", tr["lr"], "Learning rate", minimum=1e-6, maximum=1.0),
                FieldSpec("weight_decay", "float", tr["weight_decay"], "Weight decay", minimum=0.0),
                FieldSpec("scaling", "choice", tr["scaling"], "Feature scaling (fit on train only)",
                          choices=(None, "standard", "minmax"), nullable=True),
                FieldSpec("apply_l1_reg", "bool", tr["apply_l1_reg"], "L1 regularisation"),
                FieldSpec("apply_turnover_reg", "bool", tr["apply_turnover_reg"], "Turnover regularisation"),
                FieldSpec("seed", "int", tr["seed"], "Random seed"),
            )),
            SectionSchema("portfolio", label="Portfolio construction", fields=(
                FieldSpec("rule", "choice", "vol_scaled_signal", "Rule", choices=("vol_scaled_signal",)),
                FieldSpec("target_vol", "float", f["vol_target"], "Target volatility (annualised)", minimum=0.01,
                          maximum=1.0),
                FieldSpec("gross_exposure_cap", "float", c["gross_exposure_cap"], "Gross exposure cap",
                          minimum=0.01, maximum=2.0),
            )),
            SectionSchema("trading", label="Trading", fields=(
                FieldSpec("decision_frequency", "choice", c["bar_size_setting"], "Decision / rebalance / execution",
                          "One clock: a decision, a rebalance and its orders at each session",
                          choices=(c["bar_size_setting"],)),
            )),
            self._evaluation_section(c, "Daily history imported before the first decision: the rolling training "
                                        "window and the feature warm-up"),
        ))

    def default_sections(self) -> Sections:
        return self.schema().defaults()

    def _feature_config(self, s: Sections):
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
            STMFeatureConfig,
        )
        base = self.base_config()["stm"]["features"]
        f = s["factors"]
        return STMFeatureConfig(**{**base, "return_horizons": tuple(f["return_horizons"]),
                                   "vol_lookback": f["vol_lookback"],
                                   "macd_combinations": tuple(tuple(x) for x in f["macd_combinations"]),
                                   "macd_price_std_window": f["macd_price_std_window"],
                                   "macd_signal_std_window": f["macd_signal_std_window"],
                                   "winsorise_halflife": f["winsorise_halflife"],
                                   "winsorise_threshold": f["winsorise_threshold"],
                                   "vol_target": s["portfolio"]["target_vol"]})

    def _project_checks(self, s: Sections) -> List[ValidationIssue]:
        issues = []
        u, m, t = s["universe"], s["model"], s["training"]
        if u["mode"] == "explicit" and not u["tickers"]:
            issues.append(ValidationIssue("universe", "tickers", "required in explicit mode"))
        default = self._universe_defaults(self.base_config())
        if u["name"] == default["name"] and (u["mode"] != default["mode"] or (
                u["mode"] == "explicit" and u["tickers"] != default["tickers"]) or (
                u["mode"] == "sector_sample" and (u["n_per_sector"], u["seed"]) != (default["n_per_sector"],
                                                                                    default["seed"]))):
            issues.append(ValidationIssue("universe", "name", "a different universe definition needs its own name"))
        if m["model_type"] == "tft" and not m["encoder_length"] < m["lookback"]:
            issues.append(ValidationIssue("model", "encoder_length", "must be smaller than the input window"))
        if m["lookback"] > t["training_window"]:
            issues.append(ValidationIssue("model", "lookback", "cannot exceed the training window"))
        if t["val_days"] >= t["training_window"]:
            issues.append(ValidationIssue("training", "val_days", "must be smaller than the training window"))
        bad = [p for p in s["factors"]["macd_combinations"] if not p[0] < p[1]]
        if bad:
            issues.append(ValidationIssue("factors", "macd_combinations", f"short < long required: {bad}"))
        if not s["factors"]["return_horizons"]:
            issues.append(ValidationIssue("factors", "return_horizons", "at least one horizon is required"))
        if not issues:
            needed = max(t["training_window"], self._feature_config(s).required_history_days(m["lookback"]))
            have = _bdays(s["evaluation"]["price_history_start"], s["evaluation"]["backtest_start"])
            if have < needed:
                issues.append(ValidationIssue("evaluation", "price_history_start",
                                              f"{have} sessions before backtest_start; an asset needs {needed}"))
        return issues

    def _apply(self, c: Dict[str, Any], s: Sections) -> None:
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_universe import (
            select_reference_universe,
        )
        from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
        stm = c["stm"]
        u = s["universe"]
        default = self._universe_defaults(self.base_config())
        if u["mode"] == "sector_sample":
            same = (u["n_per_sector"], u["seed"]) == (default["n_per_sector"], default["seed"])
            constituents = importlib.import_module(
                f"src.application.managers.project_managers.{self.folder}.data.sector_constituents").SECTOR_CONSTITUENTS
            tickers = (list(self.module().STM_TICKERS) if same
                       else select_reference_universe(constituents, n_per_sector=u["n_per_sector"], seed=u["seed"]))
            stm["universe"].update(n_per_sector=u["n_per_sector"], seed=u["seed"])
        else:
            tickers = list(u["tickers"])
            if default["mode"] != "explicit":
                stm["universe"].update(n_per_sector=None, seed=None)
        stm["universe"]["name"] = u["name"]
        stm["universe"]["tickers"] = None if tickers == list(self.module().STM_TICKERS) else tickers
        c["universe"] = {CompanyShare: tickers}
        f = s["factors"]
        stm["features"].update(
            return_horizons=tuple(f["return_horizons"]), vol_lookback=f["vol_lookback"],
            macd_combinations=tuple(tuple(x) for x in f["macd_combinations"]),
            macd_price_std_window=f["macd_price_std_window"], macd_signal_std_window=f["macd_signal_std_window"],
            winsorise_halflife=f["winsorise_halflife"], winsorise_threshold=f["winsorise_threshold"],
            vol_target=s["portfolio"]["target_vol"])
        m = s["model"]
        stm["model"].update(model_type=m["model_type"], lookback=m["lookback"], encoder_length=m["encoder_length"])
        stm["model"]["params"] = {**stm["model"]["params"], **{k: m[k] for k in (
            "emb_dim", "prescale_dim", "hidden_dim", "n_heads", "dropout")}}
        from src.application.services.strategy.model_catalog import stm_model_parameters
        accepted = stm_model_parameters(m["model_type"])         # only what the chosen network takes
        stm["model"]["params"] = {k: v for k, v in stm["model"]["params"].items() if k in accepted}
        t = s["training"]
        for k in ("val_days", "purge_days", "n_epochs", "early_stopping_rounds", "batch_size", "lr", "weight_decay",
                  "scaling", "apply_l1_reg", "apply_turnover_reg", "seed"):
            stm["training"][k] = t[k]
        stm["training"]["rolling_window_rows"] = t["training_window"]
        stm["training"]["target_vol"] = s["portfolio"]["target_vol"]
        c["training_window"] = t["training_window"]
        c["retrain_every_days"] = t["retrain_every_days"]
        c["gross_exposure_cap"] = s["portfolio"]["gross_exposure_cap"]


def _stm_model_choices() -> Tuple[str, ...]:
    from src.application.services.strategy.model_catalog import model_choices
    return tuple(model_choices({"stm": {}}))


PROJECTS_PACKAGE = "src.application.managers.project_managers"
# never launched from the web interface (live trading / not a backtest)
NOT_LAUNCHABLE = ("spatio_temporal_momentum_project_10m_live", "etf_dispersion_screener_project")


class ProjectFolderAdapter(ProjectAdapter):
    """Any project folder, driven by a Strategy (no web form of its own): the strategy is applied onto the
    project's own config (``strategy_project_config.apply_strategy``) and the project's manager runs it.
    Launchable when the manager takes ``config`` and ``database_service`` and the project is a backtest."""

    requires_report = False                     # its run returns the project's own results (no report object)

    def __init__(self, folder: str):
        self.key = folder
        self.folder = folder
        self.config_module = f"{PROJECTS_PACKAGE}.{folder}.config"

    def base_config(self) -> Dict[str, Any]:
        module = self.module()                  # deep: get_config() copies are shallow
        return copy.deepcopy(module.get_config() if hasattr(module, "get_config") else module.DEFAULT_CONFIG)

    def manager_class(self):
        import inspect
        module = importlib.import_module(f"{PROJECTS_PACKAGE}.{self.folder}.project_manager")
        classes = [c for name, c in inspect.getmembers(module, inspect.isclass)   # by name: no import of the
                   if c.__module__ == module.__name__ and name.endswith("ProjectManager")   # managers package
                   and callable(getattr(c, "run", None))]
        if not classes:
            raise LookupError(f"project {self.folder} has no project manager class")
        return classes[0]

    @property
    def launchable(self) -> bool:
        import inspect
        if self.folder in NOT_LAUNCHABLE:
            return False
        try:
            params = inspect.signature(self.manager_class().__init__).parameters
        except Exception:
            return False
        return "config" in params and "database_service" in params

    def renderer(self):
        raise LookupError(f"project {self.folder} has no report renderer: see its results folder")

    def capabilities(self) -> ProjectCapabilities:
        from src.application.services.strategy.model_catalog import model_choices
        config = self.base_config()
        return ProjectCapabilities(
            key=self.key, label=f"project {self.folder}", strategy_type=self.folder,
            description="registered from the project's own config; designed strategies are applied onto it",
            folder=self.folder, model_families=tuple(model_choices(config)), output_contract=POSITION_SIGNAL,
            portfolio_rules=(), long_short=True, long_only=False,
            decision_frequencies=(str(config.get("bar_size_setting") or ""),), universe_modes=("explicit",),
            lifecycle=("backtest",) if self.launchable else (), trains_inside_backtest=True)

    def schema(self) -> ConfigurationSchema:
        return ConfigurationSchema(self.key, ())

    def default_sections(self) -> Sections:
        from src.application.services.strategy.project_strategy_registration import strategy_sections
        return strategy_sections(self.base_config())

    def validate(self, sections: Sections) -> Tuple[Sections, List[ValidationIssue]]:
        """No schema: the sections are the project's own config values (checked by the project when it runs)."""
        return copy.deepcopy(sections), []

    def validate_strategy(self, strategy) -> Tuple[Sections, List[ValidationIssue]]:
        """The strategy as the project would run it: it must apply onto the project's config."""
        from src.application.services.strategy.model_catalog import model_choices
        issues: List[ValidationIssue] = []
        choices = model_choices(self.base_config())
        if strategy.model_type and choices and strategy.model_type not in choices:
            issues.append(ValidationIssue("model", "model_type", f"'{strategy.model_type}' is not available for "
                                                                 f"this project (choices: {', '.join(choices)})"))
        if not issues:
            try:
                self.native_config_for(strategy, strategy.sections)
            except Exception as e:
                issues.append(ValidationIssue("strategy", None, f"cannot be applied to the project's config: {e}"))
        return copy.deepcopy(strategy.sections), issues

    def definition(self, sections: Sections) -> Dict[str, Any]:
        return {}                               # the strategy's typed fields are authoritative (set in the design)

    def initial_definition(self) -> Dict[str, Any]:
        """A new draft's typed fields (model, frequencies, training...): what the project's own config runs today,
        as a project registers its strategy when it runs."""
        from src.application.services.strategy.strategy_definition import strategy_definition
        return {k: v for k, v in strategy_definition(self.base_config()).items() if v is not None and k != "universe_id"}

    def native_config_for(self, strategy, sections: Sections, results_dir: Optional[str] = None,
                          portfolio_name: Optional[str] = None) -> Dict[str, Any]:
        from src.application.services.strategy.strategy_project_config import apply_strategy
        config = apply_strategy(self.base_config(), strategy)
        if results_dir:
            config["results_dir"] = results_dir
        if portfolio_name and isinstance(config.get("Portfolio"), dict):
            config["Portfolio"]["name"] = portfolio_name
        return config

    def native_config(self, sections: Sections, results_dir: Optional[str] = None,
                      portfolio_name: Optional[str] = None) -> Dict[str, Any]:
        raise TypeError("a project-folder strategy translates with native_config_for(strategy, ...)")


def is_project_folder(key: str) -> bool:
    if not key or not key.replace("_", "").isalnum():
        return False
    try:
        importlib.import_module(f"{PROJECTS_PACKAGE}.{key}.config")
        return True
    except ImportError:
        return False


def project_folders() -> List[str]:
    """Every project folder under project_managers that has a config module (sorted)."""
    import pkgutil
    package = importlib.import_module(PROJECTS_PACKAGE)
    return sorted(m.name for m in pkgutil.iter_modules(package.__path__) if m.ispkg and is_project_folder(m.name))


def project_title(folder: str) -> str:
    """A readable name for a project folder: the first sentence of its package docstring, else the folder name."""
    try:
        doc = (importlib.import_module(f"{PROJECTS_PACKAGE}.{folder}").__doc__ or "").strip()
    except Exception:
        doc = ""
    first = doc.split("\n\n", 1)[0].replace("\n", " ").strip()
    first = first.split(". ", 1)[0].rstrip(".:")
    return f"{first} ({folder})" if first else folder


def default_adapters() -> List[ProjectAdapter]:
    return [
        CrossSectionalAdapter(),
        STMAdapter("stm_reference", "spatio_temporal_momentum_project", "SpatioTemporalMomentumProjectManager",
                   "Spatio-Temporal Momentum — reference sector sample", ("sector_sample", "explicit")),
        STMAdapter("stm_paper", "spatio_temporal_momentum_project_full", "SpatioTemporalMomentumFullProjectManager",
                   "Spatio-Temporal Momentum — paper universe (48 US financials)", ("explicit",)),
    ]


class ProjectRegistry:
    """Explicit registry of the project implementations a strategy configuration can use."""

    def __init__(self, adapters: Optional[List[ProjectAdapter]] = None):
        self._adapters: Dict[str, ProjectAdapter] = {}
        self._folders: Dict[str, ProjectAdapter] = {}            # project folders driven by a Strategy (lazy)
        for adapter in adapters if adapters is not None else default_adapters():
            self.register(adapter)

    def register(self, adapter: ProjectAdapter) -> None:
        if adapter.key in self._adapters:
            raise ValueError(f"project '{adapter.key}' is already registered")
        self._adapters[adapter.key] = adapter

    def get(self, key: str) -> ProjectAdapter:
        try:
            return self._adapters[key]
        except KeyError:
            pass
        if key not in self._folders and is_project_folder(key):
            self._folders[key] = ProjectFolderAdapter(key)
        if key in self._folders:
            return self._folders[key]
        raise KeyError(f"unknown project '{key}' (registered: {sorted(self._adapters)})")

    def keys(self) -> List[str]:
        """The projects with a web form (schema). Any project folder is also reachable through get()."""
        return list(self._adapters)

    def has_form(self, key: str) -> bool:
        return key in self._adapters

    def capabilities(self) -> List[ProjectCapabilities]:
        return [a.capabilities() for a in self._adapters.values()]

    def folder_capabilities(self) -> List[ProjectCapabilities]:
        """The project folders a strategy can also start from (no web form: designed in the strategy designer, then
        applied onto the project's own config). Folders a registered adapter already covers are left out, and so are
        projects that are not backtests (NOT_LAUNCHABLE) or whose config / manager cannot be loaded."""
        covered = {str(a.capabilities().folder or "").rstrip("/").rsplit("/", 1)[-1] for a in self._adapters.values()}
        out = []
        for folder in project_folders():
            if folder in covered or folder in self._adapters or folder in NOT_LAUNCHABLE:
                continue
            try:
                adapter = self.get(folder)
                if not getattr(adapter, "launchable", False):
                    continue
                caps = adapter.capabilities()
            except Exception:                       # a broken project never hides the others
                continue
            out.append(dataclasses.replace(caps, label=project_title(folder), description=(
                f"project folder {folder}: starts from the project's own config, then designed in the strategy "
                f"designer")))
        return out


Factory = Callable[[], ProjectRegistry]
