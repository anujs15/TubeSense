import { useState } from 'react'
import { makeNotes } from '../api'
import Markdown from './Markdown'
import Callout from './Callout'

export default function NotesView() {
  const [notes, setNotes] = useState('')
  const [status, setStatus] = useState('idle') // idle | loading | done | error
  const [error, setError] = useState('')

  const generate = async () => {
    setStatus('loading')
    setError('')
    try {
      const md = await makeNotes()
      setNotes(md)
      setStatus('done')
    } catch (e) {
      setError(e.message)
      setStatus('error')
    }
  }

  const download = () => {
    const blob = new Blob([notes], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'notes.md'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="view">
      <div className="view-head">
        <div>
          <h2 className="view-title">Study notes</h2>
          <p className="view-sub">
            A structured, blog-style write-up generated from the transcript —
            with diagrams and code where they help.
          </p>
        </div>
        <div className="view-actions">
          {status === 'done' && notes && (
            <button type="button" className="btn btn-ghost" onClick={download}>
              Download .md
            </button>
          )}
          <button
            type="button"
            className="btn btn-primary"
            onClick={generate}
            disabled={status === 'loading'}
          >
            {status === 'loading' ? (
              <>
                <span className="spinner" aria-hidden="true" />
                Generating
              </>
            ) : status === 'done' ? (
              'Regenerate'
            ) : (
              'Generate notes'
            )}
          </button>
        </div>
      </div>

      {status === 'error' && (
        <Callout tone="error" title="Couldn’t generate notes">
          {error}
        </Callout>
      )}

      {status === 'loading' && (
        <div className="notes-skeleton" aria-hidden="true">
          <div className="sk sk-title" />
          <div className="sk sk-line" />
          <div className="sk sk-line" />
          <div className="sk sk-line short" />
          <div className="sk sk-block" />
          <div className="sk sk-line" />
          <div className="sk sk-line short" />
        </div>
      )}

      {status === 'idle' && (
        <div className="empty">
          <div className="empty-icon" aria-hidden="true">📝</div>
          <p className="empty-title">No notes yet</p>
          <p className="empty-sub">
            Generating can take a moment — the model plans sections, writes them,
            and renders any diagrams.
          </p>
        </div>
      )}

      {status === 'done' &&
        (notes ? (
          <article className="notes-doc">
            <Markdown source={notes} />
          </article>
        ) : (
          <Callout tone="info" title="No notes returned">
            The backend finished but returned empty notes. Try regenerating.
          </Callout>
        ))}
    </div>
  )
}
