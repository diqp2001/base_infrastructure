import sys
from typing import Optional, Any, Callable, Dict
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow
from PyQt5.QtCore import QTimer


class QtService:
    """
    Service for managing PyQt5 applications and UI components.
    Provides centralized Qt application lifecycle management.
    """
    
    def __init__(self):
        """Initialize the Qt service."""
        self.app: Optional[QApplication] = None
        self.main_window: Optional[QWidget] = None
        self.timers: Dict[str, QTimer] = {}
        self._initialized = False
        
    def initialize_application(self, app_name: str = "QtApplication",
                             sys_argv: Optional[list] = None) -> QApplication:
        """
        Initialize the Qt application.
        
        Args:
            app_name: Name of the application
            sys_argv: System arguments (defaults to sys.argv)
            
        Returns:
            QApplication instance
        """
        if self.app is not None:
            print("Qt application already initialized")
            return self.app
            
        try:
            if sys_argv is None:
                sys_argv = sys.argv
                
            self.app = QApplication(sys_argv)
            self.app.setApplicationName(app_name)
            self._initialized = True
            print(f"Initialized Qt application: {app_name}")
            return self.app
            
        except Exception as e:
            print(f"Error initializing Qt application: {e}")
            raise

    def set_main_window(self, main_window: QWidget) -> None:
        """
        Set the main window for the application.
        
        Args:
            main_window: The main window instance to display
        """
        if not self._initialized:
            raise RuntimeError("Qt application not initialized. Call initialize_application() first.")
            
        self.main_window = main_window
        print("Main window set")

    def start_application(self, main_window: Optional[QWidget] = None) -> int:
        """
        Start the Qt application with the given main window.
        
        Args:
            main_window: The main window instance to display (optional if already set)
            
        Returns:
            Application exit code
        """
        if not self._initialized:
            raise RuntimeError("Qt application not initialized. Call initialize_application() first.")
            
        if main_window is not None:
            self.main_window = main_window
            
        if self.main_window is None:
            raise ValueError("No main window provided. Set main window first.")
            
        try:
            print("Starting Qt application...")
            self.main_window.show()
            return self.app.exec_()
            
        except Exception as e:
            print(f"Error starting Qt application: {e}")
            return 1

    def quit_application(self) -> None:
        """Quit the Qt application gracefully."""
        if self.app is not None:
            print("Quitting Qt application...")
            self.app.quit()

    def create_timer(self, timer_name: str, interval_ms: int, 
                    callback: Callable[[], None], single_shot: bool = False) -> QTimer:
        """
        Create a named timer with specified interval and callback.
        
        Args:
            timer_name: Unique name for the timer
            interval_ms: Interval in milliseconds
            callback: Function to call when timer fires
            single_shot: If True, timer fires only once
            
        Returns:
            QTimer instance
        """
        if not self._initialized:
            raise RuntimeError("Qt application not initialized. Call initialize_application() first.")
            
        if timer_name in self.timers:
            print(f"Timer '{timer_name}' already exists. Stopping existing timer.")
            self.stop_timer(timer_name)
            
        timer = QTimer()
        timer.timeout.connect(callback)
        timer.setSingleShot(single_shot)
        timer.setInterval(interval_ms)
        
        self.timers[timer_name] = timer
        print(f"Created timer '{timer_name}' with interval {interval_ms}ms")
        return timer

    def start_timer(self, timer_name: str) -> None:
        """
        Start a named timer.
        
        Args:
            timer_name: Name of the timer to start
        """
        if timer_name not in self.timers:
            raise ValueError(f"Timer '{timer_name}' not found")
            
        self.timers[timer_name].start()
        print(f"Started timer '{timer_name}'")

    def stop_timer(self, timer_name: str) -> None:
        """
        Stop a named timer.
        
        Args:
            timer_name: Name of the timer to stop
        """
        if timer_name not in self.timers:
            raise ValueError(f"Timer '{timer_name}' not found")
            
        self.timers[timer_name].stop()
        print(f"Stopped timer '{timer_name}'")

    def remove_timer(self, timer_name: str) -> None:
        """
        Remove a named timer.
        
        Args:
            timer_name: Name of the timer to remove
        """
        if timer_name in self.timers:
            self.stop_timer(timer_name)
            del self.timers[timer_name]
            print(f"Removed timer '{timer_name}'")

    def process_events(self) -> None:
        """Process pending Qt events."""
        if self.app is not None:
            self.app.processEvents()

    def set_application_style(self, style_name: str) -> None:
        """
        Set the application style.
        
        Args:
            style_name: Name of the style ('Windows', 'Fusion', etc.)
        """
        if not self._initialized:
            raise RuntimeError("Qt application not initialized. Call initialize_application() first.")
            
        try:
            self.app.setStyle(style_name)
            print(f"Set application style to: {style_name}")
        except Exception as e:
            print(f"Error setting style '{style_name}': {e}")

    def get_available_styles(self) -> list:
        """
        Get list of available Qt styles.
        
        Returns:
            List of available style names
        """
        if not self._initialized:
            raise RuntimeError("Qt application not initialized. Call initialize_application() first.")
            
        return self.app.style().metaObject().className()

    def set_organization_info(self, organization_name: str, 
                            organization_domain: str = None) -> None:
        """
        Set organization information for the application.
        
        Args:
            organization_name: Name of the organization
            organization_domain: Domain of the organization
        """
        if not self._initialized:
            raise RuntimeError("Qt application not initialized. Call initialize_application() first.")
            
        self.app.setOrganizationName(organization_name)
        if organization_domain:
            self.app.setOrganizationDomain(organization_domain)
        print(f"Set organization info: {organization_name}")

    def get_application_info(self) -> Dict[str, str]:
        """
        Get application information.
        
        Returns:
            Dictionary with application info
        """
        if not self._initialized:
            return {"status": "Not initialized"}
            
        return {
            "application_name": self.app.applicationName(),
            "organization_name": self.app.organizationName(),
            "organization_domain": self.app.organizationDomain(),
            "application_version": self.app.applicationVersion(),
            "qt_version": self.app.qVersion(),
            "style": self.app.style().objectName() if self.app.style() else "Unknown"
        }

    def is_initialized(self) -> bool:
        """
        Check if the Qt application is initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized

    def cleanup(self) -> None:
        """Clean up Qt resources."""
        # Stop all timers
        for timer_name in list(self.timers.keys()):
            self.remove_timer(timer_name)
            
        # Close main window if exists
        if self.main_window is not None:
            self.main_window.close()
            self.main_window = None
            
        # Quit application
        if self.app is not None:
            self.quit_application()
            
        self._initialized = False
        print("Qt service cleaned up")


class QtAppService(QtService):
    """
    Extended Qt service with application-specific functionality.
    Provides higher-level application management features.
    """
    
    def __init__(self, app_name: str = "Application"):
        """
        Initialize the Qt app service.
        
        Args:
            app_name: Name of the application
        """
        super().__init__()
        self.app_name = app_name
        self.windows: Dict[str, QWidget] = {}

    def create_application(self, organization_name: str = None,
                         organization_domain: str = None,
                         version: str = "1.0.0") -> QApplication:
        """
        Create and configure a complete Qt application.
        
        Args:
            organization_name: Organization name
            organization_domain: Organization domain
            version: Application version
            
        Returns:
            Configured QApplication instance
        """
        app = self.initialize_application(self.app_name)
        
        if organization_name:
            self.set_organization_info(organization_name, organization_domain)
            
        app.setApplicationVersion(version)
        
        print(f"Created Qt application: {self.app_name} v{version}")
        return app

    def register_window(self, window_name: str, window: QWidget) -> None:
        """
        Register a window with the service.
        
        Args:
            window_name: Unique name for the window
            window: Qt window/widget instance
        """
        self.windows[window_name] = window
        print(f"Registered window: {window_name}")

    def show_window(self, window_name: str) -> None:
        """
        Show a registered window.
        
        Args:
            window_name: Name of the window to show
        """
        if window_name not in self.windows:
            raise ValueError(f"Window '{window_name}' not registered")
            
        self.windows[window_name].show()
        print(f"Showing window: {window_name}")

    def hide_window(self, window_name: str) -> None:
        """
        Hide a registered window.
        
        Args:
            window_name: Name of the window to hide
        """
        if window_name not in self.windows:
            raise ValueError(f"Window '{window_name}' not registered")
            
        self.windows[window_name].hide()
        print(f"Hiding window: {window_name}")

    def get_window(self, window_name: str) -> QWidget:
        """
        Get a registered window.
        
        Args:
            window_name: Name of the window to retrieve
            
        Returns:
            Qt window/widget instance
        """
        if window_name not in self.windows:
            raise ValueError(f"Window '{window_name}' not registered")
            
        return self.windows[window_name]

    def run_application_with_main_window(self, main_window: QWidget,
                                       window_name: str = "main") -> int:
        """
        Run the application with a main window.
        
        Args:
            main_window: Main window instance
            window_name: Name to register the main window with
            
        Returns:
            Application exit code
        """
        self.register_window(window_name, main_window)
        self.set_main_window(main_window)
        return self.start_application()

    def get_registered_windows(self) -> Dict[str, str]:
        """
        Get information about registered windows.
        
        Returns:
            Dictionary mapping window names to their class names
        """
        return {name: window.__class__.__name__ for name, window in self.windows.items()}