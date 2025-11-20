# src/application/managers/project_managers/project_manager.py

class ProjectManager:
    """
    Base Project Manager class for orchestrating various manager components.
    """
    def __init__(self):
        self.api_service = None
        self.database_service = None
        self.data_service = None
        self.model_service = None
        self.portfolio_service = None
        self.strategy_service = None
        self.reporting_service = None
        self.web_service = None

    def setup_api_service(self, api_service):
        self.api_service = api_service

    def setup_database_service(self, database_service):
        self.database_service = database_service

    def setup_data_service(self, data_service):
        self.data_service = data_service

    

    def setup_model_service(self, model_service):
        self.model_service = model_service



    def execute(self):
        """
        Execute the project workflow. This method should be overridden by child classes.
        """
        raise NotImplementedError("Execute method should be implemented by the child class.")
