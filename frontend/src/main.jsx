import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, useNavigate } from 'react-router-dom'
import Products from './pages/Products'
import Create from './pages/Create'
import Edit from './pages/Edit'
import Login from './pages/Login'
import Register from './pages/Register'
import Cart from './pages/Cart'
import Orders from './pages/Orders'
import ConfirmOrder from './pages/ConfirmOrder'
import VerifyEmail from './pages/VerifyEmail'
import './styles.css'

// --- Hàm lấy base URL ưu tiên runtime ---
function getApiBase() {
  // 1. runtime injection qua env.js
  if (
    typeof window !== 'undefined' &&
    window.__ENV__ &&
    typeof window.__ENV__.API_BASE === 'string' &&
    window.__ENV__.API_BASE.trim() !== ''
  ) {
    return window.__ENV__.API_BASE;
  }

  // 2. build-time fallback từ Vite lúc npm run build
  if (
    import.meta &&
    import.meta.env &&
    typeof import.meta.env.VITE_API_BASE === 'string' &&
    import.meta.env.VITE_API_BASE.trim() !== ''
  ) {
    return import.meta.env.VITE_API_BASE;
  }

  // 3. last resort cho dev local
  //return 'http://localhost:8000';
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
    localStorage.removeItem('is_admin')
    localStorage.removeItem('user_email')
    nav('/login')
  }

  return (
    <nav className="site-nav">
      <Link className="brand" to="/">Moss & Market</Link>
      <Link to="/">Shop</Link>
      {localStorage.getItem('is_admin') === 'true' && <Link to="/create">Add Product</Link>}
      <Link to="/cart">Cart</Link>
      <Link to="/orders">My Orders</Link>
      <div className="nav-actions">
        <Link to="/login">Login</Link>
        <Link to="/register">Register</Link>
        <button onClick={logout}>Logout</button>
      </div>
    </nav>
  )
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Nav />
      <Routes>
        <Route path="/" element={<Products />} />
        <Route path="/create" element={<Create />} />
        <Route path="/edit/:id" element={<Edit />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/confirm-order" element={<ConfirmOrder />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
