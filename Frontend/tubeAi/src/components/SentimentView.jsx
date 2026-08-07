import { useState } from 'react'
import { analyzeSentiment } from '../api'
import Callout from './Callout'

// Backend returns a short natural-language verdict string (may be "No feedback").
export default function SentimentView({ commentCount = 0 }) {
  const [feedback, setFeedback] = useState('')
  const [status, setStatus] = useState('idle') // idle | loading | done | error
  const [error, setError] = useState('')

  const run = async () => {
    setStatus('loading')
    setError('')
    try {
      const result = await analyzeSentiment()
      setFeedback(typeof result === 'string' ? result : JSON.stringify(result))
      setStatus('done')
    } catch (e) {
      setError(e.message)
      setStatus('error')
    }
  }

  const noComments = commentCount === 0
  const noFeedback = status === 'done' && /^no feedback/i.test(feedback.trim())

  return (
    <div className="view">
      <div className="view-head">
        <div>
          <h2 className="view-title">Audience sentiment</h2>
          <p className="view-sub">
            An AI read on the comment section — whether viewers found the video
            worth watching.
          </p>
        </div>
        <div className="view-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={run}
            disabled={status === 'loading'}
          >
            {status === 'loading' ? (
              <>
                <span className="spinner" aria-hidden="true" />
                Analyzing
              </>
            ) : status === 'done' ? (
              'Re-analyze'
            ) : (
              'Analyze comments'
            )}
          </button>
        </div>
      </div>

      {noComments && (
        <Callout tone="info" title="No comments were loaded">
          This video had no fetchable comments, so sentiment may return “No
          feedback”. You can still try.
        </Callout>
      )}

      {status === 'error' && (
        <Callout tone="error" title="Couldn’t analyze sentiment">
          {error}
        </Callout>
      )}

      {status === 'idle' && !noComments && (
        <div className="empty">
          <div className="empty-icon" aria-hidden="true">💬</div>
          <p className="empty-title">{commentCount} comments loaded</p>
          <p className="empty-sub">Run the analysis to get an audience verdict.</p>
        </div>
      )}

      {status === 'loading' && (
        <div className="notes-skeleton" aria-hidden="true">
          <div className="sk sk-line" />
          <div className="sk sk-line" />
          <div className="sk sk-line short" />
        </div>
      )}

      {status === 'done' &&
        (noFeedback ? (
          <Callout tone="info" title="Not enough data">
            There weren’t enough comments to form a reliable verdict.
          </Callout>
        ) : (
          <div className="sentiment-card">
            <div className="sentiment-quote-mark" aria-hidden="true">“</div>
            <p className="sentiment-text">{feedback}</p>
            <div className="sentiment-foot">
              <span className="badge badge-ok">AI verdict</span>
              <span className="sentiment-count">
                based on {commentCount} comment{commentCount === 1 ? '' : 's'}
              </span>
            </div>
          </div>
        ))}
    </div>
  )
}
