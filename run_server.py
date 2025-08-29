#!/usr/bin/env python3
"""
Kuber AI Voice Multi-Service Launcher

This script starts all services: app, ui, and custom_models from a single entry point.
"""

import argparse
import uvicorn
import sys
import os
import subprocess
import threading
import time
import signal
from pathlib import Path


# Add the project root and app directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "app"))


class ServiceManager:
    """Manages multiple services (app, ui, custom_models)."""
    
    def __init__(self):
        self.processes = []
        self.running = True
    
    def start_service(self, name, command, cwd=None, port=None):
        """Start a service in a separate process."""
        try:
            print(f"🚀 Starting {name} service...")
            if port:
                print(f"   └─ Port: {port}")
            if cwd:
                print(f"   └─ Directory: {cwd}")
            
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes.append((name, process))
            
            # Start a thread to handle output
            def handle_output():
                for line in iter(process.stdout.readline, ''):
                    if self.running:
                        print(f"[{name}] {line.strip()}")
                process.stdout.close()
            
            thread = threading.Thread(target=handle_output, daemon=True)
            thread.start()
            
            return process
            
        except Exception as e:
            print(f"❌ Failed to start {name}: {e}")
            return None
    
    def stop_all(self):
        """Stop all running services."""
        print("\n🛑 Stopping all services...")
        self.running = False
        
        for name, process in self.processes:
            try:
                print(f"   └─ Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"   └─ Force killing {name}...")
                process.kill()
            except Exception as e:
                print(f"   └─ Error stopping {name}: {e}")
        
        print("✅ All services stopped")


def check_service_exists(service_path):
    """Check if a service directory and main.py exists."""
    main_py = Path(service_path) / "main.py"
    return main_py.exists()


def main():
    # Load environment variables first
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Loaded environment variables from .env file")
    except ImportError:
        print("⚠️ python-dotenv not available, skipping .env loading")
    
    parser = argparse.ArgumentParser(description="Run all Kuber AI Voice services")
    parser.add_argument("--config", default="config.yaml", help="Config file to use")
    parser.add_argument("--host", default=None, help="Host to bind to")
    parser.add_argument("--port", type=int, default=None, help="Port to bind to")
    parser.add_argument("--minimal", action="store_true", help="Use minimal config with mock adapters")
    
    # Service control arguments
    parser.add_argument("--app-only", action="store_true", help="Start only the main app service")
    parser.add_argument("--ui-only", action="store_true", help="Start only the UI service")
    parser.add_argument("--models-only", action="store_true", help="Start only the custom models service")
    parser.add_argument("--no-ui", action="store_true", help="Skip UI service")
    parser.add_argument("--no-models", action="store_true", help="Skip custom models service")
    
    # Port configuration
    parser.add_argument("--ui-port", type=int, default=3000, help="UI server port")
    parser.add_argument("--models-port", type=int, default=8001, help="Custom models port")
    
    args = parser.parse_args()
    
    # Use minimal config if requested
    if args.minimal:
        args.config = "config-minimal.yaml"
        print("🔧 Using minimal configuration with mock adapters")
    
    # Set config file path (ensure it points to app/config.yaml)
    if not os.path.isabs(args.config):
        config_path = os.path.join("app", args.config)
    else:
        config_path = args.config
    os.environ['CONFIG_FILE'] = config_path
    
    # Initialize service manager
    service_manager = ServiceManager()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        service_manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Determine which services to start
        start_app = not (args.ui_only or args.models_only)
        start_ui = not (args.app_only or args.models_only or args.no_ui)
        start_models = not (args.app_only or args.ui_only or args.no_models)
        
        print("🎯 Kuber AI Voice - Multi-Service Launcher")
        print("=" * 50)
        
        # Start custom models service
        if start_models and check_service_exists("custom_models"):
            service_manager.start_service(
                "custom_models",
                [sys.executable, "main.py", "--port", str(args.models_port)],
                cwd="custom_models",
                port=args.models_port
            )
            time.sleep(2)  # Give it time to start
        elif start_models:
            print("⚠️  custom_models/main.py not found, skipping custom models service")
        
        # Start UI service
        if start_ui and check_service_exists("ui"):
            service_manager.start_service(
                "ui",
                [sys.executable, "main.py", "--port", str(args.ui_port)],
                cwd="ui",
                port=args.ui_port
            )
            time.sleep(1)  # Give it time to start
        elif start_ui:
            print("⚠️  ui/main.py not found, skipping UI service")
        
        # Start main app service
        if start_app:
            # Change to root directory before importing
            os.chdir(project_root)
            
            from config import config
            
            # Use command line args or fall back to config
            host = args.host or config.server.host
            port = args.port or config.server.port
            
            print(f"🚀 Starting main app service on {host}:{port}")
            print(f"📋 Using config: {args.config}")
            print(f"🔧 Log level: {config.server.log_level}")
            
            # Import the FastAPI app
            from app.main import app
            
            # Start the main server (this will block)
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level=config.server.log_level.lower(),
                reload=False,
                access_log=True
            )
        else:
            # If not starting the main app, just wait for other services
            print("📡 Services running. Press Ctrl+C to stop all services.")
            try:
                while service_manager.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        service_manager.stop_all()


if __name__ == "__main__":
    main()