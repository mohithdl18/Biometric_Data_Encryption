import { useState, useEffect } from 'react'

function Dashboard({ currentUser, onLogout, onBackToHome }) {
  const [userInfo, setUserInfo] = useState(null)
  const [userPhoto, setUserPhoto] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('info') // 'info', 'success', 'error'
  const [downloadingPhoto, setDownloadingPhoto] = useState(false)
  const [verifyingKey, setVerifyingKey] = useState(false)
  const [keyVerificationResult, setKeyVerificationResult] = useState(null)
  const [hasSteganographicPhoto, setHasSteganographicPhoto] = useState(false)
  const [checkingStegoStatus, setCheckingStegoStatus] = useState(false)

  // Fetch user information on component mount
  useEffect(() => {
    if (currentUser) {
      fetchUserInfo()
      checkSteganographicStatus()
    }
  }, [currentUser])

  const checkSteganographicStatus = async () => {
    try {
      setCheckingStegoStatus(true)
      const response = await fetch(`http://localhost:5000/api/dashboard/has-steganographic-photo/${currentUser}`)
      const data = await response.json()
      
      if (response.ok && data.success) {
        setHasSteganographicPhoto(data.has_steganographic_photo)
      }
    } catch (error) {
      console.error('Failed to check steganographic status:', error)
    } finally {
      setCheckingStegoStatus(false)
    }
  }

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

  const downloadSteganographicPhoto = async () => {
    try {
      setDownloadingPhoto(true)
      setMessage('Downloading steganographic photo with embedded key...')
      setMessageType('info')

      const response = await fetch(`http://localhost:5000/api/dashboard/download-steganographic-photo/${currentUser}`)
      
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.style.display = 'none'
        a.href = url
        
        // Get filename from response headers or use default
        const contentDisposition = response.headers.get('Content-Disposition')
        const filename = contentDisposition 
          ? contentDisposition.split('filename=')[1]?.replace(/"/g, '') 
          : `${currentUser}_steganographic_photo.png`
        
        a.download = filename
        document.body.appendChild(a)
        a.click()
        
        // Cleanup
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        
        setMessage('✅ Steganographic photo downloaded successfully! Your fingerprint key is hidden inside.')
        setMessageType('success')
      } else {
        const errorData = await response.json()
        setMessage(errorData.error || 'Failed to download steganographic photo')
        setMessageType('error')
      }
    } catch (error) {
      setMessage('Error downloading steganographic photo. Please check your connection.')
      setMessageType('error')
    } finally {
      setDownloadingPhoto(false)
    }
  }

  const verifyEmbeddedKey = async () => {
    try {
      setVerifyingKey(true)
      setMessage('Verifying embedded fingerprint key...')
      setMessageType('info')

      const response = await fetch(`http://localhost:5000/api/dashboard/verify-steganographic-key/${currentUser}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      const data = await response.json()
      
      if (response.ok && data.success) {
        setKeyVerificationResult({
          verified: data.verified,
          message: data.message,
          keyPreview: data.key_preview
        })
        
        if (data.verified) {
          setMessage(`✅ Key verification successful! Preview: ${data.key_preview}`)
          setMessageType('success')
        } else {
          setMessage('❌ Key verification failed - key not found in image')
          setMessageType('error')
        }
      } else {
        setMessage(data.error || 'Failed to verify embedded key')
        setMessageType('error')
        setKeyVerificationResult(null)
      }
    } catch (error) {
      setMessage('Error verifying key. Please check your connection.')
      setMessageType('error')
      setKeyVerificationResult(null)
    } finally {
      setVerifyingKey(false)
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
                {/* User Photo with Steganography Info */}
                <div className="flex-shrink-0">
                  {userPhoto ? (
                    <div className="relative">
                      <img
                        src={userPhoto}
                        alt={`${userInfo.name}'s photo`}
                        className="w-32 h-32 rounded-full border-4 border-white shadow-lg object-cover"
                      />
                      {/* Steganography indicator */}
                      {userInfo.fingerprint_algorithm === 'sha256' && (
                        <div className="absolute -bottom-1 -right-1 bg-green-500 text-white text-xs px-2 py-1 rounded-full border-2 border-white">
                          🔐 Encrypted
                        </div>
                      )}
                    </div>
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

              {/* Steganographic Controls */}
              {hasSteganographicPhoto && userInfo.has_photo && (
                <div className="mt-6 bg-purple-50 rounded-lg p-4 border-2 border-purple-200">
                  <h3 className="text-lg font-semibold text-purple-800 mb-3 flex items-center">
                    <span className="text-purple-600 mr-2">🎭</span>
                    Steganographic Photo Available
                  </h3>
                  <p className="text-purple-700 text-sm mb-4">
                    ✨ Your face image has a special version with your encrypted fingerprint key hidden inside using advanced steganography.
                  </p>
                  
                  <div className="flex flex-wrap gap-3">
                    <button
                      onClick={downloadSteganographicPhoto}
                      disabled={downloadingPhoto}
                      className="bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200 flex items-center shadow-md hover:shadow-lg"
                    >
                      {downloadingPhoto ? (
                        <>
                          <div className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                          Preparing Download...
                        </>
                      ) : (
                        <>
                          <span className="mr-2">📥</span>
                          Download Steganographic Photo
                        </>
                      )}
                    </button>
                    
                    <button
                      onClick={verifyEmbeddedKey}
                      disabled={verifyingKey}
                      className="bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200 flex items-center shadow-md hover:shadow-lg"
                    >
                      {verifyingKey ? (
                        <>
                          <div className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                          Verifying...
                        </>
                      ) : (
                        <>
                          <span className="mr-2">🔍</span>
                          Verify Embedded Key
                        </>
                      )}
                    </button>
                  </div>
                  
                  {/* Key Verification Result */}
                  {keyVerificationResult && (
                    <div className={`mt-3 p-3 rounded-lg ${
                      keyVerificationResult.verified 
                        ? 'bg-green-100 border border-green-200' 
                        : 'bg-red-100 border border-red-200'
                    }`}>
                      <div className="flex items-center">
                        <span className={`mr-2 ${
                          keyVerificationResult.verified ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {keyVerificationResult.verified ? '✅' : '❌'}
                        </span>
                        <span className={`text-sm font-medium ${
                          keyVerificationResult.verified ? 'text-green-800' : 'text-red-800'
                        }`}>
                          {keyVerificationResult.message}
                        </span>
                      </div>
                      {keyVerificationResult.verified && keyVerificationResult.keyPreview && (
                        <div className="mt-2 text-xs text-green-700 font-mono">
                          Key Preview: {keyVerificationResult.keyPreview}
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Info Box */}
                  <div className="mt-4 bg-purple-100 rounded-lg p-3">
                    <p className="text-purple-800 text-xs">
                      <strong>ℹ️ What is steganography?</strong><br/>
                      Your fingerprint key is invisibly embedded in the image pixels. The photo looks normal but contains your encrypted biometric data for extra security.
                    </p>
                  </div>
                </div>
              )}
              
              {/* Show message if steganographic photo not available */}
              {!hasSteganographicPhoto && userInfo.fingerprint_algorithm === 'sha256' && userInfo.has_photo && (
                <div className="mt-6 bg-yellow-50 rounded-lg p-4 border-2 border-yellow-200">
                  <h3 className="text-lg font-semibold text-yellow-800 mb-2 flex items-center">
                    <span className="text-yellow-600 mr-2">⚠️</span>
                    Steganographic Photo Not Available
                  </h3>
                  <p className="text-yellow-700 text-sm">
                    To get a steganographic photo with your embedded fingerprint key, please re-register your face image after enrolling your fingerprint.
                  </p>
                </div>
              )}
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
