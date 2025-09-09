"""
Data reader implementations for various data sources and formats.
"""

import csv
import json
import zipfile
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, List, Optional, Dict, Any, Union
from decimal import Decimal

from ..common.interfaces import IDataReader
from ..common.data_types import BaseData, TradeBar, QuoteBar, Tick, SubscriptionDataConfig, Bar
from ..common.symbol import Symbol
from ..common.enums import Resolution, TickType, DataType
from ..common.time_utils import Time


class BaseDataReader(IDataReader):
    """
    Abstract base class for data readers.
    """
    
    def __init__(self):
        self._supported_resolutions = [Resolution.TICK, Resolution.SECOND, Resolution.MINUTE, 
                                     Resolution.HOUR, Resolution.DAILY]
        self._cache: Dict[str, List[BaseData]] = {}
    
    @abstractmethod
    def read_data(self, config: SubscriptionDataConfig, start_time: datetime, 
                 end_time: datetime) -> Iterator[BaseData]:
        """Read data for the given configuration and time range."""
        pass
    
    def read(self, config: SubscriptionDataConfig) -> List[BaseData]:
        """Read data based on subscription configuration."""
        # Default implementation reads all available data
        try:
            data_iterator = self.read_data(config, datetime.min, datetime.max)
            return list(data_iterator)
        except Exception as e:
            print(f"Error reading data for {config.symbol}: {e}")
            return []
    
    def supports_mapping(self) -> bool:
        """Returns true if this reader supports symbol mapping."""
        return False
    
    def supports_resolution(self, resolution: Resolution) -> bool:
        """Check if this reader supports the given resolution."""
        return resolution in self._supported_resolutions
    
    def _parse_datetime(self, date_str: str, format_str: str = "%Y%m%d %H:%M:%S") -> datetime:
        """Parse datetime string with error handling."""
        try:
            if isinstance(date_str, str):
                return datetime.strptime(date_str, format_str)
            elif isinstance(date_str, datetime):
                return date_str
            else:
                # Try to convert to string first
                return datetime.strptime(str(date_str), format_str)
        except ValueError as e:
            # Try alternative formats
            alternative_formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%Y%m%d",
                "%Y-%m-%d",
                "%Y/%m/%d"
            ]
            
            for fmt in alternative_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            raise ValueError(f"Unable to parse datetime: {date_str}")


