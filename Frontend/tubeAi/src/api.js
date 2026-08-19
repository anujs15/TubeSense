import { API_BASE } from './config'

const JSON_HEADERS = { 'Content-Type': 'application/json' }

async function request(path, options = {}) {
  let res
  try {
    res = await fetch(`${API_BASE}${path}`, options)
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


export function analyzeVideo(url, lang = 'en') {
  return request('/youtube/analyze', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ url, lang }),
  })
}

// POST /youtube/chat — RAG Q&A over the loaded transcript. Returns a string.
export function chat(userQuery) {
  return request('/youtube/chat', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ user_query: userQuery }),
  })
}


export function analyzeSentiment() {
  return request('/youtube/analyze_sentiment', { method: 'POST' })
}


export async function makeNotes() {
  const state = await request('/youtube/make_notes', { method: 'GET' })
  if (typeof state === 'string') return state
  return state?.final || state?.md_with_placeholders || state?.merged_md || ''
}


export async function makeNotesStream(onEvent, { signal } = {}) {
  let res
  try {
    res = await fetch(`${API_BASE}/youtube/make_notes/stream`, {
      method: 'GET',
      headers: { Accept: 'application/x-ndjson' },
      signal,
    })
  } catch (e) {
    if (e?.name === 'AbortError') throw e
    throw new Error(
      'Cannot reach the backend. Make sure the FastAPI server is running (uvicorn main:app) on port 8000.',
    )
  }

  if (!res.ok || !res.body) {
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
