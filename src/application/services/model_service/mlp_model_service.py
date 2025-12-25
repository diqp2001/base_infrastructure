import os
import pickle
import random
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from typing import Dict, Any
import torch
from torch import nn, optim
from src.application.services.model_service.model_service import ModelService

class MLPModelService(ModelService):
    """Multi-Layer Perceptron (MLP) Model Service - advanced neural network service with financial trading capabilities."""
    
    def __init__(self):
        super().__init__()
        

    def _build_model(self, input_dim, output_dim, timesteps, cat_info=None, mult=0.3, hidden_layers=None) -> nn.Module:
        """
        Build the MLP model with configurable hidden layers.
        
        Args:
            input_dim: Number of input features
            output_dim: Number of output features
            timesteps: Number of timesteps in sequence
            cat_info: Categorical information (unused in this implementation)
            mult: Multiplier for default hidden dimension calculation
            hidden_layers: List of hidden layer sizes (e.g., [128, 64, 32])
        """
        class MLP(nn.Module):
            def __init__(self, input_dim, output_dim, timesteps, cat_info=None, mult=0.3, hidden_layers=None):
                super().__init__()
                
                self.timesteps = timesteps
                self.output_dim = output_dim
                
                # Calculate input size after flattening
                input_size = input_dim * timesteps
                
                # Use configured hidden layers or default calculation
                if hidden_layers is not None and len(hidden_layers) > 0:
                    # Use configured hidden layers
                    layers = []
                    prev_size = input_size
                    
                    # Add hidden layers
                    for i, hidden_size in enumerate(hidden_layers):
                        layers.append(nn.Linear(prev_size, hidden_size))
                        if i < len(hidden_layers) - 1:  # Don't add activation after last hidden layer
                            layers.append(nn.LayerNorm(hidden_size))  # Use LayerNorm instead of BatchNorm1d
                            layers.append(nn.ReLU())
                        prev_size = hidden_size
                    
                    # Final output layer
                    layers.append(nn.Linear(prev_size, output_dim * timesteps))
                    
                    self.network = nn.Sequential(*layers)
                else:
                    # Use original simple architecture
                    hidden_dim = int(input_size * mult)
                    self.network = nn.Sequential(
                        nn.Linear(input_size, hidden_dim),
                        nn.LayerNorm(hidden_dim),  # Use LayerNorm instead of BatchNorm1d
                        nn.Tanh(),
                        nn.Linear(hidden_dim, output_dim * timesteps)
                    )

            def forward(self, x):
                # Flatten the input tensor: [batch_size, timesteps, features] -> [batch_size, timesteps * features]
                x = x.flatten(start_dim=1)
                
                # Pass through network
                out = self.network(x)
                
                # Reshape to [batch_size, timesteps, output_dim]
                out = out.view(out.shape[0], self.timesteps, self.output_dim)
                out = torch.tanh(out)
                return out

        return MLP(input_dim, output_dim, timesteps, cat_info, mult, hidden_layers)

    def train_univariate(self, splitter, start, val_delta, test_delta, seed, hidden_layers=None, **kwargs):
        """
        Advanced training method for univariate time series prediction with financial metrics.
        
        Args:
            splitter: Data splitter service
            start: Start date for training
            val_delta: Validation delta period
            test_delta: Test delta period
            seed: Random seed for reproducibility
            hidden_layers: Number of hidden layers (optional, uses default if None)
            **kwargs: Additional keyword arguments
        """
        val_delta = pd.Timedelta('365days')
        test_delta = pd.Timedelta('365days')
        
        apply_turnover_reg = False
        apply_l1_reg = False
        weight_decay = 1e-5
        lr = 1e-3
        decay_steps = 10
        decay_gamma = 0.75
        early_stopping_rounds = 10
        n_epochs = 2
        device = 'cpu'
        target_vol = 0.15 #measure for turnover evaluation
        basis_points = [0, 1, 5, 10] #coefficients for turnover evaluation
        model_type = 'mlp'
        
        # Use hidden_layers parameter if provided, otherwise use default configuration
        if hidden_layers is not None:
            # Custom hidden layer configuration could be implemented here
            print(f"📊 Using custom hidden layers configuration: {hidden_layers}")
        
        if model_type == 'tft':
            history_size = 63
            encoder_length = 42 # in case of tft encoder length should be int
            model_params = {'device': 'cpu'}
            use_asset_info_as_feature = True # use asset name as categorical variable
        else:
            history_size = 21
            encoder_length = None # in case of non tft model encoder length should be None
            model_params = {}
            use_asset_info_as_feature = False
        test_dts = []
        train_loader, val_loader, test_loader, test_dt, cat_info = splitter.split(start, val_delta, test_delta, seed)

        test_dts.append(test_dt)
        if len(test_loader) == 0:
            breakpoint
        
        dt = start

        batch_data = next(iter(train_loader))
        if model_type != 'tft':
            # Handle case where batch_data only contains 2 tensors: features and targets
            if len(batch_data) == 2:
                batch_x, batch_y = batch_data
            else:
                # Handle case with 4 values (includes mask and volatility)
                batch_x, batch_y, _, _ = batch_data
        else:
            batch_x, _, _, _, _, _, batch_y, _, _ = batch_data
        
        input_dim = batch_x.shape[2]
        output_dim = 1
        timesteps = history_size
        
        # fix weights initialization for reproducibility
        self._set_seed(seed)
        model = self._build_model(input_dim, output_dim, timesteps=history_size, cat_info=cat_info, hidden_layers=hidden_layers).to(device)
        
        opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
        sc = torch.optim.lr_scheduler.StepLR(opt, decay_steps, decay_gamma)

        counter = 0
        
        train_losses = []
        train_l1_losses = []
        train_turnover_losses = []
        val_losses = []
        val_turnover_losses = []
        best_val_sharpe = -100
        
        for e in range(n_epochs):
            train_loss = 0
            train_l1_loss = 0
            train_turnover_loss = 0
            model.train()
            for batch_data in train_loader:
                # unpack batches
                for i in range(len(batch_data)):
                    batch_data[i] = batch_data[i].to(device)
                
                if model_type != 'tft':
                    # Handle case where batch_data only contains 2 tensors: features and targets
                    if len(batch_data) == 2:
                        batch_x, batch_y = batch_data
                        batch_mask, batch_vol = None, None
                    else:
                        # Handle case with 4 values (includes mask and volatility)
                        batch_x, batch_y, batch_mask, batch_vol = batch_data
                    input_data = [batch_x]
                else:
                    batch_x_enc_real, batch_x_enc_cat, batch_x_dec_real, batch_x_dec_cat, \
                    batch_enc_len, batch_dec_len, batch_y, batch_mask, batch_vol = batch_data
                    input_data = [batch_x_enc_real, batch_x_enc_cat, batch_x_dec_real, batch_x_dec_cat, \
                                  batch_enc_len, batch_dec_len]
                
                # train step
                opt.zero_grad()

                output = model(*input_data)
                
                # mask is used to avoid overlapping of data of different assets in single batch
                l = sharpe_loss(output, batch_y, mask=batch_mask)
                train_loss += l.item()
                
                # optionally apply regularization
                if apply_turnover_reg and batch_vol is not None:
                    l_turnover = reg_turnover(output, batch_vol, batch_mask)
                    train_turnover_loss += l_turnover.item()
                    l += l_turnover
                
                l.backward()
                opt.step()

            
            # we do not want learning rate to be too small
            if sc.get_last_lr()[0] > 1e-5:
                sc.step()
            
            val_loss = 0
            val_turnover_loss = 0
            
            preds, returns, vols = [], [], []
            
            model.eval()
            # evaluate model performance on validation dataset
            # for evaluation we do not need assets data to be stacked into single large dataset as it is done for training
            # so data for each asset come separate
            with torch.no_grad():
                for batch_data in val_loader:
                    # unpack batches
                    for i in range(len(batch_data)):
                        batch_data[i] = batch_data[i].to(device)

                    if model_type != 'tft':
                        # Handle case where batch_data only contains 2 tensors: features and targets
                        if len(batch_data) == 2:
                            batch_x, batch_y = batch_data
                            batch_vol = None
                        else:
                            # Handle case with 3+ values (includes volatility)
                            batch_x, batch_y, batch_vol = batch_data
                    else:
                        batch_x_enc_real, batch_x_enc_cat, batch_x_dec_real, batch_x_dec_cat, \
                        batch_enc_len, batch_dec_len, batch_y, batch_vol = batch_data

                    if model_type != 'tft':
                        input_data = batch_x
                    else:                                     
                        input_data = [batch_x_enc_real, batch_x_enc_cat, batch_x_dec_real,
                                      batch_x_dec_cat, batch_enc_len, batch_dec_len]

                    output = model(input_data) if model_type != 'tft' else model(*input_data)
                    
                    l = sharpe_loss(output, batch_y)
                    val_loss += l.item()

                    if apply_turnover_reg and batch_vol is not None:
                        l_turnover = reg_turnover(output, batch_vol)
                        val_turnover_loss += l_turnover.item()

                    # select last timestep as we no longer need for time axis in batch, collect data
                    preds_ = output[:, -1, :].detach().cpu().numpy()
                    returns_ = batch_y[:, -1, :].detach().cpu().numpy()
                    if batch_vol is not None:
                        vols_ = batch_vol[:, -1, :].detach().cpu().numpy()
                    else:
                        # Create dummy volatility if not available
                        vols_ = np.ones_like(output[:, -1, :].detach().cpu().numpy()) * 0.2
                    
                    # data is already in the correct format, no need to concatenate
                    
                    preds.append(preds_)
                    returns.append(returns_)
                    vols.append(vols_)
            
            # concatenate asset data
            preds = np.concatenate(preds)
            returns = np.concatenate(returns)
            vols = np.concatenate(vols)
            
            #annualized volatility
            vols = vols * 252**0.5
            # validation turnover
            T = target_vol*np.abs(np.diff(preds/(vols+1e-12), prepend=0.0, axis=0))
            # validation sharpe ratios with different turnover strength
            val_sharpes = {}
            
            # calculate Sharpe Ratio given different turnover strength
            for c in basis_points:
                captured = returns*preds - 1e-4*c*T
                R = np.mean(captured, axis=1)
                sharpes = sharpe_ratio(R)
                sharpes = np.mean(sharpes)
                val_sharpes[c] = sharpes
                
            # one can use sharpe ratio averaged by all turnover coefficients as validation performance metric
            #val_sharpe = np.mean(list(val_sharpes.values()))
            
            #select "pure" Sharpe Ratio as current epoch metric
            val_sharpe = val_sharpes[0]
            
            # if current metric is best, save model weights
            if best_val_sharpe < val_sharpe and e > 0:
                best_val_sharpe = val_sharpe
                counter = 0
                torch.save(model.state_dict(), os.path.join('weights', '{}_seed_{}_uni.pt'.format(model_type, seed)))
            
            else:
                counter += 1
            
            # if metric value didn't improve for several epochs, stop training
            if counter > early_stopping_rounds:
                break
            
            # aggregate losses and metrics, print current epoch training state
            train_loss /= len(train_loader)
            train_l1_loss/= len(train_loader)
            train_turnover_loss /= len(train_loader)
            val_loss /= len(val_loader)
            val_turnover_loss /= len(val_loader)
            
            train_losses.append(train_loss)
            train_l1_losses.append(train_l1_loss)
            train_turnover_losses.append(train_turnover_loss)
            val_losses.append(val_loss)
            val_turnover_losses.append(val_turnover_loss)
            
            print('Iter: ', e)
            print('Train loss: ', round(train_losses[-1], 3))
            print('Val loss: ', round(val_losses[-1], 3))
            print('Validation Sharpe Ratio')
            for key in val_sharpes.keys():
                print('C: ', key, 'SR: ', round(val_sharpes[key], 3))
            if apply_l1_reg:
                print('L1 loss', round(train_l1_losses[-1], 5))
            if apply_turnover_reg:
                print('Train turnover loss: ', round(train_turnover_losses[-1], 5))
                print('Val turnover loss: ', round(val_turnover_losses[-1], 5))
            print('Epochs till end: ', early_stopping_rounds - counter + 1)
            print()
        
        # plot losses evolution during training
        print('Validation dates: ', start, start+val_delta)
        
        '''plt.figure(figsize=(20, 10))
        plt.title('Loss evolution')
        #plt.plot(train_losses, label='train', marker='o')
        plt.plot(val_losses, label='validation', marker='o')
        plt.ylabel('Loss')
        plt.xlabel('Epochs')
        plt.legend()
        plt.show()
        
        if apply_l1_reg:
            plt.figure(figsize=(20, 10))
            plt.title('L1 regularization loss evolution')
            plt.plot(train_l1_losses, label='train', marker='o')
            plt.ylabel('L1 Loss')
            plt.xlabel('Epochs')
            plt.legend()
            plt.show()
        
        if apply_turnover_reg:
            plt.figure(figsize=(20, 10))
            plt.title('Turnover loss evolution')
            plt.plot(train_turnover_losses, label='train', marker='o')
            plt.plot(val_turnover_losses, label='validation', marker='o')
            plt.ylabel('Turnover loss')
            plt.xlabel('Epochs')
            plt.legend()
            plt.show()'''
        
        # load best checkpoint in terms of sharpe ratio on validation dataset
        model.load_state_dict(torch.load(os.path.join('weights', '{}_seed_{}_uni.pt'.format(model_type, seed))))
        model = model.to(device)
        model.eval()
        
        val_preds = []
        val_returns = []
        val_vols = []

        model.eval()
        # calculate model predictions on validation and test datasets
        with torch.no_grad():
            for batch_data in val_loader:
                
                for i in range(len(batch_data)):
                    batch_data[i] = batch_data[i].to(device)

                if model_type != 'tft':
                    # Handle case where batch_data only contains 2 tensors: features and targets
                    if len(batch_data) == 2:
                        batch_x, batch_y = batch_data
                        batch_vol = None
                    else:
                        # Handle case with 3+ values (includes volatility)
                        batch_x, batch_y, batch_vol = batch_data
                else:
                    batch_x_enc_real, batch_x_enc_cat, batch_x_dec_real, batch_x_dec_cat, \
                    batch_enc_len, batch_dec_len, batch_y, batch_vol = batch_data

                if model_type != 'tft':
                    input_data = batch_x
                else:                                     
                    input_data = [batch_x_enc_real, batch_x_enc_cat, batch_x_dec_real,
                                  batch_x_dec_cat, batch_enc_len, batch_dec_len]

                output = model(input_data) if model_type != 'tft' else model(*input_data)

                preds_ = output[:, -1, :].detach().cpu().numpy()
                returns_ = batch_y[:, -1, :].detach().cpu().numpy()
                if batch_vol is not None:
                    vols_ = batch_vol[:, -1, :].detach().cpu().numpy()
                else:
                    # Create dummy volatility if not available
                    vols_ = np.ones_like(output[:, -1, :].detach().cpu().numpy()) * 0.2

                val_preds.append(preds_)
                val_returns.append(returns_)
                val_vols.append(vols_)


        val_preds = np.concatenate(val_preds)
        val_returns = np.concatenate(val_returns)
        val_vols = np.concatenate(val_vols)
        
        test_preds = []
        test_returns = []
        test_vols = []

        with torch.no_grad():
            for batch_data in test_loader:
                
                for i in range(len(batch_data)):
                    batch_data[i] = batch_data[i].to(device)

                if model_type != 'tft':
                    # Handle case where batch_data only contains 2 tensors: features and targets
                    if len(batch_data) == 2:
                        batch_x, batch_y = batch_data
                        batch_vol = None
                    else:
                        # Handle case with 3+ values (includes volatility)
                        batch_x, batch_y, batch_vol = batch_data
                else:
                    batch_x_enc_real, batch_x_enc_cat, batch_x_dec_real, batch_x_dec_cat, \
                    batch_enc_len, batch_dec_len, batch_y, batch_vol = batch_data

                if model_type != 'tft':
                    input_data = batch_x
                else:                                     
                    input_data = [batch_x_enc_real, batch_x_enc_cat, batch_x_dec_real,
                                  batch_x_dec_cat, batch_enc_len, batch_dec_len]

                output = model(input_data) if model_type != 'tft' else model(*input_data)
                
                preds_.append(output[:, -1, :].detach().cpu().numpy())
                returns_.append(batch_y[:, -1, :].detach().cpu().numpy())
                if batch_vol is not None:
                    vols_.append(batch_vol[:, -1, :].detach().cpu().numpy())
                else:
                    # Create dummy volatility if not available
                    vols_.append(np.ones_like(output[:, -1, :].detach().cpu().numpy()) * 0.2)
                
                preds_ = np.concatenate(preds_, axis=-1) if len(preds_) > 1 else preds_[0]
                returns_ = np.concatenate(returns_, axis=-1) if len(returns_) > 1 else returns_[0]
                vols_ = np.concatenate(vols_, axis=-1) if len(vols_) > 1 else vols_[0]

                test_preds.append(preds_)
                test_returns.append(returns_)
                test_vols.append(vols_)


        test_preds = np.concatenate(test_preds)
        test_returns = np.concatenate(test_returns)
        test_vols = np.concatenate(test_vols)

        # Return the expected 7 values for compatibility with calling code
        return test_dt, val_preds, val_returns, val_vols, test_preds, test_returns, test_vols





    def _set_seed(self,seed):
        """
        Set random seed for reproducibility across multiple libraries.
        """
        np.random.seed(seed)
        random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed(seed)
        # When running on the CuDNN backend, two further options must be set
        #torch.backends.cudnn.deterministic = True
        #torch.backends.cudnn.benchmark = False
        # Set a fixed value for the hash seed
        os.environ["PYTHONHASHSEED"] = str(seed)
        print(f"Random seed set as {seed}")

    def train_model(self, features: pd.DataFrame, target: pd.Series, epochs: int = 10, lr: float = 0.001) -> None:
        """
        Train the MLP model using classic approach.
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

    def evaluate_model(self, test_data: pd.DataFrame) -> Dict[str, float]:
        """
        Evaluate the MLP model using classic approach.
        """
        X_test = torch.tensor(test_data.drop(columns=[self.target_column]).values, dtype=torch.float32)
        y_test = torch.tensor(test_data[self.target_column].values, dtype=torch.float32).view(-1, 1)
        y_pred = self.model(X_test)
        mse = nn.MSELoss()(y_pred, y_test).item()
        return {"MSE": mse}
    
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
    # Handle tensor dimension mismatch by ensuring compatible shapes
    # preds: [batch_size, timesteps, 1] or [batch_size, timesteps, output_dim]  
    # returns: can be [batch_size, features] or [batch_size, timesteps, features]
    
    # Handle different dimensions for returns tensor
    if len(returns.shape) == 2:
        # returns is [batch_size, features], need to expand to match preds timesteps
        if len(preds.shape) == 3:
            # Expand returns to [batch_size, timesteps, features] 
            returns = returns.unsqueeze(1).expand(-1, preds.shape[1], -1)
        else:
            # Both are 2D, ensure they have same shape
            if returns.shape != preds.shape:
                # If shapes don't match, expand the smaller one or reshape
                if returns.shape[1] == 1 and preds.shape[1] > 1:
                    returns = returns.expand(-1, preds.shape[1])
                elif preds.shape[1] == 1 and returns.shape[1] > 1:
                    preds = preds.expand(-1, returns.shape[1])
    
    # Now both tensors should be 3D, handle timestep alignment
    if len(preds.shape) == 3 and len(returns.shape) == 3:
        # Both are 3D - handle timestep dimension differences
        if preds.shape[1] != returns.shape[1]:
            min_timesteps = min(preds.shape[1], returns.shape[1])
            preds = preds[:, :min_timesteps, :]
            returns = returns[:, :min_timesteps, :]
        
        # Handle feature dimension differences  
        if preds.shape[2] == 1 and returns.shape[2] > 1:
            # Expand preds to match returns' last dimension
            preds = preds.expand(-1, -1, returns.shape[2])
        elif preds.shape[2] > 1 and returns.shape[2] == 1:
            # Expand returns to match preds' last dimension
            returns = returns.expand(-1, -1, preds.shape[2])
        elif preds.shape[2] != returns.shape[2]:
            # If dimensions don't match and neither is 1, take the mean
            if preds.shape[2] > returns.shape[2]:
                preds = torch.mean(preds, dim=2, keepdim=True)
                preds = preds.expand(-1, -1, returns.shape[2])
            else:
                returns = torch.mean(returns, dim=2, keepdim=True) 
                returns = returns.expand(-1, -1, preds.shape[2])
    
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