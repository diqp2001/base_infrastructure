from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow
from application.services.ui_service.qt_service import QtService

class QtAppManager(QtService):
    """
    A manager class for loading and running a PyQt5 application with Qt Designer UI files.
    Uses the new QtService for application management.
    """
    def __init__(self, ui_file_path: str):
        super().__init__()
        self.ui_file_path = ui_file_path
        print(f"Initialized QtAppManager with UI file: {ui_file_path}")

    def load_main_window(self):
        """
        Loads the main window UI from a .ui file.
        :return: QMainWindow instance with the loaded UI.
        """
        class MainWindow(QMainWindow):
            pass

        main_window = MainWindow()
        uic.loadUi(self.ui_file_path, main_window)
        return main_window