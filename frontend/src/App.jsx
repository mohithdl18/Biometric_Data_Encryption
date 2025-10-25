import { useState } from 'react'
import './App.css'
import Register from './pages/Register'
import Login from './pages/Login'

function App() {
  const [currentPage, setCurrentPage] = useState('home')

  const handleLogin = () => {
    console.log('Login button clicked')
    setCurrentPage('login')
  }

  const handleRegister = () => {
    console.log('Register button clicked')
    setCurrentPage('register')
  }

  const handleBackToHome = () => {
    setCurrentPage('home')
  }

  if (currentPage === 'register') {
    return <Register />
  }

  if (currentPage === 'login') {
    return <Login onBackToHome={handleBackToHome} />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-400 to-purple-600 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Welcome</h1>
          <p className="text-gray-600">Please choose an option to continue</p>
        </div>
        
        <div className="space-y-4">
          <button 
            onClick={handleLogin}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200 shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
          >
            Login
          </button>
          
          <button 
            onClick={handleRegister}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200 shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
          >
            Register
          </button>
        </div>
        
        <div className="mt-8 text-center">
          <p className="text-sm text-gray-500">
            Built with React + Tailwind CSS
          </p>
        </div>
      </div>
    </div>
  )
}

export default App
