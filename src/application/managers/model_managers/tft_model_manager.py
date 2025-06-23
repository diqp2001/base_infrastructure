import pickle
import pandas as pd
import numpy as np
from typing import Dict, Any
import torch
from torch import nn, optim
from src.application.managers.model_managers.model_manager import ModelManager

class TFTModelManager(ModelManager):
    def __init__(self, input_size: int, hidden_size: int, output_size: int, target_column: str = 'price close', num_layers: int = 2):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.num_layers = num_layers
        self.target_column = target_column
        self.model = self._build_model()

    def _build_model(self) -> nn.Module:
        """
        Build the TFT model.
        """
        class TFT(nn.Module):
            def __init__(self, input_size, hidden_size, output_size, num_layers):
                super(TFT, self).__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
                self.fc = nn.Linear(hidden_size, output_size)

            def forward(self, x):
                h_lstm, _ = self.lstm(x)
                out = self.fc(h_lstm[:, -1, :])
                return out

        return TFT(self.input_size, self.hidden_size, self.output_size, self.num_layers)

    def train(self, features: pd.DataFrame, target: pd.Series, epochs: int = 10, lr: float = 0.001) -> None:
        """
        Train the TFT model.
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

    def evaluate(self, model: Any, test_data: pd.DataFrame) -> Dict[str, float]:
        """
        Evaluate the TFT model.
        """
        X_test = torch.tensor(test_data.drop(columns=[self.target_column]).values, dtype=torch.float32)
        y_test = torch.tensor(test_data[self.target_column].values, dtype=torch.float32).view(-1, 1)
        y_pred = model(X_test)
        mse = nn.MSELoss()(y_pred, y_test).item()
        return {"MSE": mse}