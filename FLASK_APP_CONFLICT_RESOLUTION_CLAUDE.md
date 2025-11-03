# Flask App Conflict Resolution - CLAUDE.md

## Issue Summary
The Flask app conflict was occurring because:
1. `main.py` starts Flask on localhost:5000
2. API endpoints create manager instances that also try to start Flask on localhost:5000
3. Result: "Address already in use" error

## Root Cause Analysis
- User observation: No place in code calls `start_interface_and_open_browser(existing_flask_app=app)`
- The dependency injection approach was implemented but never utilized
- Managers always called `start_interface_and_open_browser()` without parameters
- This caused duplicate Flask app creation on the same port

## Solution Implemented

### 1. Manager Run Method Enhancement
Modified `TestProjectBacktestManager.run()` to accept optional parameter:
```python
def run(self, start_web_interface=True):
    """Main run method that launches web interface and executes backtest
    
    Args:
        start_web_interface (bool): Whether to start web interface (default: True)
                                   Set to False when called from existing web API
    """
    if start_web_interface:
        # Start web interface and open browser
        self.web_interface.start_interface_and_open_browser()
    
    # Start the actual backtest
    return self._run_backtest()
```

### 2. API Endpoint Fix
Modified dashboard controller to prevent duplicate Flask instances:
```python
# Execute actual backtest manager with configuration
manager = TestProjectBacktestManager()
result = manager.run(start_web_interface=False)  # Don't start another web interface
```

### 3. Code Cleanup
- Removed unused dependency injection code from `WebInterfaceManager`
- Simplified `start_interface_and_open_browser()` method
- Removed `existing_flask_app` parameter that was never used

## Benefits
1. **No Port Conflicts**: Only one Flask app runs on localhost:5000
2. **Clean Architecture**: API endpoints don't create redundant web interfaces
3. **Backward Compatibility**: Standalone manager execution still works
4. **Simplified Code**: Removed unnecessary complexity

## Usage Patterns

### Standalone Manager Execution
```python
manager = TestProjectBacktestManager()
manager.run()  # Starts web interface by default
```

### API Endpoint Execution (within existing Flask app)
```python
manager = TestProjectBacktestManager()
manager.run(start_web_interface=False)  # Uses existing Flask app
```

## File Changes Made
- `src/application/managers/project_managers/test_project_backtest/test_project_backtest_manager.py`
- `src/interfaces/flask/web/controllers/dashboard_controller.py`
- `src/application/services/misbuffet/web/web_interface.py`

## Testing
After this fix, users can:
1. Run `python -m src.main` to start web-only interface
2. Use dashboard buttons to execute backtests without Flask conflicts
3. Managers execute properly without attempting duplicate Flask creation

## Architecture Pattern
**Web Controllers → API Controllers → Business Logic (without web interface startup)**

This maintains separation of concerns while preventing Flask app conflicts.