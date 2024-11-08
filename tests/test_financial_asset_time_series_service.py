import pytest
from unittest.mock import MagicMock
from src.application.services.time_series.financial_asset_time_series_service import FinancialAssetTimeSeriesService
from src.domain.entities.time_series.financial_asset_time_series import FinancialAssetTimeSeries

@pytest.fixture
def mock_repository():
    """Fixture to mock the FinancialAssetTimeSeriesRepository methods."""
    mock_repo = MagicMock()
    return mock_repo

@pytest.fixture
def financial_asset_time_series_service(mock_repository):
    """Fixture to initialize the FinancialAssetTimeSeriesService."""
    return FinancialAssetTimeSeriesService(mock_repository)

def test_get_by_id(financial_asset_time_series_service, mock_repository):
    # Arrange
    mock_time_series = FinancialAssetTimeSeries(id=1, asset_id=101, dates=["2023-01-01"], values=[100.0])
    mock_repository.get_by_id.return_value = mock_time_series

    # Act
    result = financial_asset_time_series_service.get_by_id(1)

    # Assert
    assert result == mock_time_series
    mock_repository.get_by_id.assert_called_once_with(1)

def test_save(financial_asset_time_series_service, mock_repository):
    # Arrange
    mock_time_series = FinancialAssetTimeSeries(id=1, asset_id=101, dates=["2023-01-01"], values=[100.0])

    # Act
    financial_asset_time_series_service.save(mock_time_series)

    # Assert
    mock_repository.save.assert_called_once_with(mock_time_series)

def test_get_by_asset_id(financial_asset_time_series_service, mock_repository):
    # Arrange
    mock_time_series_list = [
        FinancialAssetTimeSeries(id=1, asset_id=101, dates=["2023-01-01"], values=[100.0]),
        FinancialAssetTimeSeries(id=2, asset_id=101, dates=["2023-01-02"], values=[200.0]),
    ]
    mock_repository.get_by_asset_id.return_value = mock_time_series_list

    # Act
    result = financial_asset_time_series_service.get_by_asset_id(101)

    # Assert
    assert result == mock_time_series_list
    mock_repository.get_by_asset_id.assert_called_once_with(101)
