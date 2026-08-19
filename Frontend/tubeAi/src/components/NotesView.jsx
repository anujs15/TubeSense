import { useEffect, useMemo, useRef, useState } from 'react'
import { makeNotesStream } from '../api'
import Markdown from './Markdown'
import Callout from './Callout'

const STAGE_LABELS = {
  starting: 'Starting…',
  research: 'Researching sources…',
  planning: 'Planning the outline…',
  assembling: 'Assembling the document…',
  images: 'Generating diagrams…',
  finalizing: 'Finalizing…',
}

export default function NotesView() {
  const [status, setStatus] = useState('idle') 
  const [error, setError] = useState('')
  const [stage, setStage] = useState('')
  const [stageDetail, setStageDetail] = useState('')
  const [blogTitle, setBlogTitle] = useState('')
  const [outline, setOutline] = useState([]) 
  const [sectionsById, setSectionsById] = useState({}) 
  const [finalMd, setFinalMd] = useState('')

  const abortRef = useRef(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  const generate = async () => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setStatus('streaming')
    setError('')
    setStage('starting')
    setStageDetail('')
    setBlogTitle('')
    setOutline([])
    setSectionsById({})
    setFinalMd('')

    try {
      const md = await makeNotesStream(
        (evt) => {
          if (controller.signal.aborted) return
          switch (evt.type) {
            case 'stage':
              setStage(evt.stage)
              setStageDetail(evt.detail || '')
              break
            case 'plan':
              setBlogTitle(evt.blog_title || '')
              setOutline([...(evt.sections || [])].sort((a, b) => a.id - b.id))
              break
            case 'section':
              setSectionsById((prev) => ({ ...prev, [evt.id]: evt.markdown }))
              break
            default:
              break
          }
        },
        { signal: controller.signal },
      )
      if (controller.signal.aborted) return
      setFinalMd(md)
      setStatus('done')
    } catch (e) {
      if (e?.name === 'AbortError' || controller.signal.aborted) return
      setError(e.message)
      setStatus('error')
    } finally {
      if (abortRef.current === controller) abortRef.current = null
    }
  }

 
  const assembled = useMemo(() => {
    const parts = []
    if (blogTitle) parts.push(`# ${blogTitle}`)
    for (const s of outline) {
      const md = sectionsById[s.id]
      parts.push(md || `## ${s.title}\n\n_Writing this section…_`)
    }
    return parts.join('\n\n')
  }, [blogTitle, outline, sectionsById])

  const displayed = status === 'done' ? finalMd || assembled : assembled
  const downloadSource = finalMd || assembled

  const total = outline.length
  const written = outline.reduce((n, s) => n + (sectionsById[s.id] ? 1 : 0), 0)

  const statusText = useMemo(() => {
    if (!outline.length) {
      const base = STAGE_LABELS[stage] || 'Working…'
      return stageDetail ? `${base} (${stageDetail})` : base
    }
    if (written < total) return `Writing sections… ${written}/${total}`
    const base = STAGE_LABELS[stage] || 'Finalizing…'
    return stageDetail ? `${base} (${stageDetail})` : base
  }, [outline.length, written, total, stage, stageDetail])

  const download = () => {
    const blob = new Blob([downloadSource], { type: 'text/markdown;charset=utf-8' })
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
            A structured, deep-notes write-up generated from the video's
            summary — with diagrams and code where they help.
          </p>
        </div>
        <div className="view-actions">
          {status === 'done' && downloadSource && (
            <button type="button" className="btn btn-ghost" onClick={download}>
              Download .md
            </button>
          )}
          <button
            type="button"
            className="btn btn-primary"
            onClick={generate}
            disabled={status === 'streaming'}
          >
            {status === 'streaming' ? (
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

      {status === 'streaming' && (
        <>
          <div className="notes-progress" role="status" aria-live="polite">
            <span className="spinner" aria-hidden="true" />
            <span>{statusText}</span>
          </div>
          {assembled ? (
            <article className="notes-doc">
              <Markdown source={assembled} />
            </article>
          ) : (
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
        </>
      )}

      {status === 'idle' && (
        <div className="empty">
          <div className="empty-icon" aria-hidden="true">📝</div>
          <p className="empty-title">No notes yet</p>
          <p className="empty-sub">
            Generating can take a moment — the model plans sections, writes them,
            and renders any diagrams. You'll see each section appear as it's ready.
          </p>
        </div>
      )}

      {status === 'done' &&
        (displayed ? (
          <article className="notes-doc">
            <Markdown source={displayed} />
          </article>
        ) : (
          <Callout tone="info" title="No notes returned">
            The backend finished but returned empty notes. Try regenerating.
          </Callout>
        ))}
    </div>
  )
}
