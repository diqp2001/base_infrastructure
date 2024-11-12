# src/application/managers/project_managers/project_manager.py

class ProjectManager:
    """
    Base Project Manager class for orchestrating various manager components.
    """
    def __init__(self):
        self.api_manager = None
        self.database_manager = None
        self.data_manager = None
        self.model_manager = None
        self.portfolio_manager = None
        self.strategy_manager = None
        self.reporting_manager = None
        self.web_manager = None

    def setup_api_manager(self, api_manager):
        self.api_manager = api_manager

    def setup_database_manager(self, database_manager):
        self.database_manager = database_manager

    def setup_data_manager(self, data_manager):
        self.data_manager = data_manager

    

    def setup_model_manager(self, model_manager):
        self.model_manager = model_manager

    def setup_portfolio_manager(self, portfolio_manager):
        self.portfolio_manager = portfolio_manager

    def setup_strategy_manager(self, strategy_manager):
        self.strategy_manager = strategy_manager

    def setup_reporting_manager(self, reporting_manager):
        self.reporting_manager = reporting_manager

    def setup_web_manager(self, web_manager):
        self.web_manager = web_manager

    def execute(self):
        """
        Execute the project workflow. This method should be overridden by child classes.
        """
        raise NotImplementedError("Execute method should be implemented by the child class.")
