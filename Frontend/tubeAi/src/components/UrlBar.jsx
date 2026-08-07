import { useState } from 'react'

// A few common YouTube URL shapes -> video id, so we can validate before
// hitting the backend and give instant feedback.
function extractVideoId(url) {
  if (!url) return null
  const patterns = [
    /[?&]v=([\w-]{11})/,
    /youtu\.be\/([\w-]{11})/,
    /youtube\.com\/embed\/([\w-]{11})/,
    /youtube\.com\/shorts\/([\w-]{11})/,
    /youtube\.com\/live\/([\w-]{11})/,
  ]
  for (const re of patterns) {
    const m = url.match(re)
    if (m) return m[1]
  }
  return null
}

const LANGS = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'Hindi' },
  { code: 'es', label: 'Spanish' },
  { code: 'fr', label: 'French' },
  { code: 'de', label: 'German' },
  { code: 'pt', label: 'Portuguese' },
  { code: 'ja', label: 'Japanese' },
]

export default function UrlBar({ onAnalyze, loading }) {
  const [url, setUrl] = useState('')
  const [lang, setLang] = useState('en')

  const videoId = extractVideoId(url.trim())
  const valid = Boolean(videoId)
  const showHint = url.trim().length > 0 && !valid

  const submit = (e) => {
    e.preventDefault()
    if (!valid || loading) return
    onAnalyze(url.trim(), lang)
  }

  return (
    <form className="urlbar" onSubmit={submit}>
      <div className={`urlbar-field ${showHint ? 'urlbar-field-invalid' : ''}`}>
        <svg className="urlbar-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M10 13a5 5 0 0 0 7.07 0l3-3A5 5 0 0 0 12.9 2.9l-1.7 1.7a1 1 0 0 0 1.42 1.42l1.7-1.7a3 3 0 0 1 4.24 4.24l-3 3a3 3 0 0 1-4.24 0 1 1 0 0 0-1.42 1.42Zm4-2a5 5 0 0 0-7.07 0l-3 3A5 5 0 0 0 11.1 21.1l1.7-1.7a1 1 0 0 0-1.42-1.42l-1.7 1.7a3 3 0 0 1-4.24-4.24l3-3a3 3 0 0 1 4.24 0A1 1 0 0 0 14 11Z"
          />
        </svg>
        <input
          type="text"
          inputMode="url"
          placeholder="Paste a YouTube video URL to begin…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          aria-label="YouTube video URL"
          autoComplete="off"
        />
        <select
          className="urlbar-lang"
          value={lang}
          onChange={(e) => setLang(e.target.value)}
          aria-label="Transcript language"
          title="Transcript language"
        >
          {LANGS.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
        <button type="submit" className="btn btn-primary" disabled={!valid || loading}>
          {loading ? (
            <>
              <span className="spinner" aria-hidden="true" />
              Analyzing
            </>
          ) : (
            'Analyze'
          )}
        </button>
      </div>
      {showHint && (
        <p className="urlbar-hint">That doesn’t look like a YouTube video URL.</p>
      )}
    </form>
  )
}
