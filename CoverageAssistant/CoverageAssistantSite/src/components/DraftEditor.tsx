import { useState, useRef, useCallback, useLayoutEffect } from 'react'
import { analyzeDraft, analyzeDocument } from '../api'
import type { AnalysisResult, ClaimResult, ClaimType, ClaimStatus } from '../api'

const ACCEPTED_MIME = new Set([
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/msword',
])

// ─── Per-type color palette ───────────────────────────────────────────────────

const PALETTE: Record<ClaimType, {
  primary: string; bg: string; boxBg: string; border: string
  hlBg: string; hlBgActive: string
}> = {
  milestone: {
    primary: '#c0392b', bg: 'rgba(192,57,43,0.04)', boxBg: 'rgba(192,57,43,0.09)', border: 'rgba(192,57,43,0.22)',
    hlBg: 'rgba(192,57,43,0.13)', hlBgActive: 'rgba(192,57,43,0.24)',
  },
  efficacy: {
    primary: '#27ae60', bg: 'rgba(39,174,96,0.04)', boxBg: 'rgba(39,174,96,0.09)', border: 'rgba(39,174,96,0.22)',
    hlBg: 'rgba(39,174,96,0.13)', hlBgActive: 'rgba(39,174,96,0.24)',
  },
  safety: {
    primary: '#8a7300', bg: 'rgba(138,115,0,0.04)', boxBg: 'rgba(138,115,0,0.09)', border: 'rgba(138,115,0,0.22)',
    hlBg: 'rgba(138,115,0,0.13)', hlBgActive: 'rgba(138,115,0,0.24)',
  },
}

const TYPE_LABEL: Record<ClaimType, string> = {
  milestone: 'Milestone',
  efficacy:  'Efficacy',
  safety:    'Safety',
}

const STATUS_LABEL: Record<ClaimStatus, string> = {
  new_information:  'New',
  refined_detail:   'Refined Detail',
  already_reported: 'Already Reported',
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function IconCheck() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

function IconRefresh() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="1 4 1 10 7 10" />
      <path d="M3.51 15a9 9 0 1 0 .49-3.51" />
    </svg>
  )
}

function IconLightbulb({ color }: { color: string }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0, marginTop: 1 }}>
      <line x1="9" y1="18" x2="15" y2="18" />
      <line x1="10" y1="22" x2="14" y2="22" />
      <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14" />
    </svg>
  )
}

function IconCopy() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  )
}

// ─── Highlight helpers ────────────────────────────────────────────────────────

type Segment = { text: string; claimId?: string }

function findSentenceBounds(docText: string, phraseIdx: number): { start: number; end: number } {
  // Walk backwards to the start of the sentence
  let start = phraseIdx
  while (start > 0) {
    const c = docText[start - 1]
    if (c === '\n') break
    if ((c === '.' || c === '!' || c === '?') && /\s/.test(docText[start] ?? ' ')) break
    start--
  }
  while (start < phraseIdx && /\s/.test(docText[start])) start++

  // Walk forwards to the end of the sentence
  let end = phraseIdx
  while (end < docText.length) {
    const c = docText[end]
    end++
    if (c === '\n') break
    if ((c === '.' || c === '!' || c === '?') && (end >= docText.length || /\s/.test(docText[end]))) break
  }
  while (end > start && /\s/.test(docText[end - 1])) end--

  return { start, end }
}

function buildSegments(docText: string, claims: ClaimResult[]): Segment[] {
  const hits: { start: number; end: number; claimId: string }[] = []

  for (const claim of claims) {
    const phrase = claim.claim?.slice(0, 80)
    if (!phrase || phrase.length < 15) continue
    const idx = docText.indexOf(phrase)
    if (idx !== -1) {
      const { start, end } = findSentenceBounds(docText, idx)
      hits.push({ start, end, claimId: claim.id })
    }
  }

  hits.sort((a, b) => a.start - b.start)
  const merged: typeof hits = []
  for (const h of hits) {
    if (!merged.length || h.start >= merged[merged.length - 1].end) merged.push(h)
  }

  const segs: Segment[] = []
  let cursor = 0
  for (const { start, end, claimId } of merged) {
    if (cursor < start) segs.push({ text: docText.slice(cursor, start) })
    segs.push({ text: docText.slice(start, end), claimId })
    cursor = end
  }
  if (cursor < docText.length) segs.push({ text: docText.slice(cursor) })
  return segs
}

// ─── DocumentView ─────────────────────────────────────────────────────────────

