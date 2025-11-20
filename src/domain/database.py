
from infrastructure.database.model_registry import ModelRegistry

class Database:
    """
    A domain object that encapsulates the database configuration, model registration,
    and session management for multiple projects.
    """
    def __init__(self, db_type: str):
        self.db_type = db_type
        self.model_registry = ModelRegistry(self.db_type)
        self.SessionLocal = self.model_registry.base_factory.SessionLocal
        

    def register_model(self, model):
        """
        Register a model using the model registry.
        """
        self.model_registry.register_model(model)
    
    def register_models(self, models):
        """
        Register a models using the model registry.
        """
        self.model_registry.register_models(models)

    def initialize_database_and_create_all_tables(self):
        """
        Create all tables for the registered models.
        """
        self.model_registry.base_factory.initialize_database_and_create_all_tables()

    def drop_all_tables(self):
        """
        Drop all tables for the registered models.
        """
        self.model_registry.base_factory.drop_all_tables()

    
    
    def get_models(self):
        """
        Return the list of registered models.
        """
        return self.model_registry.models
