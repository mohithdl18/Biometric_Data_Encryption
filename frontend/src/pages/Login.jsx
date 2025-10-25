import { useState, useEffect } from 'react'

function Login({ onBackToHome }) {
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('info') // 'info', 'success', 'error'

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

  const handleAuthenticate = async () => {
    if (!selectedUser) {
      setMessage('Please select a user to authenticate')
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
        
        // Could redirect to dashboard or perform other actions here
        setTimeout(() => {
          setMessage('Login successful! Redirecting...')
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
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Fingerprint Login</h1>
          <p className="text-gray-600">Select your name and authenticate with fingerprint</p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="text-center mb-6">
            <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full"></div>
            <p className="text-gray-600 mt-2">Loading users...</p>
          </div>
        )}

        {/* User Selection */}
        {!isLoading && users.length > 0 && (
          <div className="mb-6">
            <label htmlFor="user-select" className="block text-sm font-medium text-gray-700 mb-2">
              Select Your Name
            </label>
            <select
              id="user-select"
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-700"
            >
              <option value="">Choose your name...</option>
              {users.map((user, index) => (
                <option key={index} value={user}>{user}</option>
              ))}
            </select>
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
        {users.length > 0 && (
          <button
            onClick={handleAuthenticate}
            disabled={!selectedUser || isAuthenticating}
            className={`w-full py-3 px-6 rounded-lg font-semibold transition-all duration-200 ${
              !selectedUser || isAuthenticating
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
          {/* Refresh Users Button */}
          <button
            onClick={fetchUsers}
            disabled={isLoading}
            className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors duration-200"
          >
            🔄 Refresh User List
          </button>
          
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
            Secure authentication powered by R307 fingerprint sensor
          </p>
        </div>
      </div>
    </div>
  )
}

export default Login
