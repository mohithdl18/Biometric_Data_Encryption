# 🔐 Biometric Authentication System - Installation Guide

Complete installation guide for the Face and Fingerprint Registration System with R307 sensor integration.

## 📋 Table of Contents
- [Prerequisites](#prerequisites)
- [Hardware Requirements](#hardware-requirements)
- [Software Installation](#software-installation)
- [Project Setup](#project-setup)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [Hardware Configuration](#hardware-configuration)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## 🛠️ Prerequisites

### System Requirements
- **Operating System**: Windows 10/11 (tested), Linux, macOS
- **Python**: 3.8 or higher (Python 3.13+ recommended)
- **Node.js**: 16.0 or higher
- **npm**: 8.0 or higher
- **Memory**: Minimum 4GB RAM
- **Storage**: At least 2GB free space

### Hardware Requirements
- **Webcam**: Built-in or USB camera for face capture
- **R307 Fingerprint Sensor**: Connected via USB-to-Serial adapter
- **USB Port**: Available COM port (typically COM3)

---

## 💾 Software Installation

### 1. Install Python
```powershell
# Download from https://python.org/downloads/
# Ensure "Add Python to PATH" is checked during installation

# Verify installation
python --version
pip --version
```

### 2. Install Node.js and npm
```powershell
# Download from https://nodejs.org/
# This installs both Node.js and npm

# Verify installation
node --version
npm --version
```

### 3. Install Git (Optional but recommended)
```powershell
# Download from https://git-scm.com/downloads
git --version
```

---

## 🚀 Project Setup

### 1. Navigate to Project Directory
```powershell
# Open PowerShell as Administrator (recommended)
cd "D:\patil\New folder"
```

### 2. Create Python Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# You should see (.venv) prefix in your terminal
```

**Note**: If you get execution policy error, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 🔧 Backend Setup

### 1. Navigate to Backend Directory
```powershell
cd backend
```

### 2. Install Python Dependencies
```powershell
# Make sure virtual environment is activated
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt

# Verify critical packages
pip list | findstr Flask
pip list | findstr opencv
pip list | findstr pyserial
```

### 3. Test Backend Components
```powershell
# Test face capture module
cd face\capture
python face_capture.py

# Test fingerprint capture module
cd ..\..\finger\capture
python finger_capture.py

# Test fingerprint matching module  
cd ..\match
python finger_match.py

# Return to backend root
cd ..\..
```

---

## 🎨 Frontend Setup

### 1. Navigate to Frontend Directory
```powershell
# From project root
cd frontend
```

### 2. Install Node.js Dependencies
```powershell
# Install all required packages
npm install

# Verify installation
npm list --depth=0
```

### 3. Verify Frontend Dependencies
Key packages that should be installed:
- `react`: ^18.0.0
- `vite`: ^5.0.0
- `tailwindcss`: ^3.0.0
- `postcss`: ^8.0.0
- `autoprefixer`: ^10.0.0

---

## 🔌 Hardware Configuration

### 1. R307 Fingerprint Sensor Setup
1. **Connect Hardware**:
   - Connect R307 sensor to USB-to-Serial adapter
   - Plug adapter into computer USB port
   - Note the COM port number (usually COM3)

2. **Verify Connection**:
```powershell
# Check available COM ports
Get-WmiObject -Class Win32_SerialPort | Select-Object Name,DeviceID

# Or using Device Manager:
# Windows Key + X → Device Manager → Ports (COM & LPT)
```

3. **Test Sensor Communication**:
```powershell
# From project root, activate venv and test
.\.venv\Scripts\Activate.ps1
cd backend\finger\capture
python finger_capture.py
```

### 2. Camera Setup
- Ensure webcam is connected and working
- Test with Windows Camera app
- Grant camera permissions to browsers

---

## 🏃‍♂️ Running the Application

### 1. Start Backend Server
```powershell
# Open first PowerShell terminal
cd "D:\patil\New folder"
.\.venv\Scripts\Activate.ps1
cd backend
python app.py
```

**Expected Output**:
```
=== Face Registration API Server ===
Server starting on http://localhost:5000
Health check: http://localhost:5000/api/health
* Running on http://127.0.0.1:5000
```

### 2. Start Frontend Development Server
```powershell
# Open second PowerShell terminal
cd "D:\patil\New folder\frontend"
npm run dev
```

**Expected Output**:
```
  VITE v5.x.x ready in xxx ms
  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

### 3. Access Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:5000
- **Health Check**: http://localhost:5000/api/health

---

## 🧪 Testing

### 1. Test Backend API Endpoints
```powershell
# Test health check
curl http://localhost:5000/api/health

# Test user registration
curl -X POST http://localhost:5000/api/register -H "Content-Type: application/json" -d "{\"name\":\"TestUser\",\"email\":\"test@email.com\"}"

# Test registered users list
curl http://localhost:5000/api/users
```

### 2. Test Hardware Components
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Test R307 sensor (from backend directory)
cd backend\finger\capture
python finger_capture.py

# Test face capture
cd ..\face\capture  
python face_capture.py
```

### 3. Test Complete Workflow
1. Open http://localhost:5173
2. Click "Register" button
3. Fill registration form
4. Complete face capture (5 photos)
5. Complete fingerprint capture
6. Go back and click "Login"
7. Select your registered name
8. Test fingerprint authentication

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. Python Virtual Environment Issues
```powershell
# If activation fails
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# If packages not found
pip install --upgrade pip
pip install -r backend\requirements.txt --force-reinstall
```

#### 2. R307 Sensor Connection Issues
```powershell
# Check COM port
Get-WmiObject -Class Win32_SerialPort

# Test with different COM ports
# Edit finger_capture.py and change port='COM3' to your actual port
```

#### 3. Camera Access Issues
- Check Windows camera privacy settings
- Ensure browser has camera permissions
- Test camera with Windows Camera app
- Try different browsers (Chrome recommended)

#### 4. Flask Server Issues
```powershell
# If port 5000 is in use
netstat -ano | findstr :5000
# Kill process using the port or change port in app.py
```

#### 5. npm Installation Issues
```powershell
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules
rm package-lock.json
npm install
```

#### 6. Import Module Errors
```powershell
# Ensure you're in the correct directory and virtual environment is activated
cd "D:\patil\New folder"
.\.venv\Scripts\Activate.ps1

# Check Python path
python -c "import sys; print(sys.path)"
```

### Debug Mode
Enable debug logging by setting environment variables:
```powershell
# Enable Flask debug mode
$env:FLASK_DEBUG = "1"

# Enable verbose logging
$env:PYTHONPATH = "D:\patil\New folder\backend"
```

---

## 📁 Project Structure
```
New folder/
├── installation.md          # This file
├── .venv/                  # Python virtual environment
├── backend/                # Flask API server
│   ├── app.py             # Main Flask application
│   ├── requirements.txt   # Python dependencies
│   ├── face/
│   │   └── capture/       # Face capture module
│   └── finger/
│       ├── capture/       # Fingerprint capture module
│       └── match/         # Fingerprint matching module
├── frontend/              # React application
│   ├── package.json       # Node.js dependencies
│   ├── src/
│   │   ├── App.jsx        # Main React component
│   │   └── pages/         # React pages
└── dataset/               # User data storage
    └── face/              # User folders with biometric data
```

---

## 🎯 Quick Start Commands

### Complete Setup (Run these in order):
```powershell
# 1. Setup Python environment
cd "D:\patil\New folder"
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install backend dependencies
cd backend
pip install -r requirements.txt

# 3. Install frontend dependencies
cd ..\frontend
npm install

# 4. Start backend (Terminal 1)
cd ..\backend
.\.venv\Scripts\Activate.ps1
python app.py

# 5. Start frontend (Terminal 2)
cd frontend
npm run dev
```

### Daily Development Commands:
```powershell
# Terminal 1 - Backend
cd "D:\patil\New folder"
.\.venv\Scripts\Activate.ps1
cd backend
python app.py

# Terminal 2 - Frontend  
cd "D:\patil\New folder\frontend"
npm run dev
```

---

## 📞 Support
If you encounter issues not covered in this guide:
1. Check all hardware connections
2. Verify all dependencies are installed
3. Ensure virtual environment is activated
4. Check Windows Device Manager for hardware issues
5. Review console logs for error messages

---

**✅ Installation Complete!** 
Your biometric authentication system should now be running at:
- Frontend: http://localhost:5173
- Backend: http://localhost:5000
