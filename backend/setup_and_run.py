# Face Registration Backend Setup and Run Script
# This script helps set up the Python environment and run the backend server

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def setup_backend():
    """Set up the backend environment"""
    print("🚀 Face Registration Backend Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Check if virtual environment exists
    venv_path = Path("../.venv")
    if not venv_path.exists():
        print("⚠️  Virtual environment not found!")
        print("Please run the following commands first:")
        print("1. cd 'D:\\patil\\New folder'")
        print("2. python -m venv .venv")
        print("3. .venv\\Scripts\\activate")
        return False
    
    # Install requirements
    pip_path = venv_path / "Scripts" / "pip.exe"
    install_cmd = f'"{pip_path}" install -r requirements.txt'
    
    if not run_command(install_cmd, "Installing required packages"):
        return False
    
    print("\n🎉 Backend setup completed successfully!")
    print("\nTo run the backend server:")
    print("1. Make sure you're in the backend directory")
    print("2. Run: python setup_and_run.py --run")
    print("   OR: python app.py")
    
    return True

def run_backend():
    """Run the backend server"""
    print("🚀 Starting Face Registration Backend Server")
    print("=" * 50)
    
    # Check if virtual environment exists
    venv_path = Path("../.venv")
    if not venv_path.exists():
        print("❌ Virtual environment not found! Run setup first.")
        return False
    
    # Run the Flask app
    python_path = venv_path / "Scripts" / "python.exe"
    run_cmd = f'"{python_path}" app.py'
    
    print("🌐 Starting Flask server on http://localhost:5000")
    print("📋 API Endpoints:")
    print("   • Health Check: GET  /api/health")
    print("   • Register User: POST /api/register")
    print("   • Check Status:  GET  /api/status/{username}")
    print("\n🔥 Server starting... Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        subprocess.run(run_cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Server failed to start: {e}")

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        run_backend()
    else:
        if setup_backend():
            choice = input("\n🤔 Do you want to start the server now? (y/n): ").lower()
            if choice in ['y', 'yes']:
                run_backend()

if __name__ == "__main__":
    main()