class LeanDataReader(BaseDataReader):
    """
    Reader for QuantConnect Lean data format (compressed zip files).
    """
    
    def __init__(self, data_folder: str = "data"):
        super().__init__()
        self.data_folder = Path(data_folder)
    
    def read_data(self, config: SubscriptionDataConfig, start_time: datetime, 
                 end_time: datetime) -> Iterator[BaseData]:
        """Read Lean format data."""
        data_files = self._get_data_files(config)
        
        for file_path in data_files:
            try:
                yield from self._read_file(file_path, config, start_time, end_time)
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                continue
    
    def _get_data_files(self, config: SubscriptionDataConfig) -> List[Path]:
        """Get list of data files for the given configuration."""
        symbol_folder = self._get_symbol_folder(config)
        
        if not symbol_folder.exists():
            return []
        
        # Look for zip files
        zip_files = list(symbol_folder.glob("*.zip"))
        zip_files.sort()  # Sort by filename for chronological order
        
        return zip_files
    
    def _get_symbol_folder(self, config: SubscriptionDataConfig) -> Path:
        """Get the folder path for a symbol's data."""
        return (self.data_folder / 
                config.symbol.security_type.value / 
                config.market / 
                config.resolution.value / 
                config.symbol.value.lower())
    
    def _read_file(self, file_path: Path, config: SubscriptionDataConfig, 
                  start_time: datetime, end_time: datetime) -> Iterator[BaseData]:
        """Read a single Lean data file."""
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Get the first file in the zip (should be the data file)
                file_names = zip_file.namelist()
                if not file_names:
                    return
                
                data_file_name = file_names[0]
                with zip_file.open(data_file_name) as data_file:
                    content = data_file.read().decode('utf-8')
                    
                    for line in content.strip().split('\n'):
                        if not line.strip():
                            continue
                        
                        try:
                            data_point = self._parse_lean_line(line, config)
                            if data_point and start_time <= data_point.time <= end_time:
                                yield data_point
                        except Exception as e:
                            print(f"Error parsing line '{line}': {e}")
                            continue
                            
        except Exception as e:
            print(f"Error reading zip file {file_path}: {e}")
    
    def _parse_lean_line(self, line: str, config: SubscriptionDataConfig) -> Optional[BaseData]:
        """Parse a line from Lean data format."""
        parts = line.split(',')
        
        if len(parts) < 2:
            return None
        
        try:
            # First field is usually timestamp (milliseconds since epoch)
            timestamp_ms = int(parts[0])
            time = datetime.utcfromtimestamp(timestamp_ms / 1000.0)
            
            if config.data_type == TradeBar:
                return self._parse_trade_bar(parts, config.symbol, time)
            elif config.data_type == QuoteBar:
                return self._parse_quote_bar(parts, config.symbol, time)
            elif config.data_type == Tick:
                return self._parse_tick(parts, config.symbol, time)
            else:
                # Generic BaseData
                value = Decimal(parts[1]) if len(parts) > 1 else Decimal('0')
                return BaseData(
                    symbol=config.symbol,
                    time=time,
                    value=value,
                    data_type=DataType.TRADE_BAR
                )
                
        except (ValueError, IndexError) as e:
            print(f"Error parsing Lean data line: {e}")
            return None
    
    def _parse_trade_bar(self, parts: List[str], symbol: Symbol, time: datetime) -> TradeBar:
        """Parse TradeBar from Lean format."""
        # Lean TradeBar format: timestamp,open,high,low,close,volume
        if len(parts) < 6:
            raise ValueError(f"Invalid TradeBar format, expected 6 fields, got {len(parts)}")
        
        return TradeBar(
            symbol=symbol,
            time=time,
            value=Decimal(parts[4]),  # Close price
            data_type=DataType.TRADE_BAR,
            open=Decimal(parts[1]),
            high=Decimal(parts[2]),
            low=Decimal(parts[3]),
            close=Decimal(parts[4]),
            volume=int(parts[5])
        )
    
    def _parse_quote_bar(self, parts: List[str], symbol: Symbol, time: datetime) -> QuoteBar:
        """Parse QuoteBar from Lean format."""
        # Lean QuoteBar format: timestamp,bid_open,bid_high,bid_low,bid_close,bid_size,ask_open,ask_high,ask_low,ask_close,ask_size
        if len(parts) < 11:
            raise ValueError(f"Invalid QuoteBar format, expected 11 fields, got {len(parts)}")
        
        bid = Bar(
            open=Decimal(parts[1]),
            high=Decimal(parts[2]),
            low=Decimal(parts[3]),
            close=Decimal(parts[4])
        )
        
        ask = Bar(
            open=Decimal(parts[6]),
            high=Decimal(parts[7]),
            low=Decimal(parts[8]),
            close=Decimal(parts[9])
        )
        
        return QuoteBar(
            symbol=symbol,
            time=time,
            value=(bid.close + ask.close) / 2,
            data_type=DataType.QUOTE_BAR,
            bid=bid,
            ask=ask,
            last_bid_size=int(parts[5]),
            last_ask_size=int(parts[10])
        )
    
    def _parse_tick(self, parts: List[str], symbol: Symbol, time: datetime) -> Tick:
        """Parse Tick from Lean format."""
        # Lean Tick format: timestamp,value,tick_type,quantity,exchange,sale_condition
        if len(parts) < 3:
            raise ValueError(f"Invalid Tick format, expected at least 3 fields, got {len(parts)}")
        
        # Determine tick type
        tick_type = TickType.TRADE  # Default
        if len(parts) > 2:
            tick_type_str = parts[2].lower()
            if 'quote' in tick_type_str:
                tick_type = TickType.QUOTE
        
        return Tick(
            symbol=symbol,
            time=time,
            value=Decimal(parts[1]),
            data_type=DataType.TICK,
            tick_type=tick_type,
            quantity=int(parts[3]) if len(parts) > 3 else 0,
            exchange=parts[4] if len(parts) > 4 else "",
            sale_condition=parts[5] if len(parts) > 5 else ""
        )


