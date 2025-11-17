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
  const [showManualSelection, setShowManualSelection] = useState(false)
  const [faceMatchResult, setFaceMatchResult] = useState(null)

  // Fetch registered users on component mount
  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      setIsLoading(true)
      const response = await fetch('http://localhost:5000/api/users-for-selection')
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
      setShowManualSelection(false)

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
        setMessage(`Face recognized as ${data.matched_user} (confidence: ${(data.confidence * 100).toFixed(1)}%)`)
        setMessageType('success')
      } else {
        setMessage(data.message || data.error || 'Face recognition failed.')
        setMessageType('error')
        
        // Check if manual selection should be shown
        if (data.show_manual_selection) {
          setShowManualSelection(true)
        }
      }
    } catch (error) {
      setMessage('Error connecting to server or webcam. Please check connections.')
      setMessageType('error')
    } finally {
      setIsFaceMatching(false)
    }
  }

  const handleConfirmUser = async (confirmed) => {
    if (confirmed) {
      // User confirmed their identity
      try {
        const response = await fetch('http://localhost:5000/api/verify-user-identity', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: matchedUser,
            is_correct: true,
            confidence: faceMatchResult?.confidence || 0
          })
        })

        const data = await response.json()

        if (response.ok && data.success) {
          setSelectedUser(matchedUser)
          setShowConfirmation(false)
          setMessage(`Confirmed as ${matchedUser}. Now please proceed with fingerprint authentication.`)
          setMessageType('info')
        } else {
          setMessage(data.error || 'Identity verification failed')
          setMessageType('error')
        }
      } catch (error) {
        setMessage('Error confirming identity')
        setMessageType('error')
      }
    } else {
      // User rejected the identification - show manual selection
      setMatchedUser('')
      setSelectedUser('')
      setShowConfirmation(false)
      setFaceMatchResult(null)
      setShowManualSelection(true)
      setMessage('Please select your name manually from the list below.')
      setMessageType('info')
    }
  }

  const handleManualLogin = async (username) => {
    try {
      setIsLoading(true)
      setMessage(`Logging in as ${username}...`)
      setMessageType('info')

      const response = await fetch('http://localhost:5000/api/manual-login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: username,
          method: 'Manual Selection'
        })
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setSelectedUser(username)
        setShowManualSelection(false)
        setMessage(`Selected as ${username}. Now please proceed with fingerprint authentication.`)
        setMessageType('info')
      } else {
        setMessage(data.error || 'Manual selection failed')
        setMessageType('error')
      }
    } catch (error) {
      setMessage('Error with manual selection')
      setMessageType('error')
    } finally {
      setIsLoading(false)
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
        {!isLoading && users.length > 0 && !selectedUser && !showManualSelection && (
          <div className="mb-6">
            <div className="text-center mb-4">
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Step 1: Face Recognition</h3>
              <p className="text-gray-600 text-sm">Click below to start automatic face recognition</p>
            </div>
            
            <button
              onClick={handleFaceMatch}
              disabled={isFaceMatching}
              className={`w-full py-3 px-6 rounded-lg font-semibold transition-all duration-200 mb-3 ${
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

            <div className="text-center">
              <p className="text-gray-500 text-sm mb-2">Or</p>
              <button
                onClick={() => {
                  setShowManualSelection(true)
                  setMessage('Select your name from the list below.')
                  setMessageType('info')
                }}
                className="text-blue-600 hover:text-blue-800 underline text-sm font-medium"
              >
                Select manually if face recognition doesn't work
              </button>
            </div>
          </div>
        )}

        {/* Manual User Selection */}
        {showManualSelection && users.length > 0 && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <h3 className="text-lg font-semibold text-yellow-800 mb-3">Manual User Selection</h3>
            <p className="text-yellow-700 mb-4 text-sm">
              Face recognition didn't find a match. Please select your name from the list below:
            </p>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {users.map((user, index) => (
                <button
                  key={index}
                  onClick={() => handleManualLogin(user.name)}
                  disabled={isLoading}
                  className="w-full text-left p-3 bg-white hover:bg-yellow-100 border border-yellow-300 rounded-lg transition-colors duration-200 disabled:opacity-50"
                >
                  <div className="font-medium text-gray-800">{user.name}</div>
                  {user.email && (
                    <div className="text-sm text-gray-600">{user.email}</div>
                  )}
                  {user.created_at && (
                    <div className="text-xs text-gray-500">Registered: {user.created_at}</div>
                  )}
                </button>
              ))}
            </div>
            <button
              onClick={() => {
                setShowManualSelection(false)
                setMessage('Manual selection cancelled. Try face recognition again or contact support.')
                setMessageType('info')
              }}
              className="w-full mt-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors duration-200"
            >
              Cancel Manual Selection
            </button>
          </div>
        )}
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
          {(selectedUser || showConfirmation || showManualSelection) && (
            <button
              onClick={() => {
                setSelectedUser('')
                setMatchedUser('')
                setShowConfirmation(false)
                setShowManualSelection(false)
                setFaceMatchResult(null)
                setMessage('Process reset. Choose face recognition or manual selection to begin again.')
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
