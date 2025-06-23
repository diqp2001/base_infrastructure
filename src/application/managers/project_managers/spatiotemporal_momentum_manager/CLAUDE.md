# CLAUDE.md – Spatiotemporal Momentum Manager

This manager coordinates the workflow for a **spatiotemporal momentum model**, typically used in financial ML.

## Context
The model:
- Uses multiple securities and factors over time
- Predicts return direction or momentum class
- Is trained with time series inputs and spatiotemporal dependencies

## Responsibilities
- Format time series data for model input
- Manage model lifecycle (training, prediction)
- Interface with model repositories or storage

## Design Considerations
- Input shape often includes `[timesteps, features, assets]`
- Targets are multi-class (e.g., momentum quintiles)
- Ensure temporal integrity (no lookahead bias)

This manager should be the only access point for running the full spatiotemporal pipeline end-to-end.
