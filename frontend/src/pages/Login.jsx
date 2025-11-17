import { useState, useEffect } from 'react'

function Login({ onBackToHome, onLoginSuccess }) {
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState('')
  const [matchedUser, setMatchedUser] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isFaceMatching, setIsFaceMatching] = useState(false)
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('info') // 'info', 'success', 'error'
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [faceMatchResult, setFaceMatchResult] = useState(null)

  // Fetch registered users on component mount
  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      setIsLoading(true)
      const response = await fetch('http://localhost:5000/api/users')
      const data = await response.json()
      
      if (response.ok) {
        setUsers(data.users)
        setMessage(data.message)
        setMessageType('info')
      } else {
        setMessage(data.error || 'Failed to fetch users')
        setMessageType('error')
      }
    } catch (error) {
      setMessage('Error connecting to server. Please ensure the backend is running.')
      setMessageType('error')
    } finally {
      setIsLoading(false)
    }
  }

  const handleFaceMatch = async () => {
    try {
      setIsFaceMatching(true)
      setMessage('🎥 Starting face recognition... Please look at your webcam.')
      setMessageType('info')

      const response = await fetch('http://localhost:5000/api/face-match', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setFaceMatchResult(data)
        setMatchedUser(data.matched_user)
        setShowConfirmation(true)
        setMessage(`Face recognized as ${data.matched_user} (confidence: ${data.confidence.toFixed(2)})`)
        setMessageType('success')
      } else {
        setMessage(data.error || 'Face recognition failed. Please try again.')
        setMessageType('error')
      }
    } catch (error) {
      setMessage('Error connecting to server or webcam. Please check connections.')
      setMessageType('error')
    } finally {
      setIsFaceMatching(false)
    }
  }

  const handleConfirmUser = (confirmed) => {
    if (confirmed) {
      setSelectedUser(matchedUser)
      setShowConfirmation(false)
      setMessage(`Confirmed as ${matchedUser}. Now please proceed with fingerprint authentication.`)
      setMessageType('info')
    } else {
      setMatchedUser('')
      setSelectedUser('')
      setShowConfirmation(false)
      setFaceMatchResult(null)
      setMessage('Face recognition cancelled. Please try again.')
      setMessageType('info')
    }
  }

  const handleAuthenticate = async () => {
    if (!selectedUser) {
      setMessage('Please complete face recognition first')
      setMessageType('error')
      return
    }

    try {
      setIsAuthenticating(true)
      setMessage('Authenticating... Please place your finger on the R307 sensor.')
      setMessageType('info')

      const response = await fetch('http://localhost:5000/api/authenticate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username: selectedUser })
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setMessage(`🎉 Welcome, ${selectedUser}! Authentication successful (Confidence: ${data.confidence})`)
        setMessageType('success')
        
        // Redirect to dashboard after successful authentication
        setTimeout(() => {
          setMessage('Login successful! Redirecting to dashboard...')
          if (onLoginSuccess) {
            onLoginSuccess(selectedUser)
          }
        }, 2000)
      } else {
        setMessage(data.message || 'Authentication failed')
        setMessageType('error')
      }
    } catch (error) {
      setMessage('Error connecting to server or sensor. Please check connections.')
      setMessageType('error')
    } finally {
      setIsAuthenticating(false)
    }
  }

  const handleBackToHome = () => {
    if (onBackToHome) {
      onBackToHome()
    }
  }

  const getMessageColor = () => {
    switch (messageType) {
      case 'success': return 'text-green-700 bg-green-50 border-green-200'
      case 'error': return 'text-red-700 bg-red-50 border-red-200'
      default: return 'text-blue-700 bg-blue-50 border-blue-200'
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-400 to-blue-600 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Biometric Login</h1>
          <p className="text-gray-600">Automatic face recognition + fingerprint authentication</p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="text-center mb-6">
            <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full"></div>
            <p className="text-gray-600 mt-2">Loading users...</p>
          </div>
        )}

        {/* Face Recognition Step */}
        {!isLoading && users.length > 0 && !selectedUser && (
          <div className="mb-6">
            <div className="text-center mb-4">
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Step 1: Face Recognition</h3>
              <p className="text-gray-600 text-sm">Click below to start automatic face recognition</p>
            </div>
            
            <button
              onClick={handleFaceMatch}
              disabled={isFaceMatching}
              className={`w-full py-3 px-6 rounded-lg font-semibold transition-all duration-200 ${
                isFaceMatching
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-purple-600 hover:bg-purple-700 text-white shadow-md hover:shadow-lg transform hover:-translate-y-0.5'
              }`}
            >
              {isFaceMatching ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                  Recognizing Face...
                </div>
              ) : (
                '📷 Start Face Recognition'
              )}
            </button>
          </div>
        )}

        {/* User Confirmation Modal */}
        {showConfirmation && faceMatchResult && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="text-lg font-semibold text-blue-800 mb-2">Face Recognition Result</h3>
            <p className="text-blue-700 mb-4">
              Detected: <strong>{faceMatchResult.matched_user}</strong> 
              <br />
              Confidence: <strong>{(faceMatchResult.confidence * 100).toFixed(1)}%</strong>
            </p>
            <div className="flex space-x-3">
              <button
                onClick={() => handleConfirmUser(true)}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
              >
                ✅ Yes, that's me
              </button>
              <button
                onClick={() => handleConfirmUser(false)}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
              >
                ❌ No, try again
              </button>
            </div>
          </div>
        )}

        {/* Selected User Display */}
        {selectedUser && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <h3 className="text-lg font-semibold text-green-800 mb-2">Step 2: Fingerprint Authentication</h3>
            <p className="text-green-700 mb-2">
              User identified: <strong>{selectedUser}</strong>
            </p>
            <p className="text-green-600 text-sm">Now proceed with fingerprint authentication below</p>
          </div>
        )}

        {/* No Users Found */}
        {!isLoading && users.length === 0 && (
          <div className="text-center mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-yellow-700">No registered users found with fingerprint data.</p>
            <p className="text-yellow-600 text-sm mt-1">Please register first to use fingerprint login.</p>
          </div>
        )}

        {/* Authentication Button */}
        {selectedUser && (
          <button
            onClick={handleAuthenticate}
            disabled={isAuthenticating}
            className={`w-full py-3 px-6 rounded-lg font-semibold transition-all duration-200 ${
              isAuthenticating
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white shadow-md hover:shadow-lg transform hover:-translate-y-0.5'
            }`}
          >
            {isAuthenticating ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                Authenticating...
              </div>
            ) : (
              '🔒 Authenticate with Fingerprint'
            )}
          </button>
        )}

        {/* Message Display */}
        {message && (
          <div className={`mt-6 p-4 rounded-lg border ${getMessageColor()}`}>
            <p className="text-sm font-medium">{message}</p>
          </div>
        )}

        {/* Actions */}
        <div className="mt-8 space-y-3">
          {/* Reset Process Button */}
          {(selectedUser || showConfirmation) && (
            <button
              onClick={() => {
                setSelectedUser('')
                setMatchedUser('')
                setShowConfirmation(false)
                setFaceMatchResult(null)
                setMessage('Process reset. Click "Start Face Recognition" to begin again.')
                setMessageType('info')
              }}
              disabled={isFaceMatching || isAuthenticating}
              className="w-full bg-orange-100 hover:bg-orange-200 text-orange-700 font-medium py-2 px-4 rounded-lg transition-colors duration-200"
            >
              🔄 Start Over
            </button>
          )}
          
          {/* Back to Home Button */}
          <button
            onClick={handleBackToHome}
            className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors duration-200"
          >
            ← Back to Home
          </button>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-400">
            Dual biometric authentication: Face recognition + R307 fingerprint sensor
          </p>
        </div>
      </div>
    </div>
  )
}

export default Login
