import pickle
import pandas as pd
import numpy as np
from typing import Dict, Any
import torch
from torch import nn, optim
from src.application.managers.model_managers.model_manager import ModelManager

class SLPModelManager(ModelManager):
    def __init__(self, input_size: int, output_size: int, timesteps: int, target_column: str = 'price close'):
        super().__init__()
        self.input_size = input_size
        self.output_size = output_size
        self.timesteps = timesteps
        self.target_column = target_column
        self.model = self._build_model()

    def _build_model(self) -> nn.Module:
        """
        Build the SLP model.
        """
        class SLP(nn.Module):
            def __init__(self, input_dim, output_dim, timesteps):
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

        return SLP(self.input_size, self.output_size, self.timesteps)

    def train(self, features: pd.DataFrame, target: pd.Series, epochs: int = 10, lr: float = 0.001) -> None:
        """
        Train the SLP model.
        """
        X = torch.tensor(features.values, dtype=torch.float32)
        y = torch.tensor(target.values, dtype=torch.float32).view(-1, 1)

        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=lr)

        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = self.model(X)
            loss = criterion(outputs, y)
            loss.backward()
            optimizer.step()

            print(f"Epoch {epoch+1}/{epochs}, Loss: {loss.item()}")

    def evaluate(self, test_data: pd.DataFrame) -> Dict[str, float]:
        """
        Evaluate the SLP model.
        """
        X_test = torch.tensor(test_data.drop(columns=[self.target_column]).values, dtype=torch.float32)
        y_test = torch.tensor(test_data[self.target_column].values, dtype=torch.float32).view(-1, 1)
        y_pred = self.model(X_test)
        mse = nn.MSELoss()(y_pred, y_test).item()
        return {"MSE": mse}

    