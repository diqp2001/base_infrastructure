# src/application/managers/project_managers/project_manager.py

class ProjectManager:
    """
    Base Project Manager class for orchestrating various manager components.
    """
    def __init__(self):
        # Recent logs of this process for the read-only monitoring dashboard (idempotent, never raises)
        try:
            from src.application.services.monitoring.log_store import install_monitoring_log_handler
            install_monitoring_log_handler(process_name=type(self).__name__)
        except Exception:
            pass
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
