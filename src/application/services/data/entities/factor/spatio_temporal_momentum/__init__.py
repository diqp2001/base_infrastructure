"""
Spatio-Temporal Momentum (STM) — reusable research components.

Port of the PyTorch reference implementation of
"Spatio-Temporal Momentum: Jointly Learning Time-Series and Cross-Sectional
Strategies" (Tan, Roberts, Zohren 2023):
https://github.com/KurochkinAlexey/SpatioTemporalMomentum

Pure components (no DB):
    stm_configuration   — all research parameters in one place
    stm_features        — DeepMomentum + MACD features (causal port)
    stm_dataset         — [assets x lookback x features] tensors, walk-forward splits
    stm_tft / stm_models — reference architectures + joint universe wrapper
    stm_losses          — Sharpe loss + regularisers
    stm_training        — reference training loop (one walk-forward window)
    stm_metrics         — empyrical-equivalent performance metrics
    stm_backtest        — captured returns with turnover costs + baselines

Infrastructure-facing components (use the RepositoryFactory):
    stm_price_history   — daily closes from factor_values
    stm_universe        — Universe / UniverseConstituent registration
    stm_feature_store   — feature + signal FactorValues
    stm_artifact_store  — MLModel / ModelTraining / TrainingMetric / ModelArtifact
    stm_model_provider  — inference provider injected into the signal factor
"""