function DocumentView({
  text, claims, activeId, onPhraseClick, setHighlightRef,
}: {
  text: string
  claims: ClaimResult[]
  activeId: string | null
  onPhraseClick: (id: string) => void
  setHighlightRef: (id: string, el: HTMLElement | null) => void
}) {
  const segments = buildSegments(text, claims)
  const claimMap = Object.fromEntries(claims.map(c => [c.id, c]))

  return (
    <>
      {segments.map((seg, i) => {
        if (!seg.claimId) return <span key={i}>{seg.text}</span>
        const claim = claimMap[seg.claimId]
        const pal = PALETTE[claim?.claim_type ?? 'milestone']
        const isActive = seg.claimId === activeId
        return (
          <mark
            key={i}
            ref={(el) => setHighlightRef(seg.claimId!, el)}
            className={`doc-highlight${isActive ? ' doc-highlight--active' : ''}`}
            style={{
              '--hl-color':      pal.primary,
              '--hl-bg':         pal.hlBg,
              '--hl-bg-active':  pal.hlBgActive,
            } as React.CSSProperties}
            onClick={() => onPhraseClick(seg.claimId!)}
          >
            {seg.text}
          </mark>
        )
      })}
    </>
  )
}

// ─── TextCollapse ─────────────────────────────────────────────────────────────

function TextCollapse({ text, quoted = false }: { text: string; quoted?: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const [overflows, setOverflows] = useState(false)
  const ref = useRef<HTMLParagraphElement>(null)

  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    // Measure with clamp applied; scrollHeight > clientHeight means it overflows
    setOverflows(el.scrollHeight > el.clientHeight + 2)
  }, [text])

  return (
    <div>
      <p
        ref={ref}
        className={`cc-compare-body${expanded ? '' : ' cc-compare-body--clamped'}`}
      >
        {quoted ? `"${text}"` : text}
      </p>
      {overflows && (
        <button
          className="cc-see-more"
          type="button"
          onClick={(e) => { e.stopPropagation(); setExpanded(v => !v) }}
        >
          {expanded ? 'See less ↑' : 'See more ↓'}
        </button>
      )}
    </div>
  )
}

// ─── ClaimCard ────────────────────────────────────────────────────────────────

function shortTitle(text: string): string {
  if (text.length <= 62) return text
  return text.slice(0, 62).replace(/\s+\S*$/, '') + '...'
}

function hasHistory(claim: ClaimResult): boolean {
  const h = claim.historical_claim?.trim()
  return !!h && h !== 'No historical matches found'
}

function ClaimCard({
  claim, active, setRef, onCardClick,
}: {
  claim: ClaimResult
  active: boolean
  setRef: (el: HTMLDivElement | null) => void
  onCardClick: (id: string) => void
}) {
  const pal = PALETTE[claim.claim_type] ?? PALETTE.milestone
  const showHistory = hasHistory(claim)

  function copyText(e: React.MouseEvent) {
    e.stopPropagation()
    navigator.clipboard.writeText(claim.claim).catch(() => {})
  }

  return (
    <div
      ref={setRef}
      className={`cc${active ? ' cc--active' : ''}`}
      style={{
        '--cc-primary': pal.primary,
        '--cc-bg':      pal.bg,
        '--cc-box-bg':  pal.boxBg,
        '--cc-border':  pal.border,
        cursor: 'pointer',
      } as React.CSSProperties}
      onClick={() => onCardClick(claim.id)}
    >
      {/* ── Badge row ── */}
      <div className="cc-header">
        <div className="cc-badges-left">
          <span className="cc-badge cc-badge--type">
            <span className="cc-dot" />
            {TYPE_LABEL[claim.claim_type].toUpperCase()}
          </span>
          {claim.specific_type && (
            <span className="cc-badge cc-badge--type">
              <span className="cc-dot" />
              {claim.specific_type.toUpperCase()}
            </span>
          )}
        </div>
        <span className="cc-badge cc-badge--status">
          {claim.classification === 'new_information'  && <IconCheck />}
          {claim.classification === 'refined_detail'   && <IconRefresh />}
          {STATUS_LABEL[claim.classification]}
        </span>
      </div>

      {/* ── Title ── */}
      <h3 className="cc-title">{shortTitle(claim.claim)}</h3>

      {/* ── Comparison box ── */}
      <div className="cc-compare">
        {showHistory ? (
          <div className="cc-compare-grid">
            <div className="cc-compare-col">
              <p className="cc-compare-heading">Previously reported:</p>
              <TextCollapse text={claim.historical_claim} quoted />
              {claim.report_date && (
                <p className="cc-compare-source">From Historical DB · {claim.report_date}</p>
              )}
            </div>
            <div className="cc-compare-col cc-compare-col--right">
              <p className="cc-compare-heading">What's new</p>
              <TextCollapse text={claim.claim} />
              <button className="cc-copy-btn" onClick={copyText} type="button">
                <IconCopy />
                Copy Text
              </button>
            </div>
          </div>
        ) : (
          <p className="cc-compare-new">This information was not in previous reports.</p>
        )}
      </div>

      {/* ── Why it matters ── */}
      <div className="cc-why">
        <IconLightbulb color={pal.primary} />
        <p className="cc-why-text">
          <strong>Why it matters: </strong>{claim.reason}
        </p>
      </div>
    </div>
  )
}

// ─── Panel states ─────────────────────────────────────────────────────────────

function PanelEmpty() {
  return (
    <div className="panel-empty">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" className="panel-empty-icon" aria-hidden="true">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
      <p className="panel-empty-title">No analysis yet</p>
      <p className="panel-empty-body">Upload a report and click Analyze Draft.</p>
    </div>
  )
}

