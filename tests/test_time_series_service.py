import pytest
from unittest.mock import MagicMock
from src.application.services.time_series.time_series_service import TimeSeriesService
from src.domain.entities.time_series.time_series import TimeSeries

@pytest.fixture
def mock_repository():
    """Fixture to mock the repository methods."""
    mock_repo = MagicMock()
    return mock_repo

@pytest.fixture
def time_series_service(mock_repository):
    """Fixture to initialize the TimeSeriesService."""
    return TimeSeriesService(mock_repository)

def test_get_by_id(time_series_service, mock_repository):
    # Arrange
    mock_time_series = TimeSeries(id=1, dates=["2023-01-01"], values=[100.0])
    mock_repository.get_by_id.return_value = mock_time_series

    # Act
    result = time_series_service.get_by_id(1)

    # Assert
    assert result == mock_time_series
    mock_repository.get_by_id.assert_called_once_with(1)

def test_save(time_series_service, mock_repository):
    # Arrange
    mock_time_series = TimeSeries(id=1, dates=["2023-01-01"], values=[100.0])

    # Act
    time_series_service.save(mock_time_series)

    # Assert
    mock_repository.save.assert_called_once_with(mock_time_series)

def test_get_all(time_series_service, mock_repository):
    # Arrange
    mock_time_series_list = [
        TimeSeries(id=1, dates=["2023-01-01"], values=[100.0]),
        TimeSeries(id=2, dates=["2023-01-02"], values=[200.0]),
    ]
    mock_repository.get_all.return_value = mock_time_series_list

    # Act
    result = time_series_service.get_all()

    # Assert
    assert result == mock_time_series_list
    mock_repository.get_all.assert_called_once()
