// Shows the currently loaded video: thumbnail + transcript / comment status.
export default function VideoCard({ content }) {
  if (!content) return null

  const {
    video_id: videoId,
    transcript_provider: provider,
    transcript_language: language,
    transcript_success: success,
    transcript_message: message,
    comments = [],
  } = content

  const thumb = videoId ? `https://img.youtube.com/vi/${videoId}/hqdefault.jpg` : null
  const watchUrl = videoId ? `https://www.youtube.com/watch?v=${videoId}` : null

  return (
    <div className="video-card">
      {thumb && (
        <a className="video-thumb" href={watchUrl} target="_blank" rel="noreferrer noopener">
          <img src={thumb} alt={`Thumbnail for video ${videoId}`} />
          <span className="video-thumb-play" aria-hidden="true">▶</span>
        </a>
      )}

      <div className="video-meta">
        <div className="video-meta-head">
          <h3>Loaded video</h3>
          <span className={`badge ${success ? 'badge-ok' : 'badge-warn'}`}>
            {success ? 'Transcript ready' : 'No transcript'}
          </span>
        </div>

        <dl className="video-facts">
          <div>
            <dt>Video ID</dt>
            <dd className="mono">{videoId || '—'}</dd>
          </div>
          <div>
            <dt>Language</dt>
            <dd>{language || '—'}</dd>
          </div>
          <div>
            <dt>Source</dt>
            <dd>{provider || '—'}</dd>
          </div>
          <div>
            <dt>Comments</dt>
            <dd>{Array.isArray(comments) ? comments.length : 0}</dd>
          </div>
        </dl>

        {!success && message && <p className="video-warn">{message}</p>}
      </div>
    </div>
  )
}
