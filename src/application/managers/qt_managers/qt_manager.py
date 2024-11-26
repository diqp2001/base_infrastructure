from PyQt5.QtWidgets import QApplication
import sys

class QtManager:
    """
    Parent class for managing PyQt5 applications.
    Provides basic methods for initializing and running the application.
    """
    def __init__(self):
        self.app = QApplication(sys.argv)
        print("Initialized QtManager")

    def start_app(self, main_window):
        """
        Starts the application with the given main window.
        :param main_window: The main window instance to display.
        """
        print("Starting PyQt5 application...")
        main_window.show()
        sys.exit(self.app.exec_())
