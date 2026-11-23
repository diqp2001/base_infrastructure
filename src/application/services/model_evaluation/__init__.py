"""
Classifier model evaluation (CompanyShare classifiers): classification metrics, confusion matrix, probability
quintiles and their realised returns — independent of TradingStrategy / portfolio construction.
See src/domain/entities/ml/classifier_evaluation.py for the definitions (true class, predicted class, probability
quintile) and classifier_evaluation_service.py for the flow.
"""


def build_classifier_evaluation_service(factory, data=None):
    """The service over every stored classifier family (LGBM quintile momentum, cross-sectional momentum)."""
    from src.application.services.model_evaluation.classifier_evaluation_service import ClassifierEvaluationService
    from src.application.services.model_evaluation.classifier_sources import (
        CSMObservationSource,
        LGBMQuintileObservationSource,
    )
    return ClassifierEvaluationService([LGBMQuintileObservationSource(factory, data),
                                        CSMObservationSource(factory, data)])
