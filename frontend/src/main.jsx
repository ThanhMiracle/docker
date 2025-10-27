import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, useNavigate } from 'react-router-dom'
import Products from './pages/Products'
import MyProducts from './pages/MyProducts'
import Create from './pages/Create'
import Edit from './pages/Edit'
import Login from './pages/Login'
import Register from './pages/Register'

// --- Hàm lấy base URL ưu tiên runtime ---
function getApiBase() {
  if (typeof window !== 'undefined' && window.__ENV__ && window.__ENV__.API_BASE) {
    return window.__ENV__.API_BASE
  }
  if (import.meta?.env?.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE
  }
  //return 'localhost:8000'
}

// Chuẩn hoá để có protocol
const API_BASE = getApiBase()
const API = API_BASE.startsWith('http://') || API_BASE.startsWith('https://')
  ? API_BASE
  : `http://${API_BASE}`

function Nav() {
  const nav = useNavigate()

  const logout = async () => {
    const token = localStorage.getItem('token')
    if (token) {
      await fetch(`${API}/auth/logout`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
    }
    localStorage.removeItem('token')
    nav('/login')
  }

  return (
    <div
      style={{
        display: 'flex',
        gap: 16,
        padding: 12,
        borderBottom: '1px solid #eee',
        fontFamily: 'system-ui, sans-serif'
      }}
    >
      <Link to="/">Products</Link>
      <Link to="/my">My Products</Link>
      <Link to="/create">Add Product</Link>
      <div style={{ marginLeft: 'auto', display: 'flex', gap: 12 }}>
        <Link to="/login">Login</Link>
        <Link to="/register">Register</Link>
        <button onClick={logout}>Logout</button>
      </div>
    </div>
  )
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Nav />
      <Routes>
        <Route path="/" element={<Products />} />
        <Route path="/my" element={<MyProducts />} />
        <Route path="/create" element={<Create />} />
        <Route path="/edit/:id" element={<Edit />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
