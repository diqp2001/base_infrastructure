import pickle
import pandas as pd
import numpy as np
from typing import Dict, Any
import torch
from torch import nn, optim
from src.application.managers.model_managers.model_manager import ModelManager

class MLPModelManager(ModelManager):
    def __init__(self, input_size: int,  output_size: int, target_column: str = 'price close'):
        super().__init__()
        self.input_size = input_size
        self.output_size = output_size
        self.target_column = target_column
        self.model = self._build_model()

    def _build_model(self) -> nn.Module:
        """
        Build the MLP model.
        """
        class MLP(nn.Module):
                def __init__(self, input_dim, output_dim, timesteps, cat_info=None, mult=0.3):
                    super().__init__()

                    hidden_dim = int(input_dim * timesteps * mult)

                    self.hidden_layer = nn.Linear(input_dim * timesteps, hidden_dim)
                    self.bn = nn.BatchNorm1d(hidden_dim)
                    self.output_layer = nn.Linear(hidden_dim, output_dim * timesteps)
                    self.timesteps = timesteps
                    self.output_dim = output_dim

                def forward(self, x):
                    x = x.flatten(start_dim=1)
                    x = self.bn(self.hidden_layer(x))
                    x = torch.tanh(x)
                    out = self.output_layer(x)
                    out = out.view(out.shape[0], self.timesteps, self.output_dim)
                    out = torch.tanh(out)
                    return out

        return MLP(self.input_size, self.output_dim)