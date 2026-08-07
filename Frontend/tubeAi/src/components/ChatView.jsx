import { useRef, useState, useEffect } from 'react'
import { chat } from '../api'
import Markdown from './Markdown'

const SUGGESTIONS = [
  'Summarize this video in 3 bullet points',
  'What are the key takeaways?',
  'Explain the main concept simply',
]

export default function ChatView() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, sending])

  const send = async (text) => {
    const query = (text ?? input).trim()
    if (!query || sending) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: query }])
    setSending(true)
    try {
      const reply = await chat(query)
      setMessages((m) => [...m, { role: 'ai', content: String(reply) }])
    } catch (e) {
      setMessages((m) => [...m, { role: 'error', content: e.message }])
    } finally {
      setSending(false)
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="view chat-view">
      <div className="view-head">
        <div>
          <h2 className="view-title">Ask the video</h2>
          <p className="view-sub">
            Grounded Q&amp;A over the transcript — answers cite what was actually
            said.
          </p>
        </div>
      </div>

      <div className="chat-window" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="empty-icon" aria-hidden="true">🤖</div>
            <p className="empty-title">Ask anything about this video</p>
            <div className="chat-suggestions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="chip"
                  onClick={() => send(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`bubble bubble-${m.role}`}>
            {m.role === 'ai' ? (
              <Markdown source={m.content} />
            ) : (
              <span>{m.content}</span>
            )}
          </div>
        ))}

        {sending && (
          <div className="bubble bubble-ai">
            <span className="typing" aria-label="Thinking">
              <i />
              <i />
              <i />
            </span>
          </div>
        )}
      </div>

      <div className="chat-composer">
        <textarea
          rows={1}
          placeholder="Ask a question about the video…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          aria-label="Your question"
        />
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => send()}
          disabled={sending || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  )
}
