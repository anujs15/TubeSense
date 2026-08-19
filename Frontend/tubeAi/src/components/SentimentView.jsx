import { useState } from 'react'
import { analyzeSentiment } from '../api'
import Callout from './Callout'

export default function SentimentView({ commentCount = 0 }) {
  const [feedback, setFeedback] = useState('')
  const [status, setStatus] = useState('idle') // idle | loading | done | error
  const [error, setError] = useState('')

  
  const noComments = commentCount === 0

  const run = async () => {
    if (noComments) return // locked — nothing to analyze
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
            disabled={noComments || status === 'loading'}
            title={noComments ? 'No comments available to analyze' : undefined}
          >
            {noComments ? (
              <>
                <span aria-hidden="true">🔒</span>
                Analyze comments
              </>
            ) : status === 'loading' ? (
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

      {noComments ? (
        // Locked state: transcript loaded but no comments could be fetched.
        <div className="empty">
          <div className="empty-icon" aria-hidden="true">🔒</div>
          <p className="empty-title">No comments available to analyze</p>
          <p className="empty-sub">
            The transcript loaded fine, but this video&rsquo;s comments
            couldn&rsquo;t be fetched — so sentiment analysis is unavailable.
            Notes and chat still work.
          </p>
        </div>
      ) : (
        <>
          {status === 'error' && (
            <Callout tone="error" title="Couldn’t analyze sentiment">
              {error}
            </Callout>
          )}

          {status === 'idle' && (
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
                There weren&rsquo;t enough comments to form a reliable verdict.
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
        </>
      )}
    </div>
  )
}
