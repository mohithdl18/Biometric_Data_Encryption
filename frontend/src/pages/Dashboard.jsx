import { useState, useEffect } from 'react'

function Dashboard({ currentUser, onLogout, onBackToHome }) {
  const [userInfo, setUserInfo] = useState(null)
  const [userPhoto, setUserPhoto] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('info') // 'info', 'success', 'error'

  // Fetch user information on component mount
  useEffect(() => {
    if (currentUser) {
      fetchUserInfo()
    }
  }, [currentUser])

  const fetchUserInfo = async () => {
    try {
      setIsLoading(true)
      const response = await fetch(`http://localhost:5000/api/dashboard/user/${currentUser}`)
      const data = await response.json()
      
      if (response.ok && data.success) {
        setUserInfo(data.user)
        if (data.user.has_photo) {
          await fetchUserPhoto()
        }
        setMessage(`Welcome back, ${data.user.name}!`)
        setMessageType('success')
      } else {
        setMessage(data.error || 'Failed to load user information')
        setMessageType('error')
      }
    } catch (error) {
      setMessage('Error connecting to server. Please check your connection.')
      setMessageType('error')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchUserPhoto = async () => {
    try {
      const response = await fetch(`http://localhost:5000/api/dashboard/photo/${currentUser}`)
      
      if (response.ok) {
        const blob = await response.blob()
        const photoUrl = URL.createObjectURL(blob)
        setUserPhoto(photoUrl)
      }
    } catch (error) {
      console.error('Failed to load user photo:', error)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Not available'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getMessageColor = () => {
    switch (messageType) {
      case 'success': return 'text-green-700 bg-green-50 border-green-200'
      case 'error': return 'text-red-700 bg-red-50 border-red-200'
      default: return 'text-blue-700 bg-blue-50 border-blue-200'
    }
  }

  const handleLogout = () => {
    // Clean up photo URL to prevent memory leaks
    if (userPhoto) {
      URL.revokeObjectURL(userPhoto)
    }
    
    if (onLogout) {
      onLogout()
    } else if (onBackToHome) {
      onBackToHome()
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-400 to-purple-600 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md text-center">
          <div className="animate-spin inline-block w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full mb-4"></div>
          <p className="text-gray-600">Loading your dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-400 to-purple-600 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-2xl p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 mb-2">🎉 Welcome to Your Dashboard</h1>
              <p className="text-gray-600">Your biometric profile and account information</p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={onBackToHome}
                className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors duration-200"
              >
                🏠 Home
              </button>
              <button
                onClick={handleLogout}
                className="bg-red-100 hover:bg-red-200 text-red-700 font-medium py-2 px-4 rounded-lg transition-colors duration-200"
              >
                🚪 Logout
              </button>
            </div>
          </div>
        </div>

        {/* Message Display */}
        {message && (
          <div className={`mb-6 p-4 rounded-lg border ${getMessageColor()}`}>
            <p className="text-sm font-medium">{message}</p>
          </div>
        )}

        {/* User Profile Card */}
        {userInfo && (
          <div className="bg-white rounded-2xl shadow-2xl overflow-hidden mb-6">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-600 p-6 text-white">
              <div className="flex items-start space-x-6">
                {/* User Photo */}
                <div className="flex-shrink-0">
                  {userPhoto ? (
                    <img
                      src={userPhoto}
                      alt={`${userInfo.name}'s photo`}
                      className="w-32 h-32 rounded-full border-4 border-white shadow-lg object-cover"
                    />
                  ) : (
                    <div className="w-32 h-32 rounded-full border-4 border-white shadow-lg bg-gray-300 flex items-center justify-center">
                      <span className="text-4xl text-gray-600">👤</span>
                    </div>
                  )}
                </div>

                {/* User Basic Info */}
                <div className="flex-1">
                  <h2 className="text-3xl font-bold mb-2">{userInfo.name}</h2>
                  <div className="space-y-2 text-indigo-100">
                    <div className="flex items-center">
                      <span className="text-lg">📧</span>
                      <span className="ml-2">{userInfo.email}</span>
                    </div>
                    <div className="flex items-center">
                      <span className="text-lg">📱</span>
                      <span className="ml-2">{userInfo.phone}</span>
                    </div>
                    <div className="flex items-center">
                      <span className="text-lg">📅</span>
                      <span className="ml-2">Member since {formatDate(userInfo.created_at)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Detailed Information */}
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Account Status */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
                    <span className="text-green-600 mr-2">✅</span>
                    Account Status
                  </h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Registration Status:</span>
                      <span className={`font-medium ${
                        userInfo.registration_complete 
                          ? 'text-green-600' 
                          : 'text-yellow-600'
                      }`}>
                        {userInfo.registration_complete ? 'Complete' : 'Incomplete'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Account ID:</span>
                      <span className="text-gray-800 font-mono text-sm">
                        {userInfo._id?.slice(-8) || 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Biometric Data Status */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
                    <span className="text-blue-600 mr-2">🔐</span>
                    Biometric Data
                  </h3>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Face Image:</span>
                      <div className="flex items-center">
                        {userInfo.has_face_image ? (
                          <>
                            <span className="text-green-600 mr-1">✅</span>
                            <span className="text-green-600 font-medium">Enrolled</span>
                          </>
                        ) : (
                          <>
                            <span className="text-red-600 mr-1">❌</span>
                            <span className="text-red-600 font-medium">Not Enrolled</span>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Fingerprint:</span>
                      <div className="flex items-center">
                        {userInfo.has_fingerprint ? (
                          <>
                            <span className="text-green-600 mr-1">✅</span>
                            <span className="text-green-600 font-medium">Enrolled</span>
                          </>
                        ) : (
                          <>
                            <span className="text-red-600 mr-1">❌</span>
                            <span className="text-red-600 font-medium">Not Enrolled</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Last Updated Information */}
              <div className="mt-6 bg-blue-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-blue-800 mb-3 flex items-center">
                  <span className="text-blue-600 mr-2">📊</span>
                  Recent Activity
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  {userInfo.face_updated_at && (
                    <div>
                      <span className="text-blue-600 font-medium">Face Image Updated:</span>
                      <br />
                      <span className="text-blue-800">{formatDate(userInfo.face_updated_at)}</span>
                    </div>
                  )}
                  {userInfo.fingerprint_updated_at && (
                    <div>
                      <span className="text-blue-600 font-medium">Fingerprint Updated:</span>
                      <br />
                      <span className="text-blue-800">{formatDate(userInfo.fingerprint_updated_at)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Action Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {/* Security Status */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <span className="text-2xl">🛡️</span>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-semibold text-gray-800">Security Level</h3>
                <p className="text-green-600 font-medium">
                  {userInfo?.registration_complete ? 'High Security' : 'Incomplete Setup'}
                </p>
              </div>
            </div>
            <p className="text-gray-600 text-sm">
              {userInfo?.registration_complete 
                ? 'Your account is fully secured with dual biometric authentication.'
                : 'Complete your biometric enrollment for maximum security.'}
            </p>
          </div>

          {/* Biometric Score */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <span className="text-2xl">📈</span>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-semibold text-gray-800">Enrollment Status</h3>
                <p className="text-blue-600 font-medium">
                  {((userInfo?.has_face_image ? 1 : 0) + (userInfo?.has_fingerprint ? 1 : 0)) * 50}% Complete
                </p>
              </div>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ 
                  width: `${((userInfo?.has_face_image ? 1 : 0) + (userInfo?.has_fingerprint ? 1 : 0)) * 50}%` 
                }}
              ></div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <span className="text-2xl">⚡</span>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-semibold text-gray-800">Quick Actions</h3>
                <p className="text-purple-600 font-medium">Account Management</p>
              </div>
            </div>
            <button
              onClick={fetchUserInfo}
              className="w-full bg-purple-100 hover:bg-purple-200 text-purple-700 font-medium py-2 px-4 rounded-lg transition-colors duration-200 text-sm"
            >
              🔄 Refresh Data
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center">
          <p className="text-white text-sm opacity-80">
            Secure dashboard powered by advanced biometric authentication
          </p>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
