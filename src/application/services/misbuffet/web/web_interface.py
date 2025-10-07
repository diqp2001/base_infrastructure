"""
Web interface utilities for Misbuffet backtesting.
Contains progress logging, Flask web interface, and browser automation functions.
"""

import time
import logging
import webbrowser
import threading
import queue
from datetime import datetime


class WebInterfaceManager:
    """Manages web interface components for backtesting progress monitoring."""
    
    def __init__(self):
        self.flask_app = None
        self.flask_thread = None
        self.progress_queue = queue.Queue()
        self.is_running = False
        
        # Set up shared progress handler
        self._setup_progress_logging()

    def _setup_progress_logging(self):
        """Set up logging handler to capture progress messages"""
        # Create custom handler that puts messages in queue
        class ProgressHandler(logging.Handler):
            def __init__(self, progress_queue):
                super().__init__()
                self.progress_queue = progress_queue
                
            def emit(self, record):
                message = self.format(record)
                self.progress_queue.put({
                    'timestamp': datetime.now().isoformat(),
                    'level': record.levelname,
                    'message': message
                })
        
        # Add handler to capture all misbuffet logs
        progress_handler = ProgressHandler(self.progress_queue)
        progress_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # Add to main loggers
        logging.getLogger("misbuffet-main").addHandler(progress_handler)
        logging.getLogger("misbuffet.engine").addHandler(progress_handler)
        logging.getLogger("TestProjectBacktestManager").addHandler(progress_handler)
    
    def _start_web_interface(self):
        """Start Flask web interface in a separate thread"""
        from src.interfaces.flask.flask import FlaskApp
        from flask import Flask, render_template, request, Response, jsonify
        import json
        
        # Create Flask app instance
        self.flask_app = FlaskApp()
        
        # Add progress streaming endpoint
        def generate_progress():
            """Server-Sent Events generator for progress updates"""
            try:
                while True:
                    try:
                        # Wait for new message with timeout
                        message = self.progress_queue.get(timeout=1)
                        yield f"data: {json.dumps(message)}\n\n"
                    except queue.Empty:
                        # Send heartbeat to keep connection alive
                        yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
            except GeneratorExit:
                # Client disconnected, clean exit
                print("🔌 Client disconnected from progress stream")
                return
            except Exception as e:
                print(f"❌ Error in progress stream: {e}")
                return
        
        @self.flask_app.app.route('/progress_stream')
        def progress_stream():
            """Server-Sent Events endpoint for progress updates"""
            return Response(generate_progress(), mimetype='text/event-stream', headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*'
            })
        
        # Add backtest progress page
        @self.flask_app.app.route('/backtest_progress')
        def backtest_progress():
            """Display backtest progress with real-time updates"""
            return render_template('backtest_progress.html')
        
        # Add shutdown endpoint for clean server shutdown
        @self.flask_app.app.route('/shutdown', methods=['POST'])
        def shutdown_server():
            """Shutdown the Flask server gracefully"""
            print("🛑 Shutdown request received")
            self.is_running = False
            # Use Werkzeug's shutdown function
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                return 'Server shutdown failed - not running with Werkzeug server', 500
            func()
            return 'Server shutting down...', 200
        
        # Start Flask in separate thread
        def run_flask():
            try:
                self.flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                print(f"❌ Flask server error: {e}")
            finally:
                print("🛑 Flask server stopped")
        
        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()
        
        self.is_running = True
        print("🌐 Flask web interface started at http://localhost:5000")
        print("📊 Progress monitor available at http://localhost:5000/backtest_progress")
    
    def _open_browser(self):
        """Automatically open browser to progress page"""
        try:
            webbrowser.open('http://localhost:5000/backtest_progress')
            webbrowser.open('http://localhost:5000/')
            print("🖥️  Browser opened automatically to backtest progress page")
        except Exception as e:
            print(f"⚠️  Could not open browser automatically: {e}")
            print("📍 Please manually navigate to: http://localhost:5000/backtest_progress")
    
    def start_interface_and_open_browser(self):
        """Start web interface and open browser"""
        # Start Flask web interface first
        self._start_web_interface()
        
        # Give Flask a moment to start
        time.sleep(5)
        
        # Open browser automatically
        self._open_browser()

        # Give Flask a moment to start
        time.sleep(5)