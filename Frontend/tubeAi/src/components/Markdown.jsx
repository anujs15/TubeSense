import { useMemo, useState } from 'react'
import { resolveAsset } from '../config'


const INLINE_PATTERNS = [
  { type: 'code', re: /`([^`]+)`/ },
  { type: 'image', re: /!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/ },
  { type: 'link', re: /\[([^\]]+)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/ },
  { type: 'bold', re: /\*\*([^*]+)\*\*/ },
  { type: 'italic', re: /\*([^*]+)\*/ },
  { type: 'strike', re: /~~([^~]+)~~/ },
]

function renderInline(text, keyPrefix = 'i') {
  const nodes = []
  let rest = String(text)
  let n = 0

  while (rest) {
    let best = null
    for (const p of INLINE_PATTERNS) {
      const m = p.re.exec(rest)
      if (m && (best === null || m.index < best.m.index)) {
        best = { p, m }
        if (m.index === 0) break
      }
    }

    if (!best) {
      nodes.push(rest)
      break
    }

    const { p, m } = best
    if (m.index > 0) nodes.push(rest.slice(0, m.index))
    const key = `${keyPrefix}-${n++}`

    if (p.type === 'code') {
      nodes.push(
        <code key={key} className="md-code-inline">
          {m[1]}
        </code>,
      )
    } else if (p.type === 'image') {
      nodes.push(
        <img
          key={key}
          className="md-inline-img"
          src={resolveAsset(m[2])}
          alt={m[1]}
          loading="lazy"
        />,
      )
    } else if (p.type === 'link') {
      nodes.push(
        <a key={key} href={m[2]} target="_blank" rel="noreferrer noopener">
          {renderInline(m[1], key)}
        </a>,
      )
    } else if (p.type === 'bold') {
      nodes.push(<strong key={key}>{renderInline(m[1], key)}</strong>)
    } else if (p.type === 'italic') {
      nodes.push(<em key={key}>{renderInline(m[1], key)}</em>)
    } else if (p.type === 'strike') {
      nodes.push(<del key={key}>{renderInline(m[1], key)}</del>)
    }

    rest = rest.slice(m.index + m[0].length)
  }

  return nodes
}


const RE = {
  heading: /^(#{1,6})\s+(.*)$/,
  fence: /^\s*(`{3,}|~{3,})\s*([\w+-]*)\s*$/,
  hr: /^\s*(-{3,}|\*{3,}|_{3,})\s*$/,
  quote: /^\s*>/,
  ul: /^\s*[-*+]\s+/,
  ol: /^\s*\d+\.\s+/,
  imageOnly: /^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)$/,
}

function splitRow(line) {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((c) => c.trim())
}

function isBlockStart(line) {
  return (
    RE.heading.test(line) ||
    RE.fence.test(line) ||
    RE.hr.test(line) ||
    RE.quote.test(line) ||
    RE.ul.test(line) ||
    RE.ol.test(line)
  )
}

