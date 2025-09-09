"""
File format utilities for data storage and retrieval.
"""

import json
import csv
import gzip
import zipfile
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime
from decimal import Decimal

from ..common.data_types import BaseData, TradeBar, QuoteBar, Tick
from ..common.symbol import Symbol
from ..common.enums import Resolution, TickType, DataType


class FileFormat(Enum):
    """Supported file formats for data storage."""
    CSV = "csv"
    JSON = "json"
    LEAN_ZIP = "lean_zip"
    PARQUET = "parquet"
    BINARY = "binary"


class DataFileWriter:
    """
    Writer for various data file formats.
    """
    
    def __init__(self, file_format: FileFormat):
        self.format = file_format
    
    def write_data(self, file_path: Path, data: List[BaseData], 
                  compression: bool = False) -> bool:
        """
        Write data to file in the specified format.
        """
        try:
            if self.format == FileFormat.CSV:
                return self._write_csv(file_path, data, compression)
            elif self.format == FileFormat.JSON:
                return self._write_json(file_path, data, compression)
            elif self.format == FileFormat.LEAN_ZIP:
                return self._write_lean_zip(file_path, data)
            else:
                print(f"Unsupported write format: {self.format}")
                return False
                
        except Exception as e:
            print(f"Error writing data to {file_path}: {e}")
            return False
    
    def _write_csv(self, file_path: Path, data: List[BaseData], compression: bool) -> bool:
        """Write data to CSV format."""
        if not data:
            return False
        
        # Determine if we can use TradeBar format
        is_trade_bar = all(isinstance(d, TradeBar) for d in data)
        
        if compression:
            file_path = file_path.with_suffix(file_path.suffix + '.gz')
            open_func = lambda: gzip.open(file_path, 'wt', newline='', encoding='utf-8')
        else:
            open_func = lambda: open(file_path, 'w', newline='', encoding='utf-8')
        
        with open_func() as csvfile:
            if is_trade_bar:
                # TradeBar CSV format
                fieldnames = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for item in data:
                    if isinstance(item, TradeBar):
                        writer.writerow({
                            'timestamp': item.time.isoformat(),
                            'open': str(item.open),
                            'high': str(item.high),
                            'low': str(item.low),
                            'close': str(item.close),
                            'volume': item.volume
                        })
            else:
                # Generic format
                fieldnames = ['timestamp', 'symbol', 'value', 'data_type']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for item in data:
                    writer.writerow({
                        'timestamp': item.time.isoformat(),
                        'symbol': str(item.symbol),
                        'value': str(item.value),
                        'data_type': item.data_type.value if hasattr(item.data_type, 'value') else str(item.data_type)
                    })
        
        return True
    
    def _write_json(self, file_path: Path, data: List[BaseData], compression: bool) -> bool:
        """Write data to JSON format."""
        json_data = []
        
        for item in data:
            if isinstance(item, TradeBar):
                json_item = {
                    'timestamp': item.time.isoformat(),
                    'symbol': str(item.symbol),
                    'type': 'TradeBar',
                    'open': str(item.open),
                    'high': str(item.high),
                    'low': str(item.low),
                    'close': str(item.close),
                    'volume': item.volume
                }
            elif isinstance(item, Tick):
                json_item = {
                    'timestamp': item.time.isoformat(),
                    'symbol': str(item.symbol),
                    'type': 'Tick',
                    'value': str(item.value),
                    'tick_type': item.tick_type.value,
                    'quantity': item.quantity,
                    'exchange': item.exchange
                }
            else:
                json_item = {
                    'timestamp': item.time.isoformat(),
                    'symbol': str(item.symbol),
                    'type': 'BaseData',
                    'value': str(item.value)
                }
            
            json_data.append(json_item)
        
        if compression:
            file_path = file_path.with_suffix(file_path.suffix + '.gz')
            with gzip.open(file_path, 'wt', encoding='utf-8') as jsonfile:
                json.dump(json_data, jsonfile, indent=2)
        else:
            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(json_data, jsonfile, indent=2)
        
        return True
    
    def _write_lean_zip(self, file_path: Path, data: List[BaseData]) -> bool:
        """Write data to Lean ZIP format."""
        if not data:
            return False
        
        # Create CSV content in memory
        csv_content = ""
        
        for item in data:
            if isinstance(item, TradeBar):
                # Lean TradeBar format: timestamp_ms,open,high,low,close,volume
                timestamp_ms = int(item.time.timestamp() * 1000)
                csv_content += f"{timestamp_ms},{item.open},{item.high},{item.low},{item.close},{item.volume}\n"
            elif isinstance(item, Tick):
                # Lean Tick format: timestamp_ms,value,tick_type,quantity,exchange
                timestamp_ms = int(item.time.timestamp() * 1000)
                csv_content += f"{timestamp_ms},{item.value},{item.tick_type.value},{item.quantity},{item.exchange}\n"
            else:
                # Generic format
                timestamp_ms = int(item.time.timestamp() * 1000)
                csv_content += f"{timestamp_ms},{item.value}\n"
        
        # Write to ZIP file
        zip_file_path = file_path.with_suffix('.zip')
        data_file_name = file_path.stem + '.csv'
        
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(data_file_name, csv_content)
        
        return True


