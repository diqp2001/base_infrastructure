"""
Training loop for one walk-forward window — port of the reference
train_multivariate.ipynb cell 19 (non-TFT and TFT branches unified through
SpatioTemporalMomentumNet.forward_sequence).

Reference behaviour kept:
  * seed reset immediately before model construction (_set_seed)
  * Adam(lr, weight_decay) + StepLR(decay_steps, gamma), scheduler only steps
    while lr > min_lr
  * loss = sharpe_loss(output_sequence, y) (+ optional L1 / turnover reg.)
  * validation metric = Sharpe of last-step captured returns at 0 bps
  * checkpoint only when val Sharpe improves AND epoch > 0
  * stop when the no-improvement counter exceeds early_stopping_rounds

Difference: if no checkpoint was ever saved (possible with very short runs)
the final weights are kept instead of failing to load a missing file.
"""

from __future__ import annotations

import copy
import os
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_backtest import (
    captured_returns,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMTrainingConfig,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import SampleSet
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_losses import (
    reg_l1,
    reg_turnover,
    sharpe_loss,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_metrics import sharpe_ratio


def set_seed(seed: int) -> None:
    """Reference _set_seed."""
    np.random.seed(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def _seed_worker(worker_id):
    worker_seed = torch.initial_seed() % 2 ** 32
    np.random.seed(worker_seed)
    random.seed(worker_seed)


def _loader(samples: SampleSet, batch_size: int, shuffle: bool, seed: int) -> DataLoader:
    ds = TensorDataset(
        torch.tensor(samples.X, dtype=torch.float32),
        torch.tensor(samples.y, dtype=torch.float32),
        torch.tensor(samples.y_orig, dtype=torch.float32),
        torch.tensor(samples.vol, dtype=torch.float32),
    )
    g = torch.Generator()
    g.manual_seed(seed)
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle, worker_init_fn=_seed_worker, generator=g)


@dataclass
class TrainResult:
    state_dict: Dict[str, torch.Tensor]
    best_val_sharpe: float
    best_epoch: Optional[int]
    epochs_run: int
    train_losses: List[float] = field(default_factory=list)
    val_losses: List[float] = field(default_factory=list)
    val_sharpes: List[Dict[int, float]] = field(default_factory=list)


@torch.no_grad()
def predict_last_step(model, samples: SampleSet, batch_size: int, device: str = "cpu") -> np.ndarray:
    """Model signal at the last time step for every sample: [S, N]."""
    if len(samples) == 0:
        return np.zeros((0, samples.y.shape[2] if samples.y.ndim == 3 else 0))
    model.eval()
    out = []
    X = torch.tensor(samples.X, dtype=torch.float32)
    for i in range(0, len(X), batch_size):
        out.append(model(X[i:i + batch_size].to(device)).cpu().numpy())
    return np.concatenate(out)


def train_window(
    model_factory: Callable[[], torch.nn.Module],
    train: SampleSet,
    val: SampleSet,
    cfg: STMTrainingConfig,
    log: Optional[Callable[[str], None]] = None,
) -> TrainResult:
    if len(train) == 0 or len(val) == 0:
        raise ValueError(f"Empty fold (train={len(train)}, val={len(val)})")
    log = log or (lambda msg: None)
    device = cfg.device

    set_seed(cfg.seed)
    model = model_factory().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    sc = torch.optim.lr_scheduler.StepLR(opt, cfg.lr_decay_steps, cfg.lr_decay_gamma)

    train_loader = _loader(train, cfg.batch_size, True, cfg.seed)
    val_loader = _loader(val, cfg.batch_size, False, cfg.seed)

    best_val_sharpe = -np.inf
    best_state = None
    best_epoch = None
    counter = 0
    result = TrainResult(state_dict={}, best_val_sharpe=float("nan"), best_epoch=None, epochs_run=0)

    for e in range(cfg.n_epochs):
        model.train()
        train_loss = 0.0
        for batch_x, batch_y, _, batch_vol in train_loader:
            batch_x, batch_y, batch_vol = batch_x.to(device), batch_y.to(device), batch_vol.to(device)
            opt.zero_grad()
            output = model.forward_sequence(batch_x)
            loss = sharpe_loss(output, batch_y)
            train_loss += loss.item()
            if cfg.apply_l1_reg:
                loss = loss + reg_l1(model, cfg.l1_alpha)
            if cfg.apply_turnover_reg:
                loss = loss + reg_turnover(output, batch_vol, alpha=cfg.turnover_alpha, target_vol=cfg.target_vol)
            loss.backward()
            opt.step()

        # "we do not want learning rate to be too small"
        if sc.get_last_lr()[0] > cfg.min_lr:
            sc.step()

        model.eval()
        val_loss, preds, returns, vols = 0.0, [], [], []
        with torch.no_grad():
            for batch_x, batch_y, _, batch_vol in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                output = model.forward_sequence(batch_x)
                val_loss += sharpe_loss(output, batch_y).item()
                returns.append(batch_y[:, -1, :].cpu().numpy())
                preds.append(output[:, -1, :].cpu().numpy())
                vols.append(batch_vol[:, -1, :].cpu().numpy())

        preds_a, returns_a, vols_a = np.concatenate(preds), np.concatenate(returns), np.concatenate(vols)
        val_sharpes = {
            c: sharpe_ratio(captured_returns(preds_a, returns_a, vols_a, c, cfg.target_vol))
            for c in cfg.basis_points
        }
        val_sharpe = val_sharpes[0] if 0 in val_sharpes else next(iter(val_sharpes.values()))

        if best_val_sharpe < val_sharpe and e > 0:
            best_val_sharpe = val_sharpe
            counter = 0
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = e
        else:
            counter += 1

        result.train_losses.append(train_loss / max(len(train_loader), 1))
        result.val_losses.append(val_loss / max(len(val_loader), 1))
        result.val_sharpes.append(val_sharpes)
        result.epochs_run = e + 1
        log(f"epoch {e}: train_loss={result.train_losses[-1]:.4f} val_loss={result.val_losses[-1]:.4f} "
            f"val_sharpe={val_sharpe:.3f} lr={sc.get_last_lr()[0]:.2e}")

        if counter > cfg.early_stopping_rounds:
            break

    result.state_dict = best_state if best_state is not None else copy.deepcopy(model.state_dict())
    result.best_val_sharpe = float(best_val_sharpe) if best_state is not None else float("nan")
    result.best_epoch = best_epoch
    return result
