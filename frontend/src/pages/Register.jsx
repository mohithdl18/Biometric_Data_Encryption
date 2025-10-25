import { useState, useRef, useEffect } from 'react'

function Register() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: ''
  })
  const [step, setStep] = useState(1) // 1: Form, 2: Face Capture Instructions, 3: Live Capture, 4: Fingerprint Capture
  const [isRegistering, setIsRegistering] = useState(false)
  const [captureStatus, setCaptureStatus] = useState({
    message: '',
    photos_captured: 0,
    total_photos: 5
  })
  const [stream, setStream] = useState(null)
  const [isCapturing, setIsCapturing] = useState(false)
  const [fingerprintStatus, setFingerprintStatus] = useState({
    message: '',
    isCapturing: false,
    completed: false
  })
  const videoRef = useRef(null)
  const canvasRef = useRef(null)

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleFormSubmit = (e) => {
    e.preventDefault()
    if (formData.name.trim() && formData.email.trim() && formData.phone.trim()) {
      setStep(2)
    } else {
      alert('Please fill in all fields')
    }
  }

  const handleStartFaceCapture = async () => {
    try {
      // Request camera access
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 } 
      })
      setStream(mediaStream)
      setStep(3) // Move to live capture step
      
      // Initialize backend session
      const response = await fetch('http://localhost:5000/api/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          phone: formData.phone
        })
      })
      
      const result = await response.json()
      if (!response.ok) {
        alert(`Error: ${result.error}`)
        stopCamera()
      }
      
    } catch (error) {
      if (error.name === 'NotAllowedError') {
        alert('Camera access denied. Please allow camera access and try again.')
      } else {
        alert(`Camera error: ${error.message}`)
      }
    }
  }

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
  }

  const capturePhoto = async () => {
    if (!videoRef.current || !canvasRef.current) return
    
    setIsCapturing(true)
    
    try {
      // Draw current video frame to canvas
      const video = videoRef.current
      const canvas = canvasRef.current
      const context = canvas.getContext('2d')
      
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      context.drawImage(video, 0, 0)
      
      // Convert canvas to blob
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8))
      
      // Send to backend
      const uploadData = new FormData()
      const photoNumber = String(captureStatus.photos_captured + 1).padStart(3, '0')
      uploadData.append('photo', blob, `face_${photoNumber}.jpg`)
      uploadData.append('user_name', formData.name)
      
      const response = await fetch('http://localhost:5000/api/capture', {
        method: 'POST',
        body: uploadData
      })
      
      const result = await response.json()
      
      if (response.ok) {
        setCaptureStatus(prev => ({
          ...prev,
          photos_captured: prev.photos_captured + 1,
          message: `Photo ${prev.photos_captured + 1}/5 captured successfully!`
        }))
        
        // Check if we're done with face capture
        if (captureStatus.photos_captured + 1 >= 5) {
          stopCamera()
          setIsRegistering(false)
          // Move to fingerprint capture step
          setStep(4)
        }
      } else {
        alert(`Capture failed: ${result.error}`)
      }
      
    } catch (error) {
      alert(`Capture error: ${error.message}`)
    } finally {
      setIsCapturing(false)
    }
  }

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream
    }
  }, [stream])

  const captureFingerprint = async () => {
    setFingerprintStatus({
      message: 'Initializing fingerprint sensor...',
      isCapturing: true,
      completed: false
    })
    
    try {
      const response = await fetch('http://localhost:5000/api/capture-fingerprint', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_name: formData.name
        })
      })
      
      const result = await response.json()
      
      if (response.ok) {
        setFingerprintStatus({
          message: 'Fingerprint captured successfully!',
          isCapturing: false,
          completed: true
        })
        
        // Complete registration
        setTimeout(() => {
          alert(`🎉 Registration completed successfully!\n\n✅ Face: 5/5 photos captured\n✅ Fingerprint: Captured\n📁 Data saved in: dataset/face/${formData.name}/`)
          setStep(1) // Go back to start
          setCaptureStatus({ message: '', photos_captured: 0, total_photos: 5 })
          setFingerprintStatus({ message: '', isCapturing: false, completed: false })
        }, 2000)
      } else {
        setFingerprintStatus({
          message: `Failed: ${result.error}`,
          isCapturing: false,
          completed: false
        })
      }
      
    } catch (error) {
      setFingerprintStatus({
        message: `Error: ${error.message}`,
        isCapturing: false,
        completed: false
      })
    }
  }

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      stopCamera()
    }
  }, [])
  
  const pollCaptureStatus = async (userName) => {
    try {
      const response = await fetch(`http://localhost:5000/api/status/${userName}`)
      const status = await response.json()
      
      if (response.ok) {
        console.log('Capture status:', status)
        
        // Update UI with current status
        setCaptureStatus({
          message: status.message || '',
          photos_captured: status.photos_captured || 0,
          total_photos: status.total_photos || 5
        })
        
        if (status.completed) {
          // Registration completed successfully
          setIsRegistering(false)
          alert(`🎉 Registration completed successfully!\n\n✅ ${status.photos_captured}/5 photos captured\n📁 Photos saved in: dataset/face/${userName}/\n\nYou can now use the login system!`)
        } else if (status.status === 'error' || status.status === 'failed') {
          // Registration failed
          setIsRegistering(false)
          alert(`❌ Registration failed: ${status.message || status.error}`)
        } else {
          // Still in progress, continue polling
          setTimeout(() => pollCaptureStatus(userName), 2000) // Poll every 2 seconds
        }
      } else {
        setIsRegistering(false)
        alert(`Status check failed: ${status.error}`)
      }
    } catch (error) {
      setIsRegistering(false)
      alert(`Status check error: ${error.message}`)
    }
  }

  const handleBackToHome = () => {
    // This would be handled by parent component (App.jsx)
    window.location.reload() // Simple way to go back to home
  }

  if (step === 1) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-400 to-blue-600 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">Create Account</h1>
            <p className="text-gray-600">Enter your details to register</p>
          </div>
          
          <form onSubmit={handleFormSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Full Name
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent outline-none transition-colors"
                placeholder="Enter your full name"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent outline-none transition-colors"
                placeholder="Enter your email"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Phone Number
              </label>
              <input
                type="tel"
                name="phone"
                value={formData.phone}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent outline-none transition-colors"
                placeholder="Enter your phone number"
                required
              />
            </div>
            
            <div className="space-y-4">
              <button
                type="submit"
                className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200 shadow-md hover:shadow-lg"
              >
                Continue to Face Registration
              </button>
              
              <button
                type="button"
                onClick={handleBackToHome}
                className="w-full bg-gray-500 hover:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
              >
                Back to Home
              </button>
            </div>
          </form>
        </div>
      </div>
    )
  }

  if (step === 2) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-400 to-blue-600 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md text-center">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">Face Registration</h1>
            <p className="text-gray-600">Hello, {formData.name}!</p>
          </div>
          
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
            <div className="text-blue-800 mb-4">
              <h3 className="font-semibold mb-2">📸 Face Capture Process:</h3>
              <div className="text-sm text-left space-y-1">
                <p>• Camera will open automatically</p>
                <p>• Position your face in the frame</p>
                <p>• 5 photos will be captured automatically</p>
                <p>• Keep your face steady during capture</p>
                <p>• Photos saved as face_001 to face_005</p>
              </div>
            </div>
          </div>
          
          <div className="space-y-4">
            <button
              onClick={handleStartFaceCapture}
              disabled={isRegistering}
              className={`w-full font-semibold py-3 px-6 rounded-lg transition-colors duration-200 shadow-md hover:shadow-lg ${
                isRegistering 
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-green-600 hover:bg-green-700 text-white'
              }`}
            >
              {isRegistering ? 'Processing...' : 'Start Face Capture'}
            </button>
            
            <button
              onClick={() => setStep(1)}
              disabled={isRegistering}
              className="w-full bg-gray-500 hover:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200 disabled:opacity-50"
            >
              Back to Form
            </button>
          </div>
          
          {isRegistering && (
            <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="text-yellow-800 text-sm">
                <p className="font-semibold mb-2">🔄 Face capture in progress...</p>
                <p className="mb-2">{captureStatus.message}</p>
                <div className="flex items-center space-x-2">
                  <div className="bg-yellow-200 rounded-full h-2 flex-1">
                    <div 
                      className="bg-yellow-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${(captureStatus.photos_captured / captureStatus.total_photos) * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-xs font-mono">
                    {captureStatus.photos_captured}/{captureStatus.total_photos}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  if (step === 3) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-400 to-blue-600 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-2xl">
          <div className="text-center mb-6">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">Live Face Capture</h1>
            <p className="text-gray-600">Hello, {formData.name}! Position your face in the camera view</p>
          </div>
          
          {/* Live Camera Feed */}
          <div className="relative mb-6">
            <div className="bg-gray-900 rounded-lg overflow-hidden aspect-video flex items-center justify-center">
              {stream ? (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="text-white text-lg">Loading camera...</div>
              )}
            </div>
            
            {/* Face detection overlay would go here */}
            <div className="absolute top-4 left-4 bg-black bg-opacity-50 text-white px-3 py-1 rounded-full text-sm">
              📸 {captureStatus.photos_captured}/5 photos captured
            </div>
          </div>

          {/* Capture Controls */}
          <div className="space-y-4">
            <button
              onClick={capturePhoto}
              disabled={isCapturing || !stream}
              className={`w-full font-bold py-4 px-6 rounded-lg transition-colors duration-200 shadow-lg ${
                isCapturing || !stream
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-blue-600 hover:bg-blue-700 text-white hover:shadow-xl'
              }`}
            >
              {isCapturing ? '📸 Capturing...' : '📸 Capture Photo'}
            </button>
            
            <div className="flex space-x-4">
              <button
                onClick={() => {
                  stopCamera()
                  setStep(2)
                }}
                className="flex-1 bg-gray-500 hover:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
              >
                ← Back
              </button>
              
              <button
                onClick={() => {
                  stopCamera()
                  setStep(1)
                  setCaptureStatus({ message: '', photos_captured: 0, total_photos: 5 })
                }}
                className="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
              >
                Cancel
              </button>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mt-6 bg-gray-200 rounded-full h-3">
            <div 
              className="bg-green-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${(captureStatus.photos_captured / captureStatus.total_photos) * 100}%` }}
            ></div>
          </div>
          
          {captureStatus.message && (
            <div className="mt-4 text-center text-green-600 font-medium">
              {captureStatus.message}
            </div>
          )}
        </div>
        
        {/* Hidden canvas for capturing photos */}
        <canvas ref={canvasRef} style={{ display: 'none' }} />
      </div>
    )
  }

  if (step === 4) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-400 to-pink-600 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md text-center">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">Fingerprint Capture</h1>
            <p className="text-gray-600">Hello, {formData.name}!</p>
            <p className="text-sm text-gray-500 mt-2">Face capture completed ✅</p>
          </div>
          
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-6 mb-6">
            <div className="text-purple-800 mb-4">
              <h3 className="font-semibold mb-2">👆 Fingerprint Capture Process:</h3>
              <div className="text-sm text-left space-y-1">
                <p>• Place finger on R307 sensor</p>
                <p>• Keep finger steady during scan</p>
                <p>• Remove and place again when prompted</p>
                <p>• Fingerprint saved as .bin format</p>
                <p>• Stored in same folder as face images</p>
              </div>
            </div>
          </div>
          
          <div className="space-y-4">
            <button
              onClick={captureFingerprint}
              disabled={fingerprintStatus.isCapturing}
              className={`w-full font-bold py-4 px-6 rounded-lg transition-colors duration-200 shadow-lg ${
                fingerprintStatus.isCapturing
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : fingerprintStatus.completed
                  ? 'bg-green-600 text-white'
                  : 'bg-purple-600 hover:bg-purple-700 text-white hover:shadow-xl'
              }`}
            >
              {fingerprintStatus.isCapturing ? '👆 Capturing Fingerprint...' : 
               fingerprintStatus.completed ? '✅ Fingerprint Captured!' : 
               '👆 Capture Fingerprint'}
            </button>
            
            <div className="flex space-x-4">
              <button
                onClick={() => {
                  // Skip fingerprint and complete registration
                  alert(`⚠️ Registration completed without fingerprint!\n\n✅ Face: 5/5 photos captured\n❌ Fingerprint: Skipped\n📁 Data saved in: dataset/face/${formData.name}/`)
                  setStep(1)
                  setCaptureStatus({ message: '', photos_captured: 0, total_photos: 5 })
                  setFingerprintStatus({ message: '', isCapturing: false, completed: false })
                }}
                disabled={fingerprintStatus.isCapturing}
                className="flex-1 bg-gray-500 hover:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200 disabled:opacity-50"
              >
                Skip Fingerprint
              </button>
              
              <button
                onClick={() => {
                  setStep(1)
                  setCaptureStatus({ message: '', photos_captured: 0, total_photos: 5 })
                  setFingerprintStatus({ message: '', isCapturing: false, completed: false })
                }}
                disabled={fingerprintStatus.isCapturing}
                className="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
          
          {/* Status Display */}
          {fingerprintStatus.message && (
            <div className={`mt-6 border rounded-lg p-4 ${
              fingerprintStatus.completed 
                ? 'bg-green-50 border-green-200 text-green-800'
                : fingerprintStatus.isCapturing
                ? 'bg-yellow-50 border-yellow-200 text-yellow-800'
                : 'bg-red-50 border-red-200 text-red-800'
            }`}>
              <p className="font-medium">
                {fingerprintStatus.completed ? '✅' : fingerprintStatus.isCapturing ? '🔄' : '❌'} {fingerprintStatus.message}
              </p>
              {fingerprintStatus.isCapturing && (
                <div className="mt-2">
                  <div className="bg-yellow-200 rounded-full h-2">
                    <div className="bg-yellow-600 h-2 rounded-full animate-pulse" style={{ width: '100%' }}></div>
                  </div>
                </div>
              )}
            </div>
          )}
          
          {!fingerprintStatus.message && (
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-blue-800 text-sm">
                💡 Make sure the R307 fingerprint sensor is connected to COM3
              </p>
            </div>
          )}
        </div>
      </div>
    )
  }
}

export default Register
