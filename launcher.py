#!/usr/bin/env python3
"""
AI Quiz Generator - Auto Launcher with Browser
Automatically starts server and opens browser
"""

import subprocess
import time
import webbrowser
import threading
import sys
import os

def open_browser_when_ready():
    """Open browser after server is ready"""
    print("🔍 Waiting for server to start...")
    time.sleep(3)  # Wait for server startup
    
    try:
        print("🌐 Opening browser at http://localhost:8000")
        webbrowser.open('http://localhost:8000')
        print("✅ Browser opened successfully!")
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print("📝 Please open browser manually: http://localhost:8000")

def check_dependencies():
    """Check and install required dependencies"""
    try:
        import fastapi
        import uvicorn
        print("✅ Dependencies already installed")
        return True
    except ImportError:
        print("📦 Installing required dependencies...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print("✅ Dependencies installed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False

def start_backend_server():
    """Start the FastAPI backend server"""
    try:
        print("🚀 Starting AI Quiz Generator Backend Server...")
        
        # Start uvicorn server
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "main:app", 
            "--host", "localhost", 
            "--port", "8000", 
            "--reload"
        ])
        
        print("✅ Backend server started successfully!")
        print("🌐 Server running at: http://localhost:8000")
        return process
        
    except Exception as e:
        print(f"❌ Failed to start backend server: {e}")
        return None

def main():
    """Main launcher function"""
    print("🎯 AI Quiz Generator - Auto Launcher")
    print("=" * 50)
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"📁 Working directory: {script_dir}")
    
    # Check dependencies first
    if not check_dependencies():
        print("❌ Cannot start without required dependencies")
        return
    
    # Start backend server
    server_process = start_backend_server()
    
    if server_process is None:
        print("❌ Failed to start backend server")
        return
    
    # Start browser opener in background
    browser_thread = threading.Thread(target=open_browser_when_ready)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        print("🎮 AI Quiz Generator is now running!")
        print("📝 Press Ctrl+C to stop the server")
        print("-" * 50)
        
        # Wait for server process
        server_process.wait()
        
    except KeyboardInterrupt:
        print("\n👋 Stopping AI Quiz Generator...")
        server_process.terminate()
        print("✅ Server stopped successfully!")
    except Exception as e:
        print(f"❌ Server error: {e}")
        print("💡 Try running: python -m uvicorn main:app --host localhost --port 8000")

if __name__ == "__main__":
    main()