class CsvDataReader(BaseDataReader):
    """
    Reader for CSV data files.
    """
    
    def __init__(self, data_folder: str = "data"):
        super().__init__()
        self.data_folder = Path(data_folder)
        self.default_columns = {
            'timestamp': ['timestamp', 'time', 'date', 'datetime'],
            'open': ['open', 'o'],
            'high': ['high', 'h'],
            'low': ['low', 'l'],
            'close': ['close', 'c', 'price'],
            'volume': ['volume', 'vol', 'v']
        }
    
    def read_data(self, config: SubscriptionDataConfig, start_time: datetime, 
                 end_time: datetime) -> Iterator[BaseData]:
        """Read CSV format data."""
        csv_files = self._get_csv_files(config)
        
        for file_path in csv_files:
            try:
                yield from self._read_csv_file(file_path, config, start_time, end_time)
            except Exception as e:
                print(f"Error reading CSV file {file_path}: {e}")
                continue
    
    def _get_csv_files(self, config: SubscriptionDataConfig) -> List[Path]:
        """Get list of CSV files for the given configuration."""
        symbol_folder = self._get_symbol_folder(config)
        
        if not symbol_folder.exists():
            return []
        
        # Look for CSV files
        csv_files = list(symbol_folder.glob("*.csv"))
        csv_files.sort()
        
        return csv_files
    
    def _get_symbol_folder(self, config: SubscriptionDataConfig) -> Path:
        """Get folder path for symbol data."""
        return (self.data_folder / 
                config.symbol.security_type.value / 
                config.market / 
                config.resolution.value / 
                config.symbol.value.lower())
    
    def _read_csv_file(self, file_path: Path, config: SubscriptionDataConfig, 
                      start_time: datetime, end_time: datetime) -> Iterator[BaseData]:
        """Read a single CSV file."""
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                # Detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
                reader = csv.DictReader(csvfile, dialect=dialect)
                
                # Map column names
                column_mapping = self._detect_column_mapping(reader.fieldnames or [])
                
                for row in reader:
                    try:
                        data_point = self._parse_csv_row(row, column_mapping, config)
                        if data_point and start_time <= data_point.time <= end_time:
                            yield data_point
                    except Exception as e:
                        print(f"Error parsing CSV row: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error reading CSV file {file_path}: {e}")
    
    def _detect_column_mapping(self, fieldnames: List[str]) -> Dict[str, str]:
        """Detect column mapping from CSV headers."""
        mapping = {}
        fieldnames_lower = [name.lower() for name in fieldnames]
        
        for key, possible_names in self.default_columns.items():
            for possible_name in possible_names:
                if possible_name in fieldnames_lower:
                    # Find the original case fieldname
                    original_name = fieldnames[fieldnames_lower.index(possible_name)]
                    mapping[key] = original_name
                    break
        
        return mapping
    
    def _parse_csv_row(self, row: Dict[str, str], column_mapping: Dict[str, str], 
                      config: SubscriptionDataConfig) -> Optional[BaseData]:
        """Parse a CSV row into BaseData."""
        if 'timestamp' not in column_mapping:
            return None
        
        try:
            # Parse timestamp
            timestamp_str = row[column_mapping['timestamp']]
            time = self._parse_datetime(timestamp_str)
            
            if config.data_type == TradeBar:
                return self._parse_csv_trade_bar(row, column_mapping, config.symbol, time)
            else:
                # Default to simple BaseData with close price
                price_col = column_mapping.get('close', column_mapping.get('price'))
                if price_col and price_col in row:
                    price = Decimal(row[price_col])
                else:
                    price = Decimal('0')
                
                return BaseData(
                    symbol=config.symbol,
                    time=time,
                    value=price,
                    data_type=DataType.TRADE_BAR
                )
                
        except Exception as e:
            print(f"Error parsing CSV row: {e}")
            return None
    
    def _parse_csv_trade_bar(self, row: Dict[str, str], column_mapping: Dict[str, str], 
                           symbol: Symbol, time: datetime) -> Optional[TradeBar]:
        """Parse CSV row as TradeBar."""
        try:
            # Extract OHLCV data
            open_val = Decimal(row[column_mapping['open']]) if 'open' in column_mapping else Decimal('0')
            high_val = Decimal(row[column_mapping['high']]) if 'high' in column_mapping else open_val
            low_val = Decimal(row[column_mapping['low']]) if 'low' in column_mapping else open_val
            close_val = Decimal(row[column_mapping['close']]) if 'close' in column_mapping else open_val
            volume_val = int(float(row[column_mapping['volume']])) if 'volume' in column_mapping else 0
            
            return TradeBar(
                symbol=symbol,
                time=time,
                value=close_val,
                data_type=DataType.TRADE_BAR,
                open=open_val,
                high=high_val,
                low=low_val,
                close=close_val,
                volume=volume_val
            )
            
        except (KeyError, ValueError, TypeError) as e:
            print(f"Error parsing TradeBar from CSV: {e}")
            return None


