"""
Parameter management for optimization.
Handles optimization parameters, parameter sets, and parameter space definitions.
"""

import json
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple, Iterator
from datetime import datetime
from uuid import uuid4

from .enums import ParameterType
from .interfaces import IParameterSpace


@dataclass
class OptimizationParameter:
    """
    Represents a single optimization parameter with its constraints and properties.
    """
    name: str
    min_value: Union[int, float, str]
    max_value: Union[int, float, str]
    parameter_type: ParameterType = ParameterType.FLOAT
    step: Optional[float] = None
    is_discrete: bool = False
    allowed_values: Optional[List[Any]] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate parameter configuration after initialization."""
        if self.parameter_type == ParameterType.CATEGORICAL:
            if not self.allowed_values:
                raise ValueError(f"Parameter {self.name}: Categorical parameters must have allowed_values")
        
        if self.parameter_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
            if not isinstance(self.min_value, (int, float)) or not isinstance(self.max_value, (int, float)):
                raise ValueError(f"Parameter {self.name}: Numeric parameters must have numeric min/max values")
            
            if self.min_value >= self.max_value:
                raise ValueError(f"Parameter {self.name}: min_value must be less than max_value")
    
    def validate_value(self, value: Any) -> bool:
        """Validate if a value is within parameter constraints."""
        try:
            if self.parameter_type == ParameterType.CATEGORICAL:
                return value in self.allowed_values
            
            elif self.parameter_type == ParameterType.BOOLEAN:
                return isinstance(value, bool)
            
            elif self.parameter_type == ParameterType.STRING:
                return isinstance(value, str)
            
            elif self.parameter_type == ParameterType.INTEGER:
                if not isinstance(value, (int, np.integer)):
                    return False
                return self.min_value <= value <= self.max_value
            
            elif self.parameter_type == ParameterType.FLOAT:
                if not isinstance(value, (int, float, np.number)):
                    return False
                return self.min_value <= value <= self.max_value
            
            return False
        except (TypeError, ValueError):
            return False
    
    def generate_random_value(self) -> Any:
        """Generate a random value within parameter constraints."""
        if self.parameter_type == ParameterType.CATEGORICAL:
            return np.random.choice(self.allowed_values)
        
        elif self.parameter_type == ParameterType.BOOLEAN:
            return np.random.choice([True, False])
        
        elif self.parameter_type == ParameterType.INTEGER:
            if self.step:
                # Handle stepped integers
                steps = int((self.max_value - self.min_value) / self.step) + 1
                step_value = np.random.randint(0, steps)
                return int(self.min_value + step_value * self.step)
            else:
                return np.random.randint(self.min_value, self.max_value + 1)
        
        elif self.parameter_type == ParameterType.FLOAT:
            if self.step:
                # Handle stepped floats
                steps = int((self.max_value - self.min_value) / self.step) + 1
                step_value = np.random.randint(0, steps)
                return self.min_value + step_value * self.step
            else:
                return np.random.uniform(self.min_value, self.max_value)
        
        elif self.parameter_type == ParameterType.STRING:
            # For string parameters, return one of allowed values or generate random string
            if self.allowed_values:
                return np.random.choice(self.allowed_values)
            else:
                # Generate random string (for demonstration)
                return f"value_{np.random.randint(0, 1000)}"
        
        raise ValueError(f"Cannot generate random value for parameter type: {self.parameter_type}")
    
    def clip_value(self, value: Any) -> Any:
        """Clip a value to parameter bounds."""
        if self.parameter_type == ParameterType.CATEGORICAL:
            return value if value in self.allowed_values else self.allowed_values[0]
        
        elif self.parameter_type == ParameterType.BOOLEAN:
            return bool(value)
        
        elif self.parameter_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
            clipped = np.clip(value, self.min_value, self.max_value)
            if self.parameter_type == ParameterType.INTEGER:
                return int(clipped)
            return float(clipped)
        
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter to dictionary for serialization."""
        return {
            'name': self.name,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'parameter_type': self.parameter_type.value,
            'step': self.step,
            'is_discrete': self.is_discrete,
            'allowed_values': self.allowed_values,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationParameter':
        """Create parameter from dictionary."""
        return cls(
            name=data['name'],
            min_value=data['min_value'],
            max_value=data['max_value'],
            parameter_type=ParameterType(data['parameter_type']),
            step=data.get('step'),
            is_discrete=data.get('is_discrete', False),
            allowed_values=data.get('allowed_values'),
            description=data.get('description')
        )


@dataclass
class OptimizationParameterSet:
    """
    Collection of parameters for a single optimization run.
    Represents one point in the parameter space.
    """
    parameters: Dict[str, Any]
    unique_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    fitness: Optional[float] = None
    generation: Optional[int] = None
    parent_ids: Optional[List[str]] = None
    
    def get_parameter_value(self, name: str, default: Any = None) -> Any:
        """Get parameter value by name."""
        return self.parameters.get(name, default)
    
    def set_parameter_value(self, name: str, value: Any) -> None:
        """Set parameter value by name."""
        self.parameters[name] = value
    
    def copy(self) -> 'OptimizationParameterSet':
        """Create a deep copy of the parameter set."""
        return OptimizationParameterSet(
            parameters=self.parameters.copy(),
            unique_id=str(uuid4()),
            timestamp=datetime.now(),
            fitness=self.fitness,
            generation=self.generation,
            parent_ids=self.parent_ids.copy() if self.parent_ids else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'parameters': self.parameters,
            'unique_id': self.unique_id,
            'timestamp': self.timestamp.isoformat(),
            'fitness': self.fitness,
            'generation': self.generation,
            'parent_ids': self.parent_ids
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationParameterSet':
        """Create parameter set from dictionary."""
        return cls(
            parameters=data['parameters'],
            unique_id=data['unique_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            fitness=data.get('fitness'),
            generation=data.get('generation'),
            parent_ids=data.get('parent_ids')
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'OptimizationParameterSet':
        """Create parameter set from JSON string."""
        return cls.from_dict(json.loads(json_str))


class ParameterSpace(IParameterSpace):
    """
    Defines the complete parameter search space for optimization.
    Manages parameter constraints and generates valid parameter combinations.
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._parameters: Dict[str, OptimizationParameter] = {}
        self._constraints: List[callable] = []
    
    def add_parameter(self, parameter: OptimizationParameter) -> None:
        """Add a parameter to the search space."""
        self._parameters[parameter.name] = parameter
    
    def remove_parameter(self, parameter_name: str) -> bool:
        """Remove a parameter from the search space."""
        if parameter_name in self._parameters:
            del self._parameters[parameter_name]
            return True
        return False
    
    def get_parameter(self, parameter_name: str) -> Optional[OptimizationParameter]:
        """Get a parameter by name."""
        return self._parameters.get(parameter_name)
    
    def get_all_parameters(self) -> List[OptimizationParameter]:
        """Get all parameters in the search space."""
        return list(self._parameters.values())
    
    def get_parameter_names(self) -> List[str]:
        """Get all parameter names."""
        return list(self._parameters.keys())
    
    def generate_random_parameter_set(self) -> OptimizationParameterSet:
        """Generate a random parameter set within the search space."""
        parameters = {}
        for param in self._parameters.values():
            parameters[param.name] = param.generate_random_value()
        
        param_set = OptimizationParameterSet(parameters=parameters)
        
        # Apply constraints and regenerate if necessary
        max_attempts = 100
        attempts = 0
        while not self.validate_parameter_set(param_set) and attempts < max_attempts:
            parameters = {}
            for param in self._parameters.values():
                parameters[param.name] = param.generate_random_value()
            param_set = OptimizationParameterSet(parameters=parameters)
            attempts += 1
        
        return param_set
    
    def validate_parameter_set(self, parameter_set: OptimizationParameterSet) -> bool:
        """Validate that a parameter set is within the search space bounds."""
        # Check individual parameter constraints
        for param_name, param_value in parameter_set.parameters.items():
            if param_name not in self._parameters:
                return False
            
            parameter = self._parameters[param_name]
            if not parameter.validate_value(param_value):
                return False
        
        # Check global constraints
        for constraint in self._constraints:
            if not constraint(parameter_set):
                return False
        
        return True
    
    def repair_parameter_set(self, parameter_set: OptimizationParameterSet) -> OptimizationParameterSet:
        """Repair a parameter set to satisfy constraints."""
        repaired_parameters = {}
        
        for param_name, param_value in parameter_set.parameters.items():
            if param_name in self._parameters:
                parameter = self._parameters[param_name]
                repaired_parameters[param_name] = parameter.clip_value(param_value)
            else:
                repaired_parameters[param_name] = param_value
        
        return OptimizationParameterSet(parameters=repaired_parameters)
    
    def get_total_combinations(self) -> Optional[int]:
        """Get total number of possible parameter combinations (if finite)."""
        total = 1
        
        for parameter in self._parameters.values():
            if parameter.parameter_type == ParameterType.CATEGORICAL:
                total *= len(parameter.allowed_values)
            elif parameter.parameter_type == ParameterType.BOOLEAN:
                total *= 2
            elif parameter.step:
                if parameter.parameter_type == ParameterType.INTEGER:
                    steps = int((parameter.max_value - parameter.min_value) / parameter.step) + 1
                    total *= steps
                elif parameter.parameter_type == ParameterType.FLOAT:
                    steps = int((parameter.max_value - parameter.min_value) / parameter.step) + 1
                    total *= steps
            else:
                # Continuous parameters have infinite combinations
                return None
        
        return total
    
    def generate_grid_combinations(self) -> Iterator[OptimizationParameterSet]:
        """Generate all possible parameter combinations for grid search."""
        parameter_names = list(self._parameters.keys())
        parameter_values = []
        
        for param_name in parameter_names:
            parameter = self._parameters[param_name]
            
            if parameter.parameter_type == ParameterType.CATEGORICAL:
                parameter_values.append(parameter.allowed_values)
            elif parameter.parameter_type == ParameterType.BOOLEAN:
                parameter_values.append([True, False])
            elif parameter.step:
                if parameter.parameter_type == ParameterType.INTEGER:
                    values = list(range(int(parameter.min_value), 
                                      int(parameter.max_value) + 1, 
                                      int(parameter.step)))
                    parameter_values.append(values)
                elif parameter.parameter_type == ParameterType.FLOAT:
                    values = np.arange(parameter.min_value, 
                                     parameter.max_value + parameter.step, 
                                     parameter.step).tolist()
                    parameter_values.append(values)
            else:
                raise ValueError(f"Cannot generate grid for continuous parameter: {param_name}")
        
        # Generate all combinations using itertools-style approach
        def _generate_combinations(index: int, current_params: Dict[str, Any]):
            if index == len(parameter_names):
                param_set = OptimizationParameterSet(parameters=current_params.copy())
                if self.validate_parameter_set(param_set):
                    yield param_set
                return
            
            param_name = parameter_names[index]
            for value in parameter_values[index]:
                current_params[param_name] = value
                yield from _generate_combinations(index + 1, current_params)
        
        yield from _generate_combinations(0, {})
    
    def add_constraint(self, constraint: callable) -> None:
        """Add a constraint function to the parameter space."""
        self._constraints.append(constraint)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter space to dictionary."""
        return {
            'name': self.name,
            'parameters': {name: param.to_dict() for name, param in self._parameters.items()}
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load parameter space from dictionary."""
        self.name = data['name']
        self._parameters = {}
        for name, param_data in data['parameters'].items():
            self._parameters[name] = OptimizationParameter.from_dict(param_data)
    
    def __len__(self) -> int:
        """Get number of parameters in the space."""
        return len(self._parameters)
    
    def __contains__(self, parameter_name: str) -> bool:
        """Check if parameter exists in the space."""
        return parameter_name in self._parameters
    
    def __iter__(self) -> Iterator[OptimizationParameter]:
        """Iterate over all parameters."""
        return iter(self._parameters.values())
    
    def __repr__(self) -> str:
        """String representation of the parameter space."""
        return f"ParameterSpace(name='{self.name}', parameters={len(self._parameters)})"