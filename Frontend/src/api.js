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
    // FastAPI raises HTTPException -> { detail: "..." }
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

// POST /youtube/analyze — loads transcript + comments into the backend store.
// This is the gate: nothing else is allowed until this succeeds.
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

// POST /youtube/analyze_sentiment — sentiment summary of the loaded comments.
// Returns a string. Requires a video to have been analyzed first.
export function analyzeSentiment() {
  return request('/youtube/analyze_sentiment', { method: 'POST' })
}

// GET /youtube/make_notes — generates blog-style notes from the transcript.
// Returns the full graph state; the rendered markdown lives in `final`.
export async function makeNotes() {
  const state = await request('/youtube/make_notes', { method: 'GET' })
  if (typeof state === 'string') return state
  return state?.final || state?.md_with_placeholders || state?.merged_md || ''
}