function parseBlocks(md) {
  const lines = String(md).replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    if (line.trim() === '') {
      i++
      continue
    }

    // fenced code block
    const fence = line.match(RE.fence)
    if (fence) {
      const marker = fence[1][0]
      const lang = fence[2] || ''
      const buf = []
      i++
      const close = new RegExp(`^\\s*\\${marker}{3,}\\s*$`)
      while (i < lines.length && !close.test(lines[i])) {
        buf.push(lines[i])
        i++
      }
      i++ // skip closing fence
      blocks.push({ type: 'code', lang, code: buf.join('\n') })
      continue
    }

    // heading
    const h = line.match(RE.heading)
    if (h) {
      blocks.push({ type: 'heading', level: h[1].length, text: h[2].replace(/\s+#+\s*$/, '') })
      i++
      continue
    }

    // horizontal rule
    if (RE.hr.test(line)) {
      blocks.push({ type: 'hr' })
      i++
      continue
    }

    // blockquote
    if (RE.quote.test(line)) {
      const buf = []
      while (i < lines.length && RE.quote.test(lines[i])) {
        buf.push(lines[i].replace(/^\s*>\s?/, ''))
        i++
      }
      blocks.push({ type: 'quote', children: parseBlocks(buf.join('\n')) })
      continue
    }

    if (
      line.includes('|') &&
      i + 1 < lines.length &&
      lines[i + 1].includes('-') &&
      /^\s*\|?[\s:|-]+\|?\s*$/.test(lines[i + 1])
    ) {
      const header = splitRow(line)
      const aligns = splitRow(lines[i + 1]).map((c) => {
        const l = c.startsWith(':')
        const r = c.endsWith(':')
        return l && r ? 'center' : r ? 'right' : l ? 'left' : null
      })
      i += 2
      const rows = []
      while (i < lines.length && lines[i].includes('|') && lines[i].trim() !== '') {
        rows.push(splitRow(lines[i]))
        i++
      }
      blocks.push({ type: 'table', header, aligns, rows })
      continue
    }

    if (RE.ul.test(line) || RE.ol.test(line)) {
      const ordered = RE.ol.test(line)
      const marker = ordered ? RE.ol : RE.ul
      const itemRe = ordered ? /^\s*\d+\.\s+(.*)$/ : /^\s*[-*+]\s+(.*)$/
      const items = []
      while (i < lines.length && marker.test(lines[i])) {
        const m = lines[i].match(itemRe)
        const itemLines = [m[1]]
        i++
        while (
          i < lines.length &&
          lines[i].trim() !== '' &&
          /^\s{2,}\S/.test(lines[i]) &&
          !RE.ul.test(lines[i]) &&
          !RE.ol.test(lines[i])
        ) {
          itemLines.push(lines[i].trim())
          i++
        }
        items.push(itemLines.join(' '))
      }
      blocks.push({ type: 'list', ordered, items })
      continue
    }

    const img = line.trim().match(RE.imageOnly)
    if (img) {
      let caption = ''
      if (i + 1 < lines.length && /^\s*\*[^*].*\*\s*$/.test(lines[i + 1])) {
        caption = lines[i + 1].trim().replace(/^\*|\*$/g, '')
        i++
      }
      blocks.push({ type: 'image', alt: img[1], src: img[2], caption })
      i++
      continue
    }

    // paragraph
    const buf = [line]
    i++
    while (i < lines.length && lines[i].trim() !== '' && !isBlockStart(lines[i])) {
      buf.push(lines[i])
      i++
    }
    blocks.push({ type: 'paragraph', text: buf.join('\n') })
  }

  return blocks
}

// ---- components ------------------------------------------------------------

function CodeBlock({ code, lang }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard blocked — ignore */
    }
  }

  return (
    <div className="md-codeblock">
      <div className="md-codeblock-bar">
        <span className="md-codeblock-lang">{lang || 'code'}</span>
        <button type="button" className="md-copy" onClick={copy}>
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="md-pre">
        <code>{code}</code>
      </pre>
    </div>
  )
}

function MdImage({ src, alt, caption }) {
  const [failed, setFailed] = useState(false)

  if (failed) {
    return (
      <figure className="md-figure md-figure-failed">
        <div className="md-image-fallback">
          <span className="md-image-fallback-icon" aria-hidden="true">
            🖼️
          </span>
          <span>{alt || caption || 'Image unavailable'}</span>
        </div>
        {caption && <figcaption>{renderInline(caption)}</figcaption>}
      </figure>
    )
  }

  return (
    <figure className="md-figure">
      <img
        src={resolveAsset(src)}
        alt={alt}
        loading="lazy"
        onError={() => setFailed(true)}
      />
      {caption && <figcaption>{renderInline(caption)}</figcaption>}
    </figure>
  )
}

function renderBlock(b, key) {
  switch (b.type) {
    case 'heading': {
      const Tag = `h${b.level}`
      return (
        <Tag key={key} className={`md-h md-h${b.level}`}>
          {renderInline(b.text, key)}
        </Tag>
      )
    }
    case 'paragraph':
      return (
        <p key={key} className="md-p">
          {renderInline(b.text, key)}
        </p>
      )
    case 'hr':
      return <hr key={key} className="md-hr" />
    case 'code':
      return <CodeBlock key={key} code={b.code} lang={b.lang} />
    case 'quote':
      return (
        <blockquote key={key} className="md-quote">
          {b.children.map((c, idx) => renderBlock(c, `${key}-${idx}`))}
        </blockquote>
      )
    case 'list': {
      const Tag = b.ordered ? 'ol' : 'ul'
      return (
        <Tag key={key} className="md-list">
          {b.items.map((it, idx) => (
            <li key={idx} className="md-li">
              {renderInline(it, `${key}-${idx}`)}
            </li>
          ))}
        </Tag>
      )
    }
    case 'image':
      return <MdImage key={key} src={b.src} alt={b.alt} caption={b.caption} />
    case 'table':
      return (
        <div key={key} className="md-table-wrap">
          <table className="md-table">
            <thead>
              <tr>
                {b.header.map((c, idx) => (
                  <th key={idx} style={{ textAlign: b.aligns[idx] || 'left' }}>
                    {renderInline(c, `${key}-h${idx}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {b.rows.map((row, r) => (
                <tr key={r}>
                  {row.map((c, idx) => (
                    <td key={idx} style={{ textAlign: b.aligns[idx] || 'left' }}>
                      {renderInline(c, `${key}-r${r}c${idx}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    default:
      return null
  }
}

export default function Markdown({ source }) {
  const blocks = useMemo(() => parseBlocks(source || ''), [source])
  return <div className="md">{blocks.map((b, i) => renderBlock(b, `b-${i}`))}</div>
}
