# Face Registration Backend

This is the backend API server for the Face Registration System. It handles user registration, face capture, and stores user data with facial images.

## 🚀 Quick Start

### Option 1: Using the Setup Script (Recommended)
```bash
cd backend
python setup_and_run.py
```

### Option 2: Using Batch File (Windows)
```bash
cd backend
start_backend.bat
```

### Option 3: Manual Setup
```bash
# 1. Navigate to project root
cd "D:\patil\New folder"

# 2. Activate virtual environment
.venv\Scripts\activate

# 3. Install requirements
cd backend
pip install -r requirements.txt

# 4. Run the server
python app.py
```

## 📦 Requirements

### Core Dependencies
- **Flask 3.1.2** - Web framework for API endpoints
- **flask-cors 6.0.1** - Cross-Origin Resource Sharing support
- **opencv-python 4.12.0.88** - Computer vision and face detection
- **numpy 2.2.6** - Numerical computing support

### System Requirements
- Python 3.13+ 
- Webcam/Camera access
- Windows/Linux/MacOS

## 🌐 API Endpoints

### Health Check
```http
GET /api/health
```
**Response:**
```json
{
  "status": "healthy",
  "message": "Face registration API is running"
}
```

### Register User
```http
POST /api/register
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com", 
  "phone": "+1234567890"
}
```

**Response:**
```json
{
  "message": "Face capture started for John Doe",
  "user_name": "John Doe", 
  "status": "started"
}
```

### Check Registration Status
```http
GET /api/status/{username}
```

**Response:**
```json
{
  "status": "capturing",
  "photos_captured": 3,
  "total_photos": 5,
  "message": "Captured photo 3/5...",
  "completed": false,
  "error": null
}
```

## 📁 File Structure

```
backend/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── setup_and_run.py      # Setup and run script
├── start_backend.bat     # Windows batch file
├── README.md             # This file
└── face/
    └── capture/
        └── face_capture.py # Face detection and capture logic
```

## 🔧 Configuration

### Camera Settings
The system uses the default camera (index 0). To use a different camera:

```python
# In face_capture.py, modify:
cap = cv2.VideoCapture(0)  # Change 0 to your camera index
```

### Storage Location
Face images are stored in:
```
../dataset/face/{username}/
├── face_001.jpg
├── face_002.jpg  
├── face_003.jpg
├── face_004.jpg
├── face_005.jpg
└── user_info.txt
```

## 🐛 Troubleshooting

### Common Issues

**1. ModuleNotFoundError: No module named 'flask'**
```bash
# Solution: Install requirements
pip install -r requirements.txt
```

**2. Camera not opening**
```bash
# Check if camera is being used by another app
# Try different camera index (0, 1, 2...)
```

**3. CORS errors from frontend**
```bash
# Make sure flask-cors is installed
pip install flask-cors
```

**4. Permission denied errors**
```bash
# Run with administrator privileges on Windows
# Or check file/folder permissions
```

### Debug Mode
The server runs in debug mode by default. To disable:

```python
# In app.py, change:
app.run(debug=False, host='0.0.0.0', port=5000)
```

## 🔒 Security Notes

- This is a development server, not suitable for production
- No authentication/authorization implemented
- CORS is enabled for all origins
- Face data is stored locally without encryption

## 🚦 Status Codes

- **200** - Success
- **400** - Bad Request (missing/invalid data)
- **404** - User not found
- **409** - Conflict (user already exists)  
- **500** - Internal Server Error

## 📈 Development

### Adding New Features
1. Add new routes in `app.py`
2. Update face capture logic in `face/capture/face_capture.py`
3. Test with frontend integration
4. Update requirements.txt if new packages needed

### Testing
```bash
# Test health endpoint
curl http://localhost:5000/api/health

# Test registration
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"name":"TestUser","email":"test@example.com","phone":"123456"}'
```

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review terminal output for error messages
3. Ensure all requirements are installed
4. Verify camera access permissions
