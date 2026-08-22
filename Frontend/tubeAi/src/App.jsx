import { useEffect, useRef, useState } from 'react'
import {
  analyzeVideo,
  listSessions,
  createSession,
  getSession,
  renameSession,
  deleteSession,
} from './api'
import { useAuth } from './context/AuthContext'
import AuthScreen from './components/AuthScreen'
import Sidebar from './components/Sidebar'
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

// Backend chat history uses role 'assistant'; ChatView renders 'ai'.
function mapMessages(messages) {
  return (messages || []).map((m) => ({
    role: m.role === 'assistant' ? 'ai' : m.role,
    content: m.content,
  }))
}

export default function App() {
  const { user, loading: authLoading, logout } = useAuth()

  // sidebar / session list
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(null)

  // current workspace contents
  const [content, setContent] = useState(null)
  const [initialNotes, setInitialNotes] = useState('')
  const [initialMessages, setInitialMessages] = useState([])
  const [tab, setTab] = useState('notes')

  // transient status
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [booting, setBooting] = useState(false)
  const [creating, setCreating] = useState(false)
  const [sessionLoading, setSessionLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const bootstrappedRef = useRef(false)

  const resetPanels = () => {
    setContent(null)
    setInitialNotes('')
    setInitialMessages([])
    setTab('notes')
    setError('')
  }

  const hydrate = (detail) => {
    setContent(detail.video || null)
    setInitialNotes(detail.notes_markdown || '')
    setInitialMessages(mapMessages(detail.messages))
    setTab('notes')
    setError('')
  }

  const refreshSessions = async () => {
    try {
      const list = await listSessions()
      if (Array.isArray(list)) setSessions(list)
      return list
    } catch {
      return null
    }
  }

  // Bootstrap once per login: load the session list, then open the most recent
  // (or create a fresh one for a brand-new account).
  useEffect(() => {
    if (!user) {
      bootstrappedRef.current = false
      setSessions([])
      setCurrentSessionId(null)
      resetPanels()
      return
    }
    if (bootstrappedRef.current) return
    bootstrappedRef.current = true
    ;(async () => {
      setBooting(true)
      try {
        const list = await listSessions()
        if (Array.isArray(list) && list.length > 0) {
          setSessions(list)
          const detail = await getSession(list[0].id)
          setCurrentSessionId(list[0].id)
          hydrate(detail)
        } else {
          const created = await createSession()
          setSessions([created])
          setCurrentSessionId(created.id)
          resetPanels()
        }
      } catch (e) {
        setError(e.message)
      } finally {
        setBooting(false)
      }
    })()
  }, [user])

  const selectSession = async (id) => {
    if (!id || id === currentSessionId) {
      setSidebarOpen(false)
      return
    }
    setSidebarOpen(false)
    setSessionLoading(true)
    setError('')
    try {
      const detail = await getSession(id)
      setCurrentSessionId(id)
      hydrate(detail)
    } catch (e) {
      setError(e.message)
    } finally {
      setSessionLoading(false)
    }
  }

  const handleNewChat = async () => {
    if (creating) return
    setCreating(true)
    setError('')
    try {
      const created = await createSession()
      setCurrentSessionId(created.id)
      resetPanels()
      setSidebarOpen(false)
      await refreshSessions()
    } catch (e) {
      setError(e.message)
    } finally {
      setCreating(false)
    }
  }

  const handleAnalyze = async (url, lang) => {
    if (!currentSessionId) return
    setAnalyzing(true)
    setError('')
    try {
      const res = await analyzeVideo(url, lang, currentSessionId)
      setContent(res?.content || null)
      // Fresh video → no saved notes and no chat history yet.
      setInitialNotes('')
      setInitialMessages([])
      setTab('notes')
      await refreshSessions() // title becomes the video id, has_video flips on
    } catch (e) {
      setError(e.message)
      setContent(null)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleRename = async (id, title) => {
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title } : s)))
    try {
      await renameSession(id, title)
    } catch (e) {
      setError(e.message)
      await refreshSessions()
    }
  }

  const handleDelete = async (id) => {
    try {
      await deleteSession(id)
      const list = (await refreshSessions()) || []
      if (id === currentSessionId) {
        if (list.length > 0) {
          await selectSession(list[0].id)
        } else {
          const created = await createSession()
          setCurrentSessionId(created.id)
          resetPanels()
          await refreshSessions()
        }
      }
    } catch (e) {
      setError(e.message)
    }
  }

  // --- render gates ----------------------------------------------------------
  if (authLoading) {
    return (
      <div className="fullscreen-loader">
        <span className="spinner" aria-hidden="true" />
        <span>Loading…</span>
      </div>
    )
  }

  if (!user) return <AuthScreen />

  const analyzed = Boolean(content)
  const commentCount = Array.isArray(content?.comments) ? content.comments.length : 0
  const currentTitle =
    sessions.find((s) => s.id === currentSessionId)?.title || 'New chat'

  return (
    <div className="layout">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelect={selectSession}
        onNewChat={handleNewChat}
        onRename={handleRename}
        onDelete={handleDelete}
        user={user}
        onLogout={logout}
        creating={creating}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="content-col">
        <header className="content-head">
          <button
            type="button"
            className="menu-toggle"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
          >
            ☰
          </button>
          <span className="content-title" title={currentTitle}>
            {currentTitle}
          </span>
          <span className={`status-pill ${analyzed ? 'status-ready' : 'status-locked'}`}>
            <span className="status-dot" aria-hidden="true" />
            {analyzed ? 'Video loaded' : 'Awaiting a URL'}
          </span>
        </header>

        <main className="main">
          {booting || sessionLoading ? (
            <div className="session-loading">
              <span className="spinner" aria-hidden="true" />
              <span>{booting ? 'Loading your chats…' : 'Opening chat…'}</span>
            </div>
          ) : !analyzed ? (
            <section className="intro">
              <h1 className="intro-title">
                Turn any YouTube video into{' '}
                <span className="grad">notes, sentiment &amp; answers</span>
              </h1>
              <p className="intro-sub">
                Paste a link, analyze it once, then generate study notes, gauge how
                the audience felt, and chat with the transcript. This chat saves your
                work — reopen it any time.
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
          ) : (
            <>
              <section className="loaded">
                <VideoCard content={content} />
              </section>

              {error && (
                <div className="intro-error">
                  <Callout tone="error" title="Something went wrong">
                    {error}
                  </Callout>
                </div>
              )}

              <section className="workspace">
                <nav className="tabs" aria-label="Tools">
                  {TABS.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      className={`tab ${tab === t.id ? 'tab-active' : ''}`}
                      onClick={() => setTab(t.id)}
                      aria-current={tab === t.id ? 'page' : undefined}
                    >
                      <span className="tab-icon" aria-hidden="true">{t.icon}</span>
                      {t.label}
                    </button>
                  ))}
                </nav>

                {/* All three panes stay mounted so switching tabs never drops a
                    running notes stream or the current chat — they're keyed by
                    session so switching chats reseeds them from saved state. */}
                <div className="panel">
                  <div style={{ display: tab === 'notes' ? undefined : 'none' }}>
                    <NotesView
                      key={`notes-${currentSessionId}`}
                      sessionId={currentSessionId}
                      initialNotes={initialNotes}
                    />
                  </div>
                  <div style={{ display: tab === 'sentiment' ? undefined : 'none' }}>
                    <SentimentView
                      key={`sent-${currentSessionId}`}
                      sessionId={currentSessionId}
                      commentCount={commentCount}
                    />
                  </div>
                  <div style={{ display: tab === 'chat' ? undefined : 'none' }}>
                    <ChatView
                      key={`chat-${currentSessionId}`}
                      sessionId={currentSessionId}
                      initialMessages={initialMessages}
                    />
                  </div>
                </div>
              </section>
            </>
          )}
        </main>

        <footer className="footer">
          <span>TubeAI · FastAPI + React</span>
        </footer>
      </div>
    </div>
  )
}
