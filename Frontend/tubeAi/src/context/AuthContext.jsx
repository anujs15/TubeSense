import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import {
  getToken,
  setToken as apiSetToken,
  onUnauthorized,
  login as apiLogin,
  signup as apiSignup,
  me as apiMe,
} from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // 'loading' until the initial /auth/me check resolves, so we don't flash the
  // auth screen for an already-logged-in user on refresh.
  const [loading, setLoading] = useState(Boolean(getToken()))

  const logout = useCallback(() => {
    apiSetToken(null)
    setUser(null)
  }, [])

  // If any API call sees a 401 (expired/revoked token), drop the session.
  useEffect(() => {
    onUnauthorized(() => {
      apiSetToken(null)
      setUser(null)
    })
    return () => onUnauthorized(null)
  }, [])

  // On first load, restore the session from a persisted token.
  useEffect(() => {
    let cancelled = false
    if (!getToken()) {
      setLoading(false)
      return
    }
    ;(async () => {
      try {
        const u = await apiMe()
        if (!cancelled) setUser(u)
      } catch {
        if (!cancelled) {
          apiSetToken(null)
          setUser(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email, password) => {
    const res = await apiLogin(email, password)
    apiSetToken(res.token)
    setUser(res.user)
    return res.user
  }, [])

  const signup = useCallback(async (email, password, displayName) => {
    const res = await apiSignup(email, password, displayName)
    apiSetToken(res.token)
    setUser(res.user)
    return res.user
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
