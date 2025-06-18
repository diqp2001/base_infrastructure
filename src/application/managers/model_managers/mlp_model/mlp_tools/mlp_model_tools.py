import os
import pickle
import random
import pandas as pd
import numpy as np
from typing import Dict, Any
import torch
from torch import nn, optim

def reg_l1(model, alpha=1e-4):
    l = 0
    for p in model.parameters():
        l += torch.mean(torch.abs(p))
    
    l = alpha*l
    
    return l

def reg_turnover(preds, vol, mask=None, alpha=1e-4, is_l1=True, target_vol=0.15, C=5):
    if mask is not None:
        preds = preds*mask
        vol = vol*mask
    
    vol = vol*252**0.5
    y = preds/(vol + 1e-12)
    y = torch.diff(y, dim=1)
    
    if is_l1:
        y = torch.abs(y)
    else:
        y = y**2      
        
    l = alpha*C*target_vol*torch.mean(y)    
    
    return l

def sharpe_loss(preds, returns, weights=None, mask=None):
    R = preds*returns
    if mask is not None:
        R = R*mask

    R_sum = torch.mean(R, dim=(1, 0))
    R_sum_sq = R_sum**2
    R_sq_sum = torch.mean(R**2, dim=(1, 0))
    
    sharpe = -1*252**0.5*R_sum/torch.sqrt(R_sq_sum - R_sum_sq + 1e-9)
    
    if returns.shape[2] != 1:
        if weights is None:
            sharpe = sharpe * 1/returns.shape[2]
        else:
            raise NotImplementedError

        sharpe = torch.sum(sharpe)
    else:
        sharpe = torch.mean(sharpe)
    
    return sharpe
def sharpe_ratio(R, rf=0, annualization_factor=252):
    excess_returns =  R - rf

    mean_excess_return = np.mean(excess_returns)
    std_excess_return = np.std(excess_returns)

    sharpe_ratio = (mean_excess_return/std_excess_return)*np.sqrt(annualization_factor)
    return sharpe_ratio
