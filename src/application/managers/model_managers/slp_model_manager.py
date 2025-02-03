import pickle
import pandas as pd
import numpy as np
from typing import Dict, Any
import torch
from torch import nn, optim
from src.application.managers.model_managers.model_manager import ModelManager

class SLPModelManager(ModelManager):
    def __init__(self, input_size: int,  output_size: int, target_column: str = 'price close', num_layers: int = 2):
        super().__init__()
        self.input_size = input_size
        self.output_size = output_size
        self.num_layers = num_layers
        self.target_column = target_column
        self.model = self._build_model()

    def _build_model(self) -> nn.Module:
        """
        Build the SLP model.
        """
        class SLP(nn.Module):
            def __init__(self, input_dim, output_dim, timesteps, cat_info=None):
                super().__init__()
                self.layer = nn.Linear(input_dim * timesteps, output_dim * timesteps)
                self.timesteps = timesteps
                self.output_dim = output_dim

            def forward(self, x):
                x = x.flatten(start_dim=1)
                out = self.layer(x)
                out = out.view(out.shape[0], self.timesteps, self.output_dim)
                out = torch.tanh(out)
                return out

        return SLP(self.input_size, self.output_dim)

    