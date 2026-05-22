

"""
src/domain/entities/factor/finance/portfolio/portfolio_value_factor.py

PortfolioValueFactor domain entity - calculates portfolio value from holding values.
"""

from typing import Optional, Dict, Any
from decimal import Decimal
import decimal

from src.domain.entities.factor.finance.portfolio.portfolio_factor import PortfolioFactor


class PortfolioValueFactor(PortfolioFactor):
    """Domain entity representing a portfolio value factor that calculates total portfolio value."""

    def __init__(
        self,
        name: str,
        group: str = "value",
        subgroup: Optional[str] = "portfolio",
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        if definition is None:
            definition = f"Portfolio value factor: {name}"
            
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency=frequency,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )

    def calculate(self, dependencies: Dict[str, Any]) -> Decimal:
        """
        Calculate portfolio value by summing all holding values.
        
        This method handles the indirect dependency case where a portfolio's value
        is calculated by aggregating the values of all holdings that belong to it.
        
        Args:
            dependencies: Dictionary containing holding value factors, where:
                - Key: factor identifier (e.g., "factor_123" for holding value factor)
                - Value: The calculated holding value (int, float, Decimal, or object with .value)
            
        Returns:
            Total portfolio value as Decimal
        """
        try:
            total_value = Decimal('0.0')
            
            # Sum up all holding values from dependencies
            for dependency_name, dependency_value in dependencies.items():
                try:
                    if isinstance(dependency_value, (int, float, Decimal)):
                        total_value += Decimal(str(dependency_value))
                    elif hasattr(dependency_value, 'value'):
                        total_value += Decimal(str(dependency_value.value))
                    else:
                        # Try to convert to string then Decimal as fallback
                        total_value += Decimal(str(dependency_value))
                except (ValueError, TypeError, decimal.InvalidOperation) as convert_error:
                    print(f"Warning: Could not convert dependency {dependency_name} with value {dependency_value}: {convert_error}")
                    # Continue with other dependencies
                    continue
                    
            print(f"Portfolio {self.name} calculated total value: {total_value} from {len(dependencies)} dependencies")
            return total_value
            
        except Exception as e:
            print(f"Error calculating portfolio value for {self.name}: {e}")
            return Decimal('0.0')

    def get_dependency_requirements(self) -> Dict[str, str]:
        """
        Get the dependency requirements for this portfolio factor.
        
        Returns:
            Dictionary describing the required dependencies and their types
        """
        return {
            "relationship_type": "indirect",  # Portfolio has indirect relationship to holdings
            "target_entities": "holdings",    # We need to aggregate from holdings
            "aggregation_method": "sum"       # Sum all holding values
        }
