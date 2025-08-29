#!/usr/bin/env python3
"""
Simple HTTP server for serving UI files.
Serves static files from the current directory.
"""

import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import argparse
from pathlib import Path


class UIRequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler for UI files."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)
    
    def end_headers(self):
        # Add CORS headers for development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()


def main():
    parser = argparse.ArgumentParser(description="Simple UI Server")
    parser.add_argument("--port", "-p", type=int, default=3000, 
                       help="Port to serve on (default: 3000)")
    parser.add_argument("--host", default="localhost", 
                       help="Host to bind to (default: localhost)")
    
    args = parser.parse_args()
    
    # Change to the ui directory
    ui_dir = Path(__file__).parent
    os.chdir(ui_dir)
    
    # Create server
    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, UIRequestHandler)
    
    print(f"🚀 UI Server running on http://{args.host}:{args.port}")
    print(f"📁 Serving files from: {ui_dir.absolute()}")
    print("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped")
        httpd.server_close()


if __name__ == "__main__":
    main()