class AlphaStreamsDataReader(BaseDataReader):
    """
    Reader for Alpha Streams data format.
    """
    
    def __init__(self, data_folder: str = "data"):
        super().__init__()
        self.data_folder = Path(data_folder)
    
    def read_data(self, config: SubscriptionDataConfig, start_time: datetime, 
                 end_time: datetime) -> Iterator[BaseData]:
        """Read Alpha Streams format data."""
        # Alpha Streams typically uses JSON format
        json_files = self._get_json_files(config)
        
        for file_path in json_files:
            try:
                yield from self._read_json_file(file_path, config, start_time, end_time)
            except Exception as e:
                print(f"Error reading Alpha Streams file {file_path}: {e}")
                continue
    
    def _get_json_files(self, config: SubscriptionDataConfig) -> List[Path]:
        """Get JSON files for the configuration."""
        symbol_folder = self._get_symbol_folder(config)
        
        if not symbol_folder.exists():
            return []
        
        json_files = list(symbol_folder.glob("*.json"))
        json_files.sort()
        
        return json_files
    
    def _get_symbol_folder(self, config: SubscriptionDataConfig) -> Path:
        """Get folder path for symbol data."""
        return (self.data_folder / 
                "alpha_streams" /
                config.symbol.security_type.value / 
                config.symbol.value.lower())
    
    def _read_json_file(self, file_path: Path, config: SubscriptionDataConfig, 
                       start_time: datetime, end_time: datetime) -> Iterator[BaseData]:
        """Read a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                
                # Handle different JSON structures
                if isinstance(data, list):
                    # Array of data points
                    for item in data:
                        data_point = self._parse_json_item(item, config)
                        if data_point and start_time <= data_point.time <= end_time:
                            yield data_point
                elif isinstance(data, dict):
                    # Single data point or nested structure
                    if 'data' in data and isinstance(data['data'], list):
                        # Nested structure with data array
                        for item in data['data']:
                            data_point = self._parse_json_item(item, config)
                            if data_point and start_time <= data_point.time <= end_time:
                                yield data_point
                    else:
                        # Single data point
                        data_point = self._parse_json_item(data, config)
                        if data_point and start_time <= data_point.time <= end_time:
                            yield data_point
                            
        except Exception as e:
            print(f"Error reading JSON file {file_path}: {e}")
    
    def _parse_json_item(self, item: Dict[str, Any], config: SubscriptionDataConfig) -> Optional[BaseData]:
        """Parse a JSON item into BaseData."""
        try:
            # Extract timestamp
            timestamp = item.get('timestamp') or item.get('time') or item.get('date')
            if not timestamp:
                return None
            
            if isinstance(timestamp, (int, float)):
                # Unix timestamp
                time = datetime.utcfromtimestamp(timestamp)
            else:
                # String timestamp
                time = self._parse_datetime(str(timestamp))
            
            # Extract value
            value = item.get('value') or item.get('price') or item.get('close')
            if value is None:
                return None
            
            return BaseData(
                symbol=config.symbol,
                time=time,
                value=Decimal(str(value)),
                data_type=DataType.TRADE_BAR
            )
            
        except Exception as e:
            print(f"Error parsing JSON item: {e}")
            return None


class MemoryDataReader(BaseDataReader):
    """
    In-memory data reader for testing and custom data scenarios.
    """
    
    def __init__(self):
        super().__init__()
        self._data_store: Dict[str, List[BaseData]] = {}
    
    def add_data(self, symbol: Symbol, data: List[BaseData]):
        """Add data for a symbol."""
        key = f"{symbol}_{symbol.security_type.value}"
        self._data_store[key] = sorted(data, key=lambda x: x.time)
    
    def read_data(self, config: SubscriptionDataConfig, start_time: datetime, 
                 end_time: datetime) -> Iterator[BaseData]:
        """Read data from memory."""
        key = f"{config.symbol}_{config.symbol.security_type.value}"
        
        if key not in self._data_store:
            return
        
        data_list = self._data_store[key]
        
        for data_point in data_list:
            if start_time <= data_point.time <= end_time:
                # Filter by data type if specified
                if config.data_type and not isinstance(data_point, config.data_type):
                    continue
                
                yield data_point
    
    def clear_data(self, symbol: Symbol = None):
        """Clear data for a symbol or all data."""
        if symbol:
            key = f"{symbol}_{symbol.security_type.value}"
            if key in self._data_store:
                del self._data_store[key]
        else:
            self._data_store.clear()
    
    def get_data_count(self, symbol: Symbol) -> int:
        """Get the number of data points for a symbol."""
        key = f"{symbol}_{symbol.security_type.value}"
        return len(self._data_store.get(key, []))