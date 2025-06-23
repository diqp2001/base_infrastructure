from src.infrastructure.database.base_factory import BaseFactory

class ModelRegistry:
    """
    Manages model registration and table creation for multiple projects.
    """
    def __init__(self, db_type):
        self.base_factory = BaseFactory(db_type)
        self.models = []

    def register_models(self, models):
        for model in models:
            self.models.append(model)
            model.__table__.create(self.base_factory.engine, checkfirst=True)
        self.base_factory.SessionLocal.commit()
    def register_model(self, model):
        """
        Register a model with the Base for later use in queries or table creation.
        """
        if model not in self.models:
            self.models.append(model)
            model.__table__.create(self.base_factory.engine, checkfirst=True)
        self.base_factory.SessionLocal.commit()

    def initialize_database_and_create_all_tables(self):
        self.base_factory.initialize_database_and_create_all_tables()
    
    def get_models(self):
        """
        Return the list of registered models.
        """
        return self.models