function PanelLoading() {
  return (
    <div className="panel-loading">
      <div className="panel-spinner" />
      <p>Analyzing claims against the report library...</p>
    </div>
  )
}

// ─── DraftEditor ──────────────────────────────────────────────────────────────

export function DraftEditor({
  initialText = '',
  initialResult = null,
}: {
  initialText?: string
  initialResult?: AnalysisResult | null
}) {
  const [draftText, setDraftText]   = useState(initialText)
  const [result, setResult]         = useState<AnalysisResult | null>(initialResult)
  const [loading, setLoading]       = useState(false)
  const [uploading, setUploading]   = useState(false)
  const [error, setError]           = useState<string | null>(null)
  const [activeId, setActiveId]     = useState<string | null>(null)

  const inputRef      = useRef<HTMLInputElement>(null)
  const cardRefs      = useRef<Record<string, HTMLDivElement | null>>({})
  const highlightRefs = useRef<Record<string, HTMLElement | null>>({})

  const wordCount    = draftText.trim() === '' ? 0 : draftText.trim().split(/\s+/).length
  const pendingCount = result?.claims.length ?? 0

  // Click on a highlight → scroll the matching card into view
  const handlePhraseClick = useCallback((id: string) => {
    setActiveId(id)
    const card = cardRefs.current[id]
    if (card) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [])

  // Click on a card → scroll the matching highlight into view
  const handleCardClick = useCallback((id: string) => {
    setActiveId(id)
    const hl = highlightRefs.current[id]
    if (hl) hl.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [])

  async function handleNewFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (!f || !ACCEPTED_MIME.has(f.type)) return
    e.target.value = ''
    setUploading(true)
    setError(null)
    setResult(null)
    setActiveId(null)
    try {
      const res = await analyzeDocument(f)
      setDraftText(res.document_text ?? '')
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  async function handleAnalyze() {
    if (!draftText.trim()) return
    setLoading(true)
    setError(null)
    setActiveId(null)
    try {
      const res = await analyzeDraft({ text: draftText })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="editor">
      {/* ── Left panel ── */}
      <div className="editor-left">
        <div className="editor-panel-header">
          <div className="editor-header-left">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="editor-header-icon" aria-hidden="true">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <h2 className="editor-panel-title">Draft Report</h2>
          </div>
          <div className="editor-header-actions">
            <input ref={inputRef} type="file" accept=".pdf,.docx,.doc" onChange={handleNewFile} style={{ display: 'none' }} />
            <button className="btn btn-ghost btn-sm" onClick={() => inputRef.current?.click()} disabled={uploading || loading}>
              {uploading ? 'Uploading...' : 'Upload New Draft'}
            </button>
            <button className="btn btn-primary" onClick={handleAnalyze} disabled={loading || uploading || !draftText.trim()}>
              {loading ? 'Analyzing...' : 'Analyze Draft'}
            </button>
          </div>
        </div>

        <div className="editor-content-area">
          {result ? (
            <div className="editor-doc-text">
              <DocumentView
                text={draftText}
                claims={result.claims}
                activeId={activeId}
                onPhraseClick={handlePhraseClick}
                setHighlightRef={(id, el) => { highlightRefs.current[id] = el }}
              />
            </div>
          ) : (
            <textarea
              className="editor-textarea"
              value={draftText}
              onChange={(e) => setDraftText(e.target.value)}
              spellCheck
            />
          )}
        </div>

        <div className="editor-footer">
          <span className="editor-wordcount">{wordCount} words</span>
        </div>
      </div>

      {/* ── Right panel ── */}
      <div className="editor-right">
        <div className="editor-panel-header">
          <div className="editor-header-left">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="editor-header-icon" aria-hidden="true">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
            <div>
              <h2 className="editor-panel-title">Coverage Assistant</h2>
              {result && (
                <p className="editor-panel-subtitle">
                  Reviewing {result.claim_count} section{result.claim_count !== 1 ? 's' : ''} from your report
                </p>
              )}
            </div>
          </div>
          {result && pendingCount > 0 && (
            <span className="badge badge--count">{pendingCount} pending</span>
          )}
        </div>

        <div className="coverage-panel">
          {error && <div className="panel-error">{error}</div>}
          {!error && !result && !loading && !uploading && <PanelEmpty />}
          {!error && (loading || uploading) && <PanelLoading />}
          {!error && !loading && !uploading && result && (
            result.claims.length === 0 ? (
              <div className="panel-empty">
                <p className="panel-empty-title">No claims detected</p>
                <p className="panel-empty-body">The backend did not return any comparable claims.</p>
              </div>
            ) : (
              result.claims.map((claim) => (
                <ClaimCard
                  key={claim.id}
                  claim={claim}
                  active={claim.id === activeId}
                  setRef={(el) => { cardRefs.current[claim.id] = el }}
                  onCardClick={handleCardClick}
                />
              ))
            )
          )}
        </div>
      </div>
    </div>
  )
}