class DataFileReader:
    """
    Reader for various data file formats.
    """
    
    def __init__(self, file_format: FileFormat = None):
        self.format = file_format
    
    def read_data(self, file_path: Path, symbol: Symbol = None) -> Iterator[BaseData]:
        """
        Read data from file. Auto-detects format if not specified.
        """
        if self.format is None:
            self.format = self._detect_format(file_path)
        
        try:
            if self.format == FileFormat.CSV:
                yield from self._read_csv(file_path, symbol)
            elif self.format == FileFormat.JSON:
                yield from self._read_json(file_path, symbol)
            elif self.format == FileFormat.LEAN_ZIP:
                yield from self._read_lean_zip(file_path, symbol)
            else:
                print(f"Unsupported read format: {self.format}")
                
        except Exception as e:
            print(f"Error reading data from {file_path}: {e}")
    
    def _detect_format(self, file_path: Path) -> FileFormat:
        """Auto-detect file format based on extension."""
        suffix = file_path.suffix.lower()
        
        if suffix == '.csv' or suffix == '.csv.gz':
            return FileFormat.CSV
        elif suffix == '.json' or suffix == '.json.gz':
            return FileFormat.JSON
        elif suffix == '.zip':
            return FileFormat.LEAN_ZIP
        else:
            # Default to CSV
            return FileFormat.CSV
    
    def _read_csv(self, file_path: Path, symbol: Symbol) -> Iterator[BaseData]:
        """Read CSV format data."""
        is_compressed = file_path.suffix.lower() == '.gz'
        
        if is_compressed:
            open_func = lambda: gzip.open(file_path, 'rt', encoding='utf-8')
        else:
            open_func = lambda: open(file_path, 'r', encoding='utf-8')
        
        with open_func() as csvfile:
            # Detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
            reader = csv.DictReader(csvfile, dialect=dialect)
            
            for row in reader:
                try:
                    data_point = self._parse_csv_row(row, symbol)
                    if data_point:
                        yield data_point
                except Exception as e:
                    print(f"Error parsing CSV row: {e}")
                    continue
    
    def _parse_csv_row(self, row: Dict[str, str], symbol: Symbol) -> Optional[BaseData]:
        """Parse a CSV row into BaseData."""
        timestamp_str = row.get('timestamp') or row.get('time') or row.get('date')
        if not timestamp_str:
            return None
        
        try:
            time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            # Try alternative parsing
            time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        
        # Check if this is OHLCV data
        if all(key in row for key in ['open', 'high', 'low', 'close']):
            return TradeBar(
                symbol=symbol,
                time=time,
                value=Decimal(row['close']),
                data_type=DataType.TRADE_BAR,
                open=Decimal(row['open']),
                high=Decimal(row['high']),
                low=Decimal(row['low']),
                close=Decimal(row['close']),
                volume=int(row.get('volume', 0))
            )
        else:
            # Simple price data
            value = Decimal(row.get('value') or row.get('price') or row.get('close'))
            return BaseData(
                symbol=symbol,
                time=time,
                value=value,
                data_type=DataType.TRADE_BAR
            )
    
    def _read_json(self, file_path: Path, symbol: Symbol) -> Iterator[BaseData]:
        """Read JSON format data."""
        is_compressed = file_path.suffix.lower() == '.gz'
        
        if is_compressed:
            with gzip.open(file_path, 'rt', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
        else:
            with open(file_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
        
        if isinstance(data, list):
            for item in data:
                data_point = self._parse_json_item(item, symbol)
                if data_point:
                    yield data_point
        elif isinstance(data, dict):
            data_point = self._parse_json_item(data, symbol)
            if data_point:
                yield data_point
    
    def _parse_json_item(self, item: Dict[str, Any], symbol: Symbol) -> Optional[BaseData]:
        """Parse a JSON item into BaseData."""
        try:
            timestamp_str = item.get('timestamp') or item.get('time')
            if not timestamp_str:
                return None
            
            time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            item_type = item.get('type', 'BaseData')
            
            if item_type == 'TradeBar':
                return TradeBar(
                    symbol=symbol,
                    time=time,
                    value=Decimal(item['close']),
                    data_type=DataType.TRADE_BAR,
                    open=Decimal(item['open']),
                    high=Decimal(item['high']),
                    low=Decimal(item['low']),
                    close=Decimal(item['close']),
                    volume=int(item.get('volume', 0))
                )
            elif item_type == 'Tick':
                return Tick(
                    symbol=symbol,
                    time=time,
                    value=Decimal(item['value']),
                    data_type=DataType.TICK,
                    tick_type=TickType(item.get('tick_type', 'trade')),
                    quantity=int(item.get('quantity', 0)),
                    exchange=item.get('exchange', '')
                )
            else:
                value = Decimal(item.get('value') or item.get('price'))
                return BaseData(
                    symbol=symbol,
                    time=time,
                    value=value,
                    data_type=DataType.TRADE_BAR
                )
                
        except Exception as e:
            print(f"Error parsing JSON item: {e}")
            return None
    
    def _read_lean_zip(self, file_path: Path, symbol: Symbol) -> Iterator[BaseData]:
        """Read Lean ZIP format data."""
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            file_names = zip_file.namelist()
            if not file_names:
                return
            
            # Read the first file in the ZIP
            with zip_file.open(file_names[0]) as data_file:
                content = data_file.read().decode('utf-8')
                
                for line in content.strip().split('\n'):
                    if not line.strip():
                        continue
                    
                    try:
                        data_point = self._parse_lean_line(line, symbol)
                        if data_point:
                            yield data_point
                    except Exception as e:
                        print(f"Error parsing Lean line '{line}': {e}")
                        continue
    
    def _parse_lean_line(self, line: str, symbol: Symbol) -> Optional[BaseData]:
        """Parse a line from Lean format."""
        parts = line.split(',')
        
        if len(parts) < 2:
            return None
        
        try:
            # First field is timestamp in milliseconds
            timestamp_ms = int(parts[0])
            time = datetime.utcfromtimestamp(timestamp_ms / 1000.0)
            
            if len(parts) >= 6:
                # TradeBar format: timestamp_ms,open,high,low,close,volume
                return TradeBar(
                    symbol=symbol,
                    time=time,
                    value=Decimal(parts[4]),  # close
                    data_type=DataType.TRADE_BAR,
                    open=Decimal(parts[1]),
                    high=Decimal(parts[2]),
                    low=Decimal(parts[3]),
                    close=Decimal(parts[4]),
                    volume=int(parts[5])
                )
            elif len(parts) >= 5:
                # Tick format: timestamp_ms,value,tick_type,quantity,exchange
                return Tick(
                    symbol=symbol,
                    time=time,
                    value=Decimal(parts[1]),
                    data_type=DataType.TICK,
                    tick_type=TickType(parts[2]) if len(parts) > 2 else TickType.TRADE,
                    quantity=int(parts[3]) if len(parts) > 3 else 0,
                    exchange=parts[4] if len(parts) > 4 else ''
                )
            else:
                # Simple format: timestamp_ms,value
                return BaseData(
                    symbol=symbol,
                    time=time,
                    value=Decimal(parts[1]),
                    data_type=DataType.TRADE_BAR
                )
                
        except (ValueError, IndexError) as e:
            print(f"Error parsing Lean line: {e}")
            return None


class DataFileConverter:
    """
    Utility for converting between different data file formats.
    """
    
    @staticmethod
    def convert_file(input_path: Path, output_path: Path, 
                    input_format: FileFormat = None, 
                    output_format: FileFormat = None,
                    symbol: Symbol = None) -> bool:
        """
        Convert a data file from one format to another.
        """
        try:
            # Read data from input file
            reader = DataFileReader(input_format)
            data = list(reader.read_data(input_path, symbol))
            
            if not data:
                print("No data found in input file")
                return False
            
            # Write data to output file
            writer = DataFileWriter(output_format or FileFormat.CSV)
            return writer.write_data(output_path, data)
            
        except Exception as e:
            print(f"Error converting file: {e}")
            return False
    
    @staticmethod
    def batch_convert(input_directory: Path, output_directory: Path,
                     input_format: FileFormat, output_format: FileFormat,
                     file_pattern: str = "*") -> Dict[str, bool]:
        """
        Convert multiple files in a directory.
        """
        results = {}
        
        input_files = list(input_directory.glob(file_pattern))
        
        for input_file in input_files:
            try:
                # Generate output file path
                output_file = output_directory / input_file.name
                
                # Change extension based on output format
                if output_format == FileFormat.CSV:
                    output_file = output_file.with_suffix('.csv')
                elif output_format == FileFormat.JSON:
                    output_file = output_file.with_suffix('.json')
                elif output_format == FileFormat.LEAN_ZIP:
                    output_file = output_file.with_suffix('.zip')
                
                # Convert file
                success = DataFileConverter.convert_file(
                    input_file, output_file, input_format, output_format
                )
                
                results[str(input_file)] = success
                
            except Exception as e:
                print(f"Error converting {input_file}: {e}")
                results[str(input_file)] = False
        
        return results