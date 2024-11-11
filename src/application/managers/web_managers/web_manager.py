# src/managers/web_manager/web_manager.py

class WebManager:
    """
    Parent WebManager class for common web server operations.
    Provides basic methods for managing and configuring web services.
    """

    def __init__(self, host='127.0.0.1', port=5000):
        """
        Initialize the WebManager with server configuration.
        :param host: The host address to bind the server to.
        :param port: The port to bind the server to.
        """
        self.host = host
        self.port = port
        print(f"Initialized WebManager with host {self.host} and port {self.port}")

    def start_server(self):
        """
        Method to start a web server. Should be implemented by child classes.
        """
        raise NotImplementedError("start_server() must be implemented by subclasses")

    def stop_server(self):
        """
        Stops the web server. Should be implemented by child classes if applicable.
        """
        raise NotImplementedError("stop_server() must be implemented by subclasses")
