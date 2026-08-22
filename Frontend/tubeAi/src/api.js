import { API_BASE } from './config'

const JSON_HEADERS = { 'Content-Type': 'application/json' }
const TOKEN_KEY = 'tubeai_token'

// --- auth token store (persisted in localStorage) ---------------------------
let _token = localStorage.getItem(TOKEN_KEY) || null
let _onUnauthorized = null

export function getToken() {
  return _token
}

export function setToken(token) {
  _token = token || null
  if (_token) localStorage.setItem(TOKEN_KEY, _token)
  else localStorage.removeItem(TOKEN_KEY)
}

// Register a callback fired whenever the API sees a 401 — lets AuthContext log
// the user out if the token expires or is revoked.
export function onUnauthorized(fn) {
  _onUnauthorized = fn
}

function authHeaders(extra = {}) {
  const h = { ...extra }
  if (_token) h.Authorization = `Bearer ${_token}`
  return h
}

async function request(path, options = {}) {
  let res
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: authHeaders(options.headers),
    })
  } catch {
    throw new Error(
      'Cannot reach the backend. Make sure the FastAPI server is running (uvicorn main:app) on port 8000.',
    )
  }

  const contentType = res.headers.get('content-type') || ''
  const data = contentType.includes('application/json')
    ? await res.json()
    : await res.text()

  if (!res.ok) {
    if (res.status === 401) _onUnauthorized?.()

    let detail
    if (data && typeof data === 'object') detail = data.detail
    else if (typeof data === 'string' && data.trim()) detail = data

    if (res.status === 429) {
      detail = detail || 'The upstream service is rate-limited. Please wait a bit and try again.'
    }

    const err = new Error(detail || `Request failed (${res.status})`)
    err.status = res.status
    throw err
  }

  return data
}

// --- auth --------------------------------------------------------------------
export function signup(email, password, displayName = '') {
  return request('/auth/signup', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ email, password, display_name: displayName }),
  })
}

export function login(email, password) {
  return request('/auth/login', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ email, password }),
  })
}

export function me() {
  return request('/auth/me', { method: 'GET' })
}

// --- sessions (workspaces) ---------------------------------------------------
export function listSessions() {
  return request('/sessions', { method: 'GET' })
}

export function createSession() {
  return request('/sessions', { method: 'POST' })
}

export function getSession(id) {
  return request(`/sessions/${encodeURIComponent(id)}`, { method: 'GET' })
}

export function renameSession(id, title) {
  return request(`/sessions/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: JSON_HEADERS,
    body: JSON.stringify({ title }),
  })
}

export function deleteSession(id) {
  return request(`/sessions/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

// --- youtube tools (scoped to a session) -------------------------------------
export function analyzeVideo(url, lang = 'en', sessionId) {
  return request('/youtube/analyze', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ url, lang, session_id: sessionId }),
  })
}

// POST /youtube/chat — RAG Q&A over the session's transcript. Returns a string.
export function chat(userQuery, sessionId) {
  return request('/youtube/chat', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ user_query: userQuery, session_id: sessionId }),
  })
}

export function analyzeSentiment(sessionId) {
  return request(`/youtube/analyze_sentiment?session_id=${encodeURIComponent(sessionId)}`, {
    method: 'POST',
  })
}

export async function makeNotes(sessionId) {
  const state = await request(
    `/youtube/make_notes?session_id=${encodeURIComponent(sessionId)}`,
    { method: 'GET' },
  )
  if (typeof state === 'string') return state
  return state?.final || state?.md_with_placeholders || state?.merged_md || ''
}

export async function makeNotesStream(onEvent, { signal, sessionId } = {}) {
  let res
  try {
    res = await fetch(
      `${API_BASE}/youtube/make_notes/stream?session_id=${encodeURIComponent(sessionId)}`,
      {
        method: 'GET',
        headers: authHeaders({ Accept: 'application/x-ndjson' }),
        signal,
      },
    )
  } catch (e) {
    if (e?.name === 'AbortError') throw e
    throw new Error(
      'Cannot reach the backend. Make sure the FastAPI server is running (uvicorn main:app) on port 8000.',
    )
  }

  if (!res.ok || !res.body) {
    if (res.status === 401) _onUnauthorized?.()
    let detail
    try {
      const j = await res.json()
      detail = j?.detail
    } catch {
      /* non-JSON / empty error body */
    }
    if (res.status === 429) {
      detail = detail || 'The upstream service is rate-limited. Please wait a bit and try again.'
    }
    const err = new Error(detail || `Request failed (${res.status})`)
    err.status = res.status
    throw err
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalMd = ''

  const handleLine = (line) => {
    const trimmed = line.trim()
    if (!trimmed) return
    let evt
    try {
      evt = JSON.parse(trimmed)
    } catch {
      return
    }
    if (evt.type === 'error') {
      const err = new Error(evt.detail || 'Notes generation failed.')
      err.status = evt.status
      throw err
    }
    if (evt.type === 'final') finalMd = evt.markdown || finalMd
    onEvent?.(evt)
  }

  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let nl
      while ((nl = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, nl)
        buffer = buffer.slice(nl + 1)
        handleLine(line)
      }
    }
    if (buffer.trim()) handleLine(buffer)
  } finally {
    try {
      reader.releaseLock()
    } catch {
      /* already released */
    }
  }

  return finalMd
}


export async function downloadNotesPdf(sessionId) {
  let res
  try {
    res = await fetch(
      `${API_BASE}/youtube/notes/pdf?session_id=${encodeURIComponent(sessionId)}`,
      { method: 'GET', headers: authHeaders() },
    )
  } catch {
    throw new Error(
      'Cannot reach the backend. Make sure the FastAPI server is running (uvicorn main:app) on port 8000.',
    )
  }

  if (!res.ok) {
    if (res.status === 401) _onUnauthorized?.()
    let detail
    try {
      const j = await res.json()
      detail = j?.detail
    } catch {
      /* non-JSON / empty error body */
    }
    const err = new Error(detail || `Request failed (${res.status})`)
    err.status = res.status
    throw err
  }

  return await res.blob()
}
