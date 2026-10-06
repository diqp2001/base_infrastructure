"""
SpatioTemporalMomentumNet — joint-universe wrapper around the reference models.

The reference multivariate setup ("each asset is used as feature") feeds the
models a tensor of shape [batch, lookback, n_assets * n_features] in
asset-major order (asset_0 features, asset_1 features, ...) and reads one
output per asset: [batch, target_timesteps, n_assets].  Cross-sectional
information flows because every asset's features enter the same network.

This wrapper exposes the conceptual API

    signals = model(X)        X: [batch, n_assets, lookback, n_features]
                              signals: [batch, n_assets]   (last time step)

and ``forward_sequence`` for training, which returns every time step like the
reference.  The wrapped architecture is the unchanged reference class.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import torch
from torch import nn

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_simple_models import (
    LSTMnet, MLP, SLP, TCN,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_tft import TFT

# Reference train_multivariate.ipynb MODEL_MAPPING
MODEL_MAPPING = {
    "lstm": LSTMnet,
    "slp": SLP,
    "mlp": MLP,
    "conv": TCN,
    "tft": TFT,
}


class SpatioTemporalMomentumNet(nn.Module):
    def __init__(
        self,
        n_assets: int,
        n_features: int,
        lookback: int,
        model_type: str = "tft",
        encoder_length: Optional[int] = None,
        model_params: Optional[Dict[str, Any]] = None,
    ):
        super().__init__()
        if model_type not in MODEL_MAPPING:
            raise ValueError(f"Unknown model_type '{model_type}'. Allowed: {sorted(MODEL_MAPPING)}")
        self.n_assets = n_assets
        self.n_features = n_features
        self.lookback = lookback
        self.model_type = model_type
        self.is_tft = model_type == "tft"
        params = dict(model_params or {})

        if self.is_tft:
            if encoder_length is None or not (0 < encoder_length < lookback):
                raise ValueError("TFT needs 0 < encoder_length < lookback")
            self.encoder_length = int(encoder_length)
            params.setdefault("device", "cpu")
        else:
            self.encoder_length = None

        self.core = MODEL_MAPPING[model_type](
            n_assets * n_features, n_assets, lookback, cat_info=None, **params
        )

    @property
    def target_timesteps(self) -> int:
        return self.lookback - self.encoder_length if self.is_tft else self.lookback

    def _to_reference_layout(self, x: torch.Tensor) -> torch.Tensor:
        """[B, N, T, F] -> [B, T, N*F] (asset-major, identical to the reference concatenation)."""
        if x.dim() != 4:
            raise ValueError(f"Expected X of shape [batch, assets, lookback, features], got {tuple(x.shape)}")
        b, n, t, f = x.shape
        if n != self.n_assets or t != self.lookback or f != self.n_features:
            raise ValueError(
                f"X shape {tuple(x.shape)} does not match model "
                f"(assets={self.n_assets}, lookback={self.lookback}, features={self.n_features})"
            )
        return x.permute(0, 2, 1, 3).reshape(b, t, n * f)

    def forward_sequence(self, x: torch.Tensor) -> torch.Tensor:
        """Reference output: [B, target_timesteps, n_assets]."""
        x = self._to_reference_layout(x)
        if not self.is_tft:
            return self.core(x)
        enc = self.encoder_length
        x_enc, x_dec = x[:, :enc, :], x[:, enc:, :]
        enc_len = torch.full((x.shape[0],), x_enc.shape[1], dtype=torch.long, device=x.device)
        dec_len = torch.full((x.shape[0],), x_dec.shape[1], dtype=torch.long, device=x.device)
        return self.core(x_enc, None, x_dec, None, enc_len, dec_len)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """One signal per asset at the last time step: [B, n_assets]."""
        return self.forward_sequence(x)[:, -1, :]


def build_model(n_assets: int, n_features: int, model_cfg) -> SpatioTemporalMomentumNet:
    """Construct the wrapper from an STMModelConfig."""
    return SpatioTemporalMomentumNet(
        n_assets=n_assets,
        n_features=n_features,
        lookback=model_cfg.lookback,
        model_type=model_cfg.model_type,
        encoder_length=model_cfg.encoder_length if model_cfg.model_type == "tft" else None,
        model_params=model_cfg.params,
    )
