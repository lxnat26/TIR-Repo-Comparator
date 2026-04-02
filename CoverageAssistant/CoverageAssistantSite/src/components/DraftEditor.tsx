import { useState } from 'react'
import { analyzeDraft, AnalysisResult, ClaimResult, ClaimCategory, ClaimStatus } from '../api'

// ─── Label maps ──────────────────────────────────────────────────────────────

const CATEGORY_LABEL: Record<ClaimCategory, string> = {
  milestone: 'Milestone',
  efficacy: 'Efficacy',
  safety: 'Safety',
  regulatory: 'Regulatory',
  other: 'Other',
}

const STATUS_LABEL: Record<ClaimStatus, string> = {
  new_information: 'New Information',
  refined_detail: 'Refined Detail',
  already_reported: 'Previously Reported',
  contradiction: 'Contradiction',
  uncertainty: 'Uncertainty',
}

// ─── Claim card ──────────────────────────────────────────────────────────────

function ClaimCard({ claim }: { claim: ClaimResult }) {
  return (
    <div className={`claim-card claim-card--${claim.status}`}>
      <div className="claim-card-header">
        <span className={`badge badge--category badge--cat-${claim.category}`}>
          {CATEGORY_LABEL[claim.category]}
        </span>
        <span className={`badge badge--status badge--${claim.status}`}>
          {claim.status === 'new_information' && (
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          )}
          {claim.status === 'refined_detail' && (
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 .49-3.51" />
            </svg>
          )}
          {STATUS_LABEL[claim.status]}
        </span>
      </div>

      <h3 className="claim-card-title">{claim.title}</h3>

      {claim.previously_reported ? (
        <div className="claim-comparison">
          <div className="claim-col">
            <p className="claim-col-label">Previously Reported</p>
            <p className="claim-col-date">{claim.previously_reported.date}</p>
            <p className="claim-col-source">{claim.previously_reported.source}</p>
            <p className="claim-col-text">{claim.previously_reported.summary}</p>
          </div>
          <div className="claim-col">
            <p className="claim-col-label">
              {claim.status === 'refined_detail' ? 'Updated' : "What's New"}
            </p>
            <p className="claim-col-text">{claim.whats_new}</p>
          </div>
        </div>
      ) : (
        claim.whats_new && (
          <p className="claim-body">{claim.whats_new}</p>
        )
      )}

      <div className="claim-why">
        <svg
          className="claim-why-icon"
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <p className="claim-why-text">
          <strong>Why it matters:</strong> {claim.why_it_matters}
        </p>
      </div>
    </div>
  )
}

// ─── Empty / loading states ───────────────────────────────────────────────────

function PanelEmpty() {
  return (
    <div className="panel-empty">
      <svg
        width="32"
        height="32"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="panel-empty-icon"
        aria-hidden="true"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
      <p className="panel-empty-title">No analysis yet</p>
      <p className="panel-empty-body">
        Paste your draft on the left and click Analyze to see how each claim
        compares against the report library.
      </p>
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

// ─── Main editor ─────────────────────────────────────────────────────────────

const PLACEHOLDER =
  `Paste your competitive intelligence draft here.

The Coverage Assistant will break your draft into individual claims and compare each one against the report library, identifying what is new, what has been updated, and what was already reported.`

export function DraftEditor() {
  const [draftText, setDraftText] = useState('')
  const [competitor, setCompetitor] = useState('')
  const [drug, setDrug] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wordCount = draftText.trim() === '' ? 0 : draftText.trim().split(/\s+/).length

  async function handleAnalyze() {
    if (!draftText.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await analyzeDraft({
        text: draftText,
        metadata: {
          competitor: competitor || undefined,
          drug: drug || undefined,
        },
      })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  function handleClear() {
    setDraftText('')
    setResult(null)
    setError(null)
  }

  return (
    <div className="editor">
      {/* ── Left panel: draft input ── */}
      <div className="editor-left">
        <div className="editor-panel-header">
          <div className="editor-header-left">
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="editor-header-icon"
              aria-hidden="true"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <h2 className="editor-panel-title">Draft Report</h2>

            <div className="editor-meta-fields">
              <input
                className="meta-input"
                placeholder="Competitor"
                value={competitor}
                onChange={(e) => setCompetitor(e.target.value)}
              />
              <input
                className="meta-input"
                placeholder="Drug / Asset"
                value={drug}
                onChange={(e) => setDrug(e.target.value)}
              />
            </div>
          </div>

          <div className="editor-header-actions">
            {draftText && (
              <button className="btn btn-ghost btn-sm" onClick={handleClear}>
                Clear
              </button>
            )}
            <button
              className="btn btn-primary"
              onClick={handleAnalyze}
              disabled={loading || !draftText.trim()}
            >
              {loading ? 'Analyzing...' : 'Analyze Draft'}
            </button>
          </div>
        </div>

        <textarea
          className="editor-textarea"
          placeholder={PLACEHOLDER}
          value={draftText}
          onChange={(e) => setDraftText(e.target.value)}
          spellCheck
        />

        <div className="editor-footer">
          <span className="editor-wordcount">{wordCount} words</span>
        </div>
      </div>

      {/* ── Right panel: coverage assistant ── */}
      <div className="editor-right">
        <div className="editor-panel-header">
          <div className="editor-header-left">
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="editor-header-icon"
              aria-hidden="true"
            >
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
            <div>
              <h2 className="editor-panel-title">Coverage Assistant</h2>
              {result && (
                <p className="editor-panel-subtitle">
                  Reviewing {result.claim_count} section
                  {result.claim_count !== 1 ? 's' : ''} from your report
                </p>
              )}
            </div>
          </div>

          {result && (
            <span className="badge badge--count">
              {result.claim_count} update{result.claim_count !== 1 ? 's' : ''} found
            </span>
          )}
        </div>

        <div className="coverage-panel">
          {error && <div className="panel-error">{error}</div>}
          {!error && !result && !loading && <PanelEmpty />}
          {!error && loading && <PanelLoading />}
          {!error && !loading && result && (
            result.claims.length === 0 ? (
              <div className="panel-empty">
                <p className="panel-empty-title">No claims detected</p>
                <p className="panel-empty-body">
                  The backend did not return any comparable claims. Try adding more
                  specific factual statements to your draft.
                </p>
              </div>
            ) : (
              result.claims.map((claim) => (
                <ClaimCard key={claim.id} claim={claim} />
              ))
            )
          )}
        </div>
      </div>
    </div>
  )
}
