import React, { useState, useRef } from 'react'
import { analyzeDocument, analyzeDraft } from './api'
import type { AnalysisResult } from './api'
import { DraftEditor } from './components/DraftEditor'
import './App.css'

// ─── Types ────────────────────────────────────────────────────────────────────

type Screen = 'landing' | 'editor'

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

// ─── Landing Page ─────────────────────────────────────────────────────────────

interface LandingProps {
  file: File | null
  setFile: (f: File | null) => void
  onAnalyze: () => void
  analyzing: boolean
}

function Landing({ file, setFile, onAnalyze, analyzing }: LandingProps) {
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
          disabled={!file || analyzing}
        >
          {analyzing ? 'Analyzing...' : 'Analyze Document'}
        </button>
      </div>
    </div>
  )
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [screen, setScreen]               = useState<Screen>('landing')
  const [file, setFile]                   = useState<File | null>(null)
  const [analyzing, setAnalyzing]         = useState(false)
  const [extractedText, setExtractedText] = useState('')
  const [initialResult, setInitialResult] = useState<AnalysisResult | null>(null)

  async function runAnalysis(f: File) {
    setFile(f)
    setAnalyzing(true)

    try {
      // Step 1: extract text from PDF
      const extractRes = await analyzeDocument(f)
      const text = extractRes.document_text ?? ''
      setExtractedText(text)

      // Step 2: immediately run the analysis on the extracted text
      const analysisRes = await analyzeDraft({ text })
      setInitialResult(analysisRes)

      setScreen('editor')
    } catch (e) {
      console.error('Analysis failed:', e)
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
        <Landing
          file={file}
          setFile={setFile}
          onAnalyze={() => file && runAnalysis(file)}
          analyzing={analyzing}
        />
      ) : (
        <DraftEditor
          initialText={extractedText}
          initialResult={initialResult}
        />
      )}
    </div>
  )
}