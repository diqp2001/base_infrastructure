"""
Factor Calculation API Controller - handles REST endpoints for factor calculations.
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, List
import pandas as pd
from datetime import datetime, date

from src.application.services.data.entities.factor.factor_calculation_service import FactorCalculationService
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository


def create_factor_calculation_blueprint() -> Blueprint:
    """Create factor calculation API blueprint."""
    
    bp = Blueprint('factor_calculation', __name__, url_prefix='/api/factors')
    
    # Initialize services
    calculation_service = FactorCalculationService()
    factor_repository = BaseFactorRepository()
    
    @bp.route('/calculate', methods=['POST'])
    def calculate_factor():
        """
        Calculate factor values and store them in the database.
        
        Expected JSON payload:
        {
            "factor_id": int,
            "entity_id": int,
            "entity_type": "share",
            "data": {
                // Format depends on factor type:
                // For momentum: {"prices": [float], "dates": ["YYYY-MM-DD"]}
                // For technical: {"ohlcv": [[date, open, high, low, close, volume]]}
                // For volatility: {"returns": [float], "dates": ["YYYY-MM-DD"]}
            },
            "overwrite": bool (optional, default: false)
        }
        """
        try:
            payload = request.get_json()
            if not payload:
                return jsonify({"error": "No JSON payload provided"}), 400
            
            # Validate required fields
            required_fields = ['factor_id', 'entity_id', 'entity_type', 'data']
            for field in required_fields:
                if field not in payload:
                    return jsonify({"error": f"Missing required field: {field}"}), 400
            
            factor_id = payload['factor_id']
            entity_id = payload['entity_id']
            entity_type = payload['entity_type']
            data = payload['data']
            overwrite = payload.get('overwrite', False)
            
            # Get the factor from database
            factor = factor_repository.get_by_id(factor_id)
            if not factor:
                return jsonify({"error": f"Factor with ID {factor_id} not found"}), 404
            
            # Process data based on factor type
            processed_data = _process_input_data(factor, data)
            if 'error' in processed_data:
                return jsonify(processed_data), 400
            
            # Calculate and store factor values
            results = calculation_service.calculate_and_store_factor(
                factor=factor,
                entity_id=entity_id,
                entity_type=entity_type,
                data=processed_data,
                overwrite=overwrite
            )
            
            return jsonify({
                "success": True,
                "results": results
            })
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/calculate/bulk', methods=['POST'])
    def bulk_calculate_factors():
        """
        Calculate multiple factor values in bulk.
        
        Expected JSON payload:
        {
            "calculations": [
                {
                    "factor_id": int,
                    "entity_id": int,
                    "entity_type": "share",
                    "data": {...}
                }
            ],
            "overwrite": bool (optional, default: false)
        }
        """
        try:
            payload = request.get_json()
            if not payload:
                return jsonify({"error": "No JSON payload provided"}), 400
            
            calculations = payload.get('calculations', [])
            if not calculations:
                return jsonify({"error": "No calculations provided"}), 400
            
            overwrite = payload.get('overwrite', False)
            
            # Process each calculation
            processed_calculations = []
            for calc in calculations:
                # Validate required fields
                required_fields = ['factor_id', 'entity_id', 'entity_type', 'data']
                for field in required_fields:
                    if field not in calc:
                        return jsonify({"error": f"Missing required field '{field}' in calculation"}), 400
                
                # Get the factor from database
                factor = factor_repository.get_by_id(calc['factor_id'])
                if not factor:
                    return jsonify({"error": f"Factor with ID {calc['factor_id']} not found"}), 404
                
                # Process data based on factor type
                processed_data = _process_input_data(factor, calc['data'])
                if 'error' in processed_data:
                    return jsonify(processed_data), 400
                
                processed_calculations.append({
                    'factor': factor,
                    'entity_id': calc['entity_id'],
                    'entity_type': calc['entity_type'],
                    'data': processed_data
                })
            
            # Execute bulk calculations
            results = calculation_service.bulk_calculate_and_store(
                calculations=processed_calculations,
                overwrite=overwrite
            )
            
            return jsonify({
                "success": True,
                "results": results
            })
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/factors/<int:factor_id>/values', methods=['GET'])
    def get_factor_values(factor_id):
        """
        Retrieve factor values for a specific factor.
        
        Query parameters:
        - entity_id: int (optional)
        - start_date: YYYY-MM-DD (optional)
        - end_date: YYYY-MM-DD (optional)
        - format: 'json' or 'csv' (default: json)
        """
        try:
            entity_id = request.args.get('entity_id', type=int)
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            output_format = request.args.get('format', 'json')
            
            # Get factor values from repository
            if entity_id:
                values = factor_repository.get_factor_values(
                    factor_id=factor_id,
                    entity_id=entity_id,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                # Get all values for this factor
                factor_value_model = factor_repository.get_factor_value_model()
                query = factor_repository.session.query(factor_value_model).filter(
                    factor_value_model.factor_id == factor_id
                )
                
                if start_date:
                    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                    query = query.filter(factor_value_model.date >= start_date_obj)
                
                if end_date:
                    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
                    query = query.filter(factor_value_model.date <= end_date_obj)
                
                orm_values = query.order_by(factor_value_model.date).all()
                values = [factor_repository._to_domain_value(v) for v in orm_values]
            
            if output_format == 'csv':
                # Convert to CSV format
                df = pd.DataFrame([
                    {
                        'date': v.date,
                        'entity_id': v.entity_id,
                        'entity_type': getattr(v, 'entity_type', 'share'),
                        'value': v.value
                    } for v in values
                ])
                
                from io import StringIO
                output = StringIO()
                df.to_csv(output, index=False)
                csv_content = output.getvalue()
                
                from flask import Response
                return Response(
                    csv_content,
                    mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=factor_{factor_id}_values.csv'}
                )
            
            else:
                # Return JSON format
                return jsonify({
                    "factor_id": factor_id,
                    "values": [
                        {
                            "id": v.id,
                            "entity_id": v.entity_id,
                            "entity_type": getattr(v, 'entity_type', 'share'),
                            "date": v.date.isoformat(),
                            "value": v.value
                        } for v in values
                    ],
                    "count": len(values)
                })
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def _process_input_data(factor, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data based on factor type."""
        from src.domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor
        from src.domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor
        from src.domain.entities.factor.finance.financial_assets.share_factor.share_volatility_factor import ShareVolatilityFactor
        
        try:
            if isinstance(factor, ShareMomentumFactor):
                # Momentum factors need prices and dates
                if 'prices' not in data or 'dates' not in data:
                    return {"error": "Momentum factors require 'prices' and 'dates' in data"}
                
                # Convert date strings to date objects
                dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in data['dates']]
                return {"prices": data['prices'], "dates": dates}
            
            elif isinstance(factor, ShareTechnicalFactor):
                # Technical factors need OHLCV data
                if 'ohlcv' not in data:
                    return {"error": "Technical factors require 'ohlcv' data"}
                
                # Convert to pandas DataFrame
                df = pd.DataFrame(
                    data['ohlcv'],
                    columns=['date', 'open', 'high', 'low', 'close', 'volume']
                )
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                return df
            
            elif isinstance(factor, ShareVolatilityFactor):
                # Volatility factors need returns and dates
                if 'returns' not in data or 'dates' not in data:
                    return {"error": "Volatility factors require 'returns' and 'dates' in data"}
                
                # Convert date strings to date objects
                dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in data['dates']]
                return {"returns": data['returns'], "dates": dates}
            
            else:
                return {"error": f"Unsupported factor type: {type(factor).__name__}"}
        
        except Exception as e:
            return {"error": f"Error processing input data: {str(e)}"}
    
    return bp