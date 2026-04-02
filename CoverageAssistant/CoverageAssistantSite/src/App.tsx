import React, { useState, useRef } from 'react'
import { analyzeDocument } from './api'
import type { ClaimResult, AnalysisResult } from './api'
import './App.css'

// ─── Types ────────────────────────────────────────────────────────────────────

type Screen = 'landing' | 'analysis'

const ACCEPTED_MIME = new Set([
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/msword',
])

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`
  return `${(b / (1024 * 1024)).toFixed(1)} MB`
}

function fileExt(file: File) {
  return file.name.split('.').pop()?.toUpperCase() ?? 'FILE'
}

// ─── Label maps ───────────────────────────────────────────────────────────────

const CATEGORY_LABEL: Record<string, string> = {
  milestone:  'Milestone',
  efficacy:   'Efficacy',
  safety:     'Safety',
  regulatory: 'Regulatory',
  other:      'Other',
}

const STATUS_LABEL: Record<string, string> = {
  new_information:  'New Information',
  refined_detail:   'Refined Detail',
  already_reported: 'Previously Reported',
  contradiction:    'Contradiction',
  uncertainty:      'Uncertainty',
}

// ─── Claim Card ───────────────────────────────────────────────────────────────

function ClaimCard({ claim }: { claim: ClaimResult }) {
  return (
    <div className={`claim-card claim-card--${claim.status}`}>
      <div className="claim-tags">
        <span className="claim-tag">
          {CATEGORY_LABEL[claim.category] ?? claim.category}
        </span>
        <span className={`claim-tag claim-tag--status-${claim.status}`}>
          {STATUS_LABEL[claim.status] ?? claim.status}
        </span>
      </div>

      <h3 className="claim-title">{claim.title}</h3>

      {claim.previously_reported ? (
        <div className="claim-comparison">
          <div>
            <span className="claim-col-header">Previously Reported</span>
            <span className="claim-col-date">{claim.previously_reported.date}</span>
            <span className="claim-col-source">{claim.previously_reported.source}</span>
            <p className="claim-col-body">{claim.previously_reported.summary}</p>
          </div>
          <div>
            <span className="claim-col-header">
              {claim.status === 'refined_detail' ? 'Updated' : "What's New"}
            </span>
            <p className="claim-col-body">{claim.whats_new}</p>
          </div>
        </div>
      ) : (
        claim.whats_new && <p className="claim-new-body">{claim.whats_new}</p>
      )}

      <div className="claim-why">
        <p className="claim-why-text">
          <span className="claim-why-label">Why it matters</span>
          {claim.why_it_matters}
        </p>
      </div>
    </div>
  )
}

// ─── Upload Zone ──────────────────────────────────────────────────────────────

interface UploadZoneProps {
  file: File | null
  onFile: (f: File) => void
  error: string
  onError: (e: string) => void
}

function UploadZone({ file, onFile, error, onError }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function validate(f: File): boolean {
    if (!ACCEPTED_MIME.has(f.type)) {
      onError('Unsupported file type. Please upload a PDF or Word document.')
      return false
    }
    if (f.size > 50 * 1024 * 1024) {
      onError('File exceeds 50 MB.')
      return false
    }
    onError('')
    return true
  }

  function pick(f: File) {
    if (validate(f)) onFile(f)
  }

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) pick(f)
  }

  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) pick(f)
    e.target.value = ''
  }

  return (
    <div
      className={`upload-zone${dragging ? ' upload-zone--over' : ''}${file ? ' upload-zone--filled' : ''}`}
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.doc"
        onChange={onChange}
        style={{ display: 'none' }}
      />

      {file ? (
        <div className="upload-zone-file">
          <span className="upload-zone-ext">{fileExt(file)}</span>
          <div className="upload-zone-file-info">
            <span className="upload-zone-filename">{file.name}</span>
            <span className="upload-zone-filesize">{formatBytes(file.size)}</span>
          </div>
          <span className="upload-zone-change">Change file</span>
        </div>
      ) : (
        <div className="upload-zone-empty">
          <p className="upload-zone-label">
            Drop your report here or <span className="upload-zone-link">browse</span>
          </p>
          <p className="upload-zone-hint">PDF and Word documents — max 50 MB</p>
        </div>
      )}

      {error && (
        <p className="upload-zone-error" onClick={e => e.stopPropagation()}>
          {error}
        </p>
      )}
    </div>
  )
}

// ─── Sidebar states ───────────────────────────────────────────────────────────

function SidebarAnalyzing() {
  return (
    <div className="sidebar-state">
      <span className="analyzing-label">Analyzing document</span>
    </div>
  )
}

function SidebarError({ message }: { message: string }) {
  return (
    <div className="sidebar-error">
      <span className="sidebar-error-label">Connection Error</span>
      <p className="sidebar-error-title">Backend not connected</p>
      <p className="sidebar-error-body">{message}</p>
      <p className="sidebar-error-hint">
        Start the FastAPI server on localhost:8000, then re-analyze.
      </p>
    </div>
  )
}

// ─── Landing Page ─────────────────────────────────────────────────────────────

interface LandingProps {
  file: File | null
  setFile: (f: File | null) => void
  onAnalyze: () => void
}

function Landing({ file, setFile, onAnalyze }: LandingProps) {
  const [uploadError, setUploadError] = useState('')

  return (
    <div className="landing">
      <div className="landing-left">
        <span className="landing-overline">AbbVie · CI Platform</span>
        <h1 className="landing-headline">
          Competitive<br />Intelligence<br />Analysis
        </h1>
        <div className="landing-rule" />
      </div>

      <div className="landing-right">
        <span className="form-label">Report Draft</span>
        <UploadZone
          file={file}
          onFile={setFile}
          error={uploadError}
          onError={setUploadError}
        />
        <button
          className="analyze-btn"
          onClick={onAnalyze}
          disabled={!file}
        >
          Analyze Document
        </button>
      </div>
    </div>
  )
}

// ─── Analysis View ────────────────────────────────────────────────────────────

interface AnalysisProps {
  file: File
  analyzing: boolean
  result: AnalysisResult | null
  error: string | null
  onNewFile: (f: File) => void
}

function AnalysisView({ file, analyzing, result, error, onNewFile }: AnalysisProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (!f) return
    if (!ACCEPTED_MIME.has(f.type)) return
    e.target.value = ''
    onNewFile(f)
  }

  return (
    <div className="analysis">
      <div className="draft-panel">
        <div className="draft-header">
          <span className="draft-panel-label">Draft Report</span>
          <div className="draft-header-right">
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.doc"
              onChange={onChange}
              style={{ display: 'none' }}
            />
            <button className="text-btn" onClick={() => inputRef.current?.click()}>
              Upload different file
            </button>
          </div>
        </div>

        <div className="doc-info">
          <span className="doc-ext">{fileExt(file)}</span>
          <div className="doc-info-meta">
            <p className="doc-filename">{file.name}</p>
            <p className="doc-filesize">{formatBytes(file.size)}</p>
          </div>
        </div>

        {result?.document_text && (
          <div className="doc-text-area">
            <p className="doc-text-label">Extracted Text</p>
            <div className="doc-text-body">{result.document_text}</div>
          </div>
        )}

        {!result?.document_text && !analyzing && <div className="doc-placeholder" />}
      </div>

      <div className="sidebar">
        <div className="sidebar-header">
          <div>
            <h2 className="sidebar-title">Coverage Assistant</h2>
            {result && (
              <p className="sidebar-sub">
                {result.claim_count} section{result.claim_count !== 1 ? 's' : ''} reviewed
              </p>
            )}
          </div>
          {result && (
            <span className="sidebar-count">
              {result.claim_count} update{result.claim_count !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        <div className="sidebar-body">
          {analyzing && <SidebarAnalyzing />}
          {!analyzing && error && <SidebarError message={error} />}
          {!analyzing && !error && result && result.claims.length === 0 && (
            <div className="sidebar-state">No comparable claims detected.</div>
          )}
          {!analyzing && !error && result && result.claims.map(c => (
            <ClaimCard key={c.id} claim={c} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [screen, setScreen]   = useState<Screen>('landing')
  const [file, setFile]       = useState<File | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult]   = useState<AnalysisResult | null>(null)
  const [error, setError]     = useState<string | null>(null)

  async function runAnalysis(f: File) {
    setFile(f)
    setAnalyzing(true)
    setResult(null)
    setError(null)
    setScreen('analysis')

    try {
      const res = await analyzeDocument(f)
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed.')
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="app">
      <header className="nav">
        <div className="nav-inner">
          <span className="nav-brand">Coverage Assistant</span>
          <span className="nav-label">AbbVie · Competitive Intelligence</span>
        </div>
      </header>

      {screen === 'landing' ? (
        <Landing file={file} setFile={setFile} onAnalyze={() => file && runAnalysis(file)} />
      ) : (
        <AnalysisView
          file={file!}
          analyzing={analyzing}
          result={result}
          error={error}
          onNewFile={runAnalysis}
        />
      )}
    </div>
  )
}
