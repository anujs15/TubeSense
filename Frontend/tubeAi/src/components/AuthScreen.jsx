import { useState } from 'react'
import { useAuth } from '../context/AuthContext'

export default function AuthScreen() {
  const { login, signup } = useAuth()
  const [mode, setMode] = useState('login') 
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const isSignup = mode === 'signup'

  const switchMode = (next) => {
    setMode(next)
    setError('')
  }

  const submit = async (e) => {
    e.preventDefault()
    if (busy) return
    const mail = email.trim().toLowerCase()
    if (!mail || !password) {
      setError('Email and password are required.')
      return
    }
    if (isSignup && password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }
    setBusy(true)
    setError('')
    try {
      if (isSignup) await signup(mail, password, displayName.trim())
      else await login(mail, password)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="brand-mark" aria-hidden="true">▶</span>
          <span className="brand-name">
            Tube<span className="brand-accent">AI</span>
          </span>
        </div>

        <h1 className="auth-title">
          {isSignup ? 'Create your account' : 'Welcome back'}
        </h1>
        <p className="auth-sub">
          {isSignup
            ? 'Sign up to save your notes and chats across videos.'
            : 'Log in to pick up your previous chats and notes.'}
        </p>

        <form className="auth-form" onSubmit={submit}>
          {isSignup && (
            <label className="auth-field">
              <span>Display name (optional)</span>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Ada Lovelace"
                autoComplete="name"
              />
            </label>
          )}

          <label className="auth-field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />
          </label>

          <label className="auth-field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={isSignup ? 'At least 6 characters' : '••••••••'}
              autoComplete={isSignup ? 'new-password' : 'current-password'}
              required
            />
          </label>

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="btn btn-primary auth-submit" disabled={busy}>
            {busy ? (
              <>
                <span className="spinner" aria-hidden="true" />
                {isSignup ? 'Creating account…' : 'Logging in…'}
              </>
            ) : isSignup ? (
              'Sign up'
            ) : (
              'Log in'
            )}
          </button>
        </form>

        <p className="auth-switch">
          {isSignup ? (
            <>
              Already have an account?{' '}
              <button type="button" className="link-btn" onClick={() => switchMode('login')}>
                Log in
              </button>
            </>
          ) : (
            <>
              New here?{' '}
              <button type="button" className="link-btn" onClick={() => switchMode('signup')}>
                Create an account
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  )
}
