"""
refactoring 


BaseProjectAlgorithm
on_data (engine calls it)-> _train_models
_train_models -> train_complete_pipeline

ModelTrainer
train_complete_pipeline->_prepare_factor_data-_normalize_and_enhance_factors-_train_models-_evaluate_model_performance
DataLoader

FactorEnginedDataManager

populate_price_factors ->populate_factor (ensure_entities_exist, _create_factor_definitions,_calculate_factor_values)




tickers: List[str],
                    start_date: datetime = None,
                    end_date: datetime = None,
                    initial_capital: float = 100_000,
                    model_type: str = 'both',
"""



