# 🏗️ Web Controller Architecture Pattern - CLAUDE.md

## 📋 Overview

This document establishes the architectural pattern for Flask web controllers in the base_infrastructure project, specifically addressing the **Web Controllers → API Controllers** pattern to eliminate conflicting logic and maintain separation of concerns.

---

## 🎯 Core Principle: Web Controllers Call API Controllers

### ✅ CORRECT Pattern
```
User Interface → Web Controller → API Controller → Business Logic
```

### ❌ INCORRECT Pattern 
```
User Interface → Web Controller → Business Logic (Direct)
```

---

## 🔧 Implementation Guidelines

### 1. **Web Controllers** (`src/interfaces/flask/web/controllers/`)
**Purpose**: Handle HTML rendering, user interface interactions, and form processing
**Responsibilities**:
- Render Jinja2 templates
- Process form data and URL parameters
- Handle user authentication/sessions
- Provide user-friendly error messages
- Manage redirects and flash messages

```python
@web_bp.route("/dashboard/backtest", methods=["GET", "POST"])
def backtest_interface():
    if request.method == "GET":
        # Show configuration form
        return render_template("backtest_config.html")
    
    # Process form data and call API controller
    config = {
        'algorithm': request.form.get('algorithm'),
        'lookback': request.form.get('lookback'),
        # ... other form fields
    }
    
    # Call API controller (not business logic directly)
    api_response = requests.post('/api/test_managers/backtest', json=config)
    
    if api_response.status_code == 200:
        flash("Backtest completed successfully!", "success")
        return redirect(url_for('web.backtest_results'))
    else:
        flash(f"Backtest failed: {api_response.json().get('error')}", "error")
        return render_template("backtest_config.html", config=config)
```

### 2. **API Controllers** (`src/interfaces/flask/api/controllers/`)
**Purpose**: Handle JSON API requests and responses
**Responsibilities**:
- Validate JSON input parameters
- Call appropriate business logic/managers
- Return structured JSON responses
- Handle API-specific error codes
- Provide machine-readable responses

```python
@api_bp.route("/test_managers/backtest", methods=["POST"])
def execute_backtest():
    try:
        data = request.json
        
        # Validate input
        if not data or 'algorithm' not in data:
            return jsonify({"success": False, "error": "Missing algorithm parameter"}), 400
        
        # Call business logic
        from src.application.managers.project_managers.test_project_backtest.test_project_backtest_manager import TestProjectBacktestManager
        manager = TestProjectBacktestManager()
        result = manager.run_with_config(data)
        
        return jsonify({
            "success": True,
            "result": result,
            "message": "Backtest completed successfully"
        })
        
    except Exception as e:
        logger.error(f"Backtest execution failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
```

---

## 🚫 Flask App Instantiation Rules

### Issue Resolution
**Problem**: Multiple Flask app instances on same localhost port cause conflicts
- `main.py:36` creates `FlaskApp()` 
- `web_interface.py:59` creates `FlaskApp()`  

### Solution Pattern
1. **Primary Flask App**: Created in `main.py` or main entry point
2. **Secondary Services**: Accept existing Flask app instance via dependency injection

```python
# ✅ CORRECT: WebInterfaceManager accepts existing Flask app
class WebInterfaceManager:
    def start_interface_and_open_browser(self, existing_flask_app=None):
        if existing_flask_app is not None:
            self.flask_app = existing_flask_app  # Use existing
        else:
            self.flask_app = FlaskApp()  # Create new only if needed

# ✅ CORRECT: Usage in main.py
app = FlaskApp()  # Primary Flask app
web_manager = WebInterfaceManager()
web_manager.start_interface_and_open_browser(existing_flask_app=app)
```

---

## 🎮 User Interface Patterns

### Configuration-First Approach
**Rule**: Never auto-start simulations. Always show configuration UI first.

#### ❌ BEFORE (Auto-start)
```javascript
function runBacktest() {
    // Immediately redirects to execution
    window.location.href = '/test_backtest';
}
```

#### ✅ AFTER (Configuration-first)
```javascript
function runBacktest() {
    // Shows configuration modal first
    showBacktestConfigModal();
}

function showBacktestConfigModal() {
    // Display modal with:
    // - Algorithm selection
    // - Stock universe selection  
    // - Date range picker
    // - Risk factor checkboxes
    // - Portfolio settings
    // - Confirmation buttons
}
```

---

## 📂 Project Structure

```
src/interfaces/flask/
├── flask.py                    # Main Flask app factory
├── web/                        # HTML interface layer
│   ├── controllers/
│   │   └── dashboard_controller.py  # Web controllers (call API)
│   └── templates/
│       └── dashboard_hub.html      # UI templates
└── api/                        # JSON API layer  
    ├── controllers/
    │   └── backtest_controller.py   # API controllers (call business logic)
    └── routes/
```

---

## 🔄 Migration Strategy

### Step 1: Identify Conflicting Logic
- [x] Find duplicate Flask app instantiations
- [x] Locate web controllers calling business logic directly
- [x] Identify missing API endpoints

### Step 2: Apply Pattern
- [x] Modify web controllers to call API endpoints
- [x] Ensure API controllers handle business logic
- [x] Add configuration modals for user interactions
- [x] Fix Flask app dependency injection

### Step 3: Validate
- [ ] Test all web UI flows
- [ ] Verify API endpoints work independently  
- [ ] Confirm no port conflicts
- [ ] Check error handling on both layers

---

## 🧪 Testing Guidelines

### Web Controller Tests
- Test template rendering
- Test form processing 
- Test redirects and flash messages
- Mock API controller calls

### API Controller Tests  
- Test JSON input/output
- Test business logic integration
- Test error handling
- Test HTTP status codes

---

## 📋 Checklist for New Features

When adding new functionality:

- [ ] Create API endpoint first (`/api/feature/action`)
- [ ] Implement web controller that calls API endpoint
- [ ] Add configuration UI (modal/form) - no auto-start
- [ ] Test both API and web interfaces independently
- [ ] Document endpoints in this file
- [ ] Ensure no duplicate Flask app creation

---

## 🎯 Benefits of This Pattern

1. **Separation of Concerns**: Web UI and API logic are decoupled
2. **Reusability**: API endpoints can be used by web UI, mobile apps, or external systems
3. **Testability**: Each layer can be tested independently
4. **Maintainability**: Business logic changes don't affect UI layer
5. **Scalability**: Can easily add new interfaces (CLI, mobile) without duplicating logic
6. **Configuration-First**: Better UX with proper configuration management

---

## 🚀 Next Steps

1. Apply this pattern to remaining controllers
2. Add comprehensive error handling on both layers  
3. Implement proper API documentation (OpenAPI/Swagger)
4. Add authentication/authorization layers
5. Consider implementing API versioning (`/api/v1/`)

---

*Generated for Issue #124 - UI improvements and Flask app conflict resolution*