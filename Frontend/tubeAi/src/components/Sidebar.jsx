import { useState } from 'react'

function initialsOf(user) {
  const src = (user?.display_name || user?.email || '?').trim()
  return src.slice(0, 1).toUpperCase()
}

export default function Sidebar({
  sessions,
  currentSessionId,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
  user,
  onLogout,
  creating,
  open,
  onClose,
}) {
  const [editingId, setEditingId] = useState(null)
  const [editValue, setEditValue] = useState('')

  const startRename = (session) => {
    setEditingId(session.id)
    setEditValue(session.title || '')
  }

  const commitRename = (id) => {
    const title = editValue.trim()
    setEditingId(null)
    if (title) onRename(id, title)
  }

  const onEditKeyDown = (e, id) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      commitRename(id)
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setEditingId(null)
    }
  }

  const handleDelete = (session) => {
    if (window.confirm(`Delete "${session.title || 'this chat'}"? This can't be undone.`)) {
      onDelete(session.id)
    }
  }

  return (
    <>
      <div
        className={`sidebar-scrim ${open ? 'is-open' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside className={`sidebar ${open ? 'is-open' : ''}`} aria-label="Your chats">
        <div className="sidebar-top">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">▶</span>
            <span className="brand-name">
              Tube<span className="brand-accent">AI</span>
            </span>
          </div>
          <button
            type="button"
            className="sidebar-close"
            onClick={onClose}
            aria-label="Close menu"
          >
            ✕
          </button>
        </div>

        <button
          type="button"
          className="btn btn-primary new-chat-btn"
          onClick={onNewChat}
          disabled={creating}
        >
          {creating ? (
            <>
              <span className="spinner" aria-hidden="true" />
              Creating…
            </>
          ) : (
            <>
              <span aria-hidden="true">＋</span> New chat
            </>
          )}
        </button>

        <div className="session-list">
          {sessions.length === 0 ? (
            <p className="session-empty">No chats yet. Start one above.</p>
          ) : (
            sessions.map((s) => {
              const active = s.id === currentSessionId
              const editing = editingId === s.id
              return (
                <div
                  key={s.id}
                  className={`session-item ${active ? 'is-active' : ''}`}
                >
                  {editing ? (
                    <input
                      className="session-rename"
                      value={editValue}
                      autoFocus
                      onChange={(e) => setEditValue(e.target.value)}
                      onBlur={() => commitRename(s.id)}
                      onKeyDown={(e) => onEditKeyDown(e, s.id)}
                      aria-label="Rename chat"
                    />
                  ) : (
                    <button
                      type="button"
                      className="session-open"
                      onClick={() => onSelect(s.id)}
                      title={s.title}
                    >
                      <span className="session-emoji" aria-hidden="true">
                        {s.has_video ? '🎬' : '💬'}
                      </span>
                      <span className="session-title">{s.title || 'Untitled'}</span>
                    </button>
                  )}

                  {!editing && (
                    <div className="session-actions">
                      <button
                        type="button"
                        className="icon-btn"
                        onClick={() => startRename(s)}
                        title="Rename"
                        aria-label="Rename chat"
                      >
                        ✎
                      </button>
                      <button
                        type="button"
                        className="icon-btn icon-btn-danger"
                        onClick={() => handleDelete(s)}
                        title="Delete"
                        aria-label="Delete chat"
                      >
                        🗑
                      </button>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>

        <div className="sidebar-footer">
          <div className="account">
            <span className="account-avatar" aria-hidden="true">
              {initialsOf(user)}
            </span>
            <span className="account-email" title={user?.email}>
              {user?.display_name || user?.email}
            </span>
          </div>
          <button type="button" className="btn btn-ghost logout-btn" onClick={onLogout}>
            Log out
          </button>
        </div>
      </aside>
    </>
  )
}
