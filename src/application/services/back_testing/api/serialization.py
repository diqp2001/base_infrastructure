"""
Serialization utilities for API data conversion.
Handles JSON serialization/deserialization with proper type conversion.
"""

import json
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type, TypeVar, get_origin, get_args
from dataclasses import is_dataclass, fields
from enum import Enum

from .interfaces import IApiSerializer
from .exceptions import SerializationException

T = TypeVar('T')


class ApiSerializer(IApiSerializer):
    """
    JSON serializer for API data with support for dataclasses, decimals, and enums.
    """
    
    def __init__(self, date_format: str = "%Y-%m-%dT%H:%M:%S.%fZ"):
        """Initialize serializer with date format."""
        self.date_format = date_format
    
    def serialize(self, obj: Any) -> str:
        """Serialize a Python object to JSON string."""
        try:
            return json.dumps(obj, default=self._serialize_object, ensure_ascii=False, indent=None)
        except Exception as e:
            raise SerializationException(f"Failed to serialize object: {str(e)}", obj, e)
    
    def deserialize(self, json_str: str, target_type: Type[T]) -> T:
        """Deserialize JSON string to Python object of specified type."""
        try:
            if not json_str or json_str.strip() == "":
                raise SerializationException("Empty JSON string provided")
            
            data = json.loads(json_str)
            return self._deserialize_object(data, target_type)
        except json.JSONDecodeError as e:
            raise SerializationException(f"Invalid JSON format: {str(e)}", json_str, e)
        except Exception as e:
            raise SerializationException(f"Failed to deserialize to {target_type.__name__}: {str(e)}", json_str, e)
    
    def serialize_decimal(self, value: Decimal) -> str:
        """Serialize a Decimal value to string format."""
        return str(value)
    
    def deserialize_decimal(self, value: str) -> Decimal:
        """Deserialize string to Decimal value."""
        try:
            return Decimal(value)
        except Exception as e:
            raise SerializationException(f"Failed to convert '{value}' to Decimal: {str(e)}", value, e)
    
    def _serialize_object(self, obj: Any) -> Any:
        """Custom serialization for complex objects."""
        if isinstance(obj, datetime):
            return obj.strftime(self.date_format)
        elif isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif is_dataclass(obj):
            return self._serialize_dataclass(obj)
        elif hasattr(obj, '__dict__'):
            return self._serialize_object_dict(obj)
        elif isinstance(obj, (list, tuple)):
            return [self._serialize_object(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._serialize_object(value) for key, value in obj.items()}
        else:
            return obj
    
    def _serialize_dataclass(self, obj: Any) -> Dict[str, Any]:
        """Serialize a dataclass to dictionary."""
        result = {}
        for field in fields(obj):
            value = getattr(obj, field.name)
            if value is not None:
                result[field.name] = self._serialize_object(value)
        return result
    
    def _serialize_object_dict(self, obj: Any) -> Dict[str, Any]:
        """Serialize an object with __dict__ to dictionary."""
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith('_') and value is not None:
                result[key] = self._serialize_object(value)
        return result
    
    def _deserialize_object(self, data: Any, target_type: Type[T]) -> T:
        """Deserialize data to target type."""
        if data is None:
            return None
        
        # Handle basic types
        if target_type in (str, int, float, bool):
            return target_type(data)
        
        # Handle Decimal
        if target_type is Decimal:
            return self.deserialize_decimal(str(data))
        
        # Handle datetime
        if target_type is datetime:
            return self._deserialize_datetime(data)
        
        # Handle date
        if target_type is date:
            return self._deserialize_date(data)
        
        # Handle Enum types
        if isinstance(target_type, type) and issubclass(target_type, Enum):
            return self._deserialize_enum(data, target_type)
        
        # Handle List types
        if hasattr(target_type, '__origin__') and target_type.__origin__ is list:
            return self._deserialize_list(data, target_type)
        
        # Handle Dict types
        if hasattr(target_type, '__origin__') and target_type.__origin__ is dict:
            return self._deserialize_dict(data, target_type)
        
        # Handle Optional types
        if hasattr(target_type, '__origin__') and target_type.__origin__ is type(Optional[int]).__origin__:
            args = get_args(target_type)
            if len(args) == 2 and type(None) in args:
                non_none_type = args[0] if args[1] is type(None) else args[1]
                return self._deserialize_object(data, non_none_type)
        
        # Handle dataclass types
        if is_dataclass(target_type):
            return self._deserialize_dataclass(data, target_type)
        
        # Handle generic objects
        if isinstance(data, dict):
            return self._deserialize_generic_object(data, target_type)
        
        # Fallback: try direct conversion
        try:
            return target_type(data)
        except Exception as e:
            raise SerializationException(
                f"Cannot deserialize {type(data).__name__} to {target_type.__name__}: {str(e)}",
                data, e
            )
    
    def _deserialize_datetime(self, data: Any) -> datetime:
        """Deserialize datetime from string."""
        if isinstance(data, datetime):
            return data
        
        if not isinstance(data, str):
            raise SerializationException(f"Expected string for datetime, got {type(data).__name__}")
        
        # Try multiple datetime formats
        formats = [
            self.date_format,
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(data, fmt)
            except ValueError:
                continue
        
        raise SerializationException(f"Cannot parse datetime from '{data}'")
    
    def _deserialize_date(self, data: Any) -> date:
        """Deserialize date from string."""
        if isinstance(data, date):
            return data
        
        if isinstance(data, datetime):
            return data.date()
        
        if not isinstance(data, str):
            raise SerializationException(f"Expected string for date, got {type(data).__name__}")
        
        try:
            return datetime.strptime(data, "%Y-%m-%d").date()
        except ValueError as e:
            raise SerializationException(f"Cannot parse date from '{data}': {str(e)}")
    
    def _deserialize_enum(self, data: Any, enum_type: Type[Enum]) -> Enum:
        """Deserialize enum from value."""
        try:
            return enum_type(data)
        except ValueError:
            # Try by name if value doesn't work
            for member in enum_type:
                if member.name == data:
                    return member
            raise SerializationException(f"Invalid value '{data}' for enum {enum_type.__name__}")
    
    def _deserialize_list(self, data: Any, list_type: Type) -> List[Any]:
        """Deserialize list with proper element types."""
        if not isinstance(data, list):
            raise SerializationException(f"Expected list, got {type(data).__name__}")
        
        args = get_args(list_type)
        if not args:
            return data  # Untyped list
        
        element_type = args[0]
        return [self._deserialize_object(item, element_type) for item in data]
    
    def _deserialize_dict(self, data: Any, dict_type: Type) -> Dict[Any, Any]:
        """Deserialize dictionary with proper key/value types."""
        if not isinstance(data, dict):
            raise SerializationException(f"Expected dict, got {type(data).__name__}")
        
        args = get_args(dict_type)
        if len(args) != 2:
            return data  # Untyped dict
        
        key_type, value_type = args
        result = {}
        for key, value in data.items():
            deserialized_key = self._deserialize_object(key, key_type)
            deserialized_value = self._deserialize_object(value, value_type)
            result[deserialized_key] = deserialized_value
        
        return result
    
    def _deserialize_dataclass(self, data: Any, dataclass_type: Type[T]) -> T:
        """Deserialize dataclass from dictionary."""
        if not isinstance(data, dict):
            raise SerializationException(f"Expected dict for dataclass {dataclass_type.__name__}, got {type(data).__name__}")
        
        kwargs = {}
        field_types = {f.name: f.type for f in fields(dataclass_type)}
        
        for field_name, field_type in field_types.items():
            if field_name in data:
                try:
                    kwargs[field_name] = self._deserialize_object(data[field_name], field_type)
                except Exception as e:
                    raise SerializationException(
                        f"Failed to deserialize field '{field_name}' in {dataclass_type.__name__}: {str(e)}"
                    )
        
        try:
            return dataclass_type(**kwargs)
        except Exception as e:
            raise SerializationException(
                f"Failed to create {dataclass_type.__name__} instance: {str(e)}",
                data, e
            )
    
    def _deserialize_generic_object(self, data: Dict[str, Any], target_type: Type[T]) -> T:
        """Deserialize to a generic object type."""
        try:
            # Try to create instance with no args first
            obj = target_type()
            
            # Set attributes from data
            for key, value in data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            
            return obj
        except Exception:
            # Try to create with data as kwargs
            try:
                return target_type(**data)
            except Exception as e:
                raise SerializationException(
                    f"Cannot create {target_type.__name__} from data: {str(e)}",
                    data, e
                )


class ApiResponseDeserializer:
    """
    Specialized deserializer for API responses with error handling.
    """
    
    def __init__(self, serializer: Optional[ApiSerializer] = None):
        """Initialize with optional custom serializer."""
        self.serializer = serializer or ApiSerializer()
    
    def deserialize_response(self, response_data: str, success_type: Type[T], 
                           error_type: Optional[Type] = None) -> T:
        """
        Deserialize API response, handling both success and error cases.
        """
        try:
            # Parse JSON first
            data = json.loads(response_data) if isinstance(response_data, str) else response_data
            
            # Check if response indicates success
            if isinstance(data, dict):
                success = data.get('success', True)  # Default to success if not specified
                
                if success:
                    return self.serializer.deserialize(response_data, success_type)
                else:
                    # Handle error response
                    if error_type:
                        return self.serializer.deserialize(response_data, error_type)
                    else:
                        # Raise exception with error details
                        errors = data.get('errors', ['Unknown error'])
                        error_message = '; '.join(errors) if isinstance(errors, list) else str(errors)
                        raise SerializationException(f"API returned error: {error_message}")
            
            # If not a dict or no success indicator, assume success
            return self.serializer.deserialize(response_data, success_type)
            
        except json.JSONDecodeError as e:
            raise SerializationException(f"Invalid JSON in API response: {str(e)}")
        except Exception as e:
            if isinstance(e, SerializationException):
                raise
            raise SerializationException(f"Failed to deserialize API response: {str(e)}")
    
    def deserialize_list_response(self, response_data: str, item_type: Type[T]) -> List[T]:
        """Deserialize API response containing a list of items."""
        try:
            data = json.loads(response_data) if isinstance(response_data, str) else response_data
            
            if isinstance(data, dict):
                # Handle wrapped list response
                if 'data' in data:
                    list_data = data['data']
                elif 'items' in data:
                    list_data = data['items']
                elif 'results' in data:
                    list_data = data['results']
                else:
                    # Assume the dict itself should be converted to a list
                    list_data = [data]
            elif isinstance(data, list):
                list_data = data
            else:
                raise SerializationException(f"Expected list or dict with list, got {type(data).__name__}")
            
            return [self.serializer._deserialize_object(item, item_type) for item in list_data]
            
        except Exception as e:
            if isinstance(e, SerializationException):
                raise
            raise SerializationException(f"Failed to deserialize list response: {str(e)}")


# Utility functions for common serialization tasks

def serialize_request_data(data: Any) -> str:
    """Serialize request data for API calls."""
    serializer = ApiSerializer()
    return serializer.serialize(data)


def deserialize_response_data(response_data: str, target_type: Type[T]) -> T:
    """Deserialize response data from API calls."""
    deserializer = ApiResponseDeserializer()
    return deserializer.deserialize_response(response_data, target_type)


def serialize_for_cache(obj: Any) -> str:
    """Serialize object for caching with minimal formatting."""
    serializer = ApiSerializer()
    return serializer.serialize(obj)


def deserialize_from_cache(cached_data: str, target_type: Type[T]) -> T:
    """Deserialize object from cache."""
    serializer = ApiSerializer()
    return serializer.deserialize(cached_data, target_type)


def convert_dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    """Convert dataclass or object to dictionary for API requests."""
    if is_dataclass(obj):
        serializer = ApiSerializer()
        return serializer._serialize_dataclass(obj)
    elif hasattr(obj, '__dict__'):
        serializer = ApiSerializer()
        return serializer._serialize_object_dict(obj)
    else:
        raise SerializationException(f"Cannot convert {type(obj).__name__} to dict")


def safe_deserialize(data: str, target_type: Type[T], default: Optional[T] = None) -> Optional[T]:
    """
    Safely deserialize data, returning default value on error.
    """
    try:
        serializer = ApiSerializer()
        return serializer.deserialize(data, target_type)
    except SerializationException:
        return default