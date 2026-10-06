"""
Losses and regularisers — verbatim port of the reference `src/utils.py`.

Tensor layout: preds / returns / vol are [batch, timesteps, n_assets].
"""

from __future__ import annotations

import torch


def reg_l1(model, alpha: float = 1e-4):
    l = 0
    for p in model.parameters():
        l += torch.mean(torch.abs(p))
    return alpha * l


def reg_turnover(preds, vol, mask=None, alpha: float = 1e-4, is_l1: bool = True, target_vol: float = 0.15, C: float = 5):
    if mask is not None:
        preds = preds * mask
        vol = vol * mask
    vol = vol * 252 ** 0.5
    y = preds / (vol + 1e-12)
    y = torch.diff(y, dim=1)
    y = torch.abs(y) if is_l1 else y ** 2
    return alpha * C * target_vol * torch.mean(y)


def sharpe_loss(preds, returns, weights=None, mask=None):
    """Negative annualised Sharpe of captured returns, averaged over assets."""
    R = preds * returns
    if mask is not None:
        R = R * mask

    R_sum = torch.mean(R, dim=(1, 0))
    R_sum_sq = R_sum ** 2
    R_sq_sum = torch.mean(R ** 2, dim=(1, 0))

    sharpe = -1 * 252 ** 0.5 * R_sum / torch.sqrt(R_sq_sum - R_sum_sq + 1e-9)

    if returns.shape[2] != 1:
        if weights is None:
            sharpe = sharpe * 1 / returns.shape[2]
        else:
            raise NotImplementedError
        sharpe = torch.sum(sharpe)
    else:
        sharpe = torch.mean(sharpe)
    return sharpe
