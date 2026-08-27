import React, { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiUrl } from '../api'

function getApiBase() {
  if (
    typeof window !== 'undefined' &&
    window.__ENV__ &&
    typeof window.__ENV__.API_BASE === 'string' &&
    window.__ENV__.API_BASE.trim() !== ''
  ) {
    return window.__ENV__.API_BASE
  }

  if (
    import.meta &&
    import.meta.env &&
    typeof import.meta.env.VITE_API_BASE === 'string' &&
    import.meta.env.VITE_API_BASE.trim() !== ''
  ) {
    return import.meta.env.VITE_API_BASE
  }

  return 'http://localhost:8000'
}

const API_BASE = getApiBase()

const API = apiUrl(API_BASE)

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const [message, setMessage] = useState('Verifying your email...')
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    const token = searchParams.get('token')

    if (!token) {
      setMessage('Verification token is missing.')
      return
    }

    const verifyEmail = async () => {
      try {
        const response = await fetch(`${API}/auth/verify-email`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            token: token
          })
        })

        const data = await response.json().catch(() => ({
          detail: 'Could not reach the verification service. Open the app through the Nginx address.'
        }))

        if (!response.ok) {
          throw new Error(data.detail || 'Email verification failed')
        }

        setSuccess(true)
        setMessage('Your email has been verified successfully.')
      } catch (error) {
        setMessage(error.message)
      }
    }

    verifyEmail()
  }, [searchParams])

  return (
    <div
      style={{
        maxWidth: 600,
        margin: '60px auto',
        padding: 24,
        fontFamily: 'system-ui, sans-serif'
      }}
    >
      <h2>Email Verification</h2>

      <p>{message}</p>

      {success && (
        <p>
          <Link to="/login">Go to Login</Link>
        </p>
      )}
    </div>
  )
}
