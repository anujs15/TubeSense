import { useState } from 'react'
import { analyzeVideo } from './api'
import UrlBar from './components/UrlBar'
import VideoCard from './components/VideoCard'
import NotesView from './components/NotesView'
import SentimentView from './components/SentimentView'
import ChatView from './components/ChatView'
import Callout from './components/Callout'
import './App.css'

const TABS = [
  { id: 'notes', label: 'Notes', icon: '📝' },
  { id: 'sentiment', label: 'Sentiment', icon: '💬' },
  { id: 'chat', label: 'Chat', icon: '🤖' },
]

export default function App() {
 
  const [content, setContent] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('notes')

  const analyzed = Boolean(content)

  const handleAnalyze = async (url, lang) => {
    setAnalyzing(true)
    setError('')
    try {
      const res = await analyzeVideo(url, lang)
      setContent(res?.content || null)
      setTab('notes')
    } catch (e) {
      setError(e.message)
      setContent(null) 
    } finally {
      setAnalyzing(false)
    }
  }

  const commentCount = Array.isArray(content?.comments) ? content.comments.length : 0

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">▶</span>
          <span className="brand-name">
            Tube<span className="brand-accent">AI</span>
          </span>
        </div>
        <span className={`status-pill ${analyzed ? 'status-ready' : 'status-locked'}`}>
          <span className="status-dot" aria-hidden="true" />
          {analyzed ? 'Video loaded' : 'Awaiting a URL'}
        </span>
      </header>

      <main className="main">
        <section className="intro">
          <h1 className="intro-title">
            Turn any YouTube video into <span className="grad">notes, sentiment &amp; answers</span>
          </h1>
          <p className="intro-sub">
            Paste a link, analyze it once, then generate study notes, gauge how
            the audience felt, and chat with the transcript.
          </p>
          <UrlBar onAnalyze={handleAnalyze} loading={analyzing} />
          {error && (
            <div className="intro-error">
              <Callout tone="error" title="Analysis failed">
                {error}
              </Callout>
            </div>
          )}
        </section>

        {analyzed && (
          <section className="loaded">
            <VideoCard content={content} />
          </section>
        )}

        <section className="workspace">
          <nav className="tabs" aria-label="Tools">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`tab ${tab === t.id ? 'tab-active' : ''}`}
                onClick={() => setTab(t.id)}
                disabled={!analyzed}
                aria-current={tab === t.id ? 'page' : undefined}
              >
                <span className="tab-icon" aria-hidden="true">{t.icon}</span>
                {t.label}
                {!analyzed && (
                  <span className="tab-lock" aria-hidden="true">🔒</span>
                )}
              </button>
            ))}
          </nav>

          <div className="panel">
            {!analyzed ? (
              <div className="locked">
                <div className="locked-icon" aria-hidden="true">🔒</div>
                <h2 className="locked-title">Paste a URL to unlock the tools</h2>
                <p className="locked-sub">
                  Notes, sentiment, and chat all read from the video you analyze.
                  Until a video is loaded, these actions stay disabled — so no
                  request runs against an empty backend.
                </p>
                <ul className="locked-steps">
                  <li><span className="step-n">1</span> Paste a YouTube URL above</li>
                  <li><span className="step-n">2</span> Hit <strong>Analyze</strong> to load its transcript &amp; comments</li>
                  <li><span className="step-n">3</span> Generate notes, sentiment &amp; chat</li>
                </ul>
              </div>
            ) : (
              <>
                {tab === 'notes' && <NotesView />}
                {tab === 'sentiment' && <SentimentView commentCount={commentCount} />}
                {tab === 'chat' && <ChatView />}
              </>
            )}
          </div>
        </section>
      </main>

      <footer className="footer">
        <span>TubeAI · FastAPI + React</span>
      </footer>
    </div>
  )
}
