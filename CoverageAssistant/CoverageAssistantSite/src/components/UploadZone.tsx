import { useRef, useState, DragEvent, ChangeEvent } from 'react'
import { uploadDocument, ReportDocument } from '../api'

const ACCEPTED_MIME = new Set([
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/msword',
])

const MAX_BYTES = 50 * 1024 * 1024 // 50 MB

interface UploadZoneProps {
  onUploadComplete: (doc: ReportDocument) => void
}

export function UploadZone({ onUploadComplete }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function validate(file: File): string | null {
    if (!ACCEPTED_MIME.has(file.type)) {
      return 'Unsupported file type. Please upload a PDF or Word document (.pdf, .docx).'
    }
    if (file.size > MAX_BYTES) {
      return 'File exceeds the 50 MB limit.'
    }
    return null
  }

  async function processFile(file: File) {
    const err = validate(file)
    if (err) {
      setError(err)
      return
    }
    setError(null)
    setUploading(true)
    try {
      const doc = await uploadDocument(file)
      onUploadComplete(doc)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed. Is the backend running?')
    } finally {
      setUploading(false)
    }
  }

  function onDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragging(true)
  }

  function onDragLeave(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragging(false)
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) processFile(file)
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) processFile(file)
    e.target.value = ''
  }

  const zoneClass = [
    'upload-zone',
    isDragging ? 'upload-zone--dragging' : '',
    uploading ? 'upload-zone--uploading' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div
      className={zoneClass}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => !uploading && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && !uploading && inputRef.current?.click()}
      aria-label="Upload document"
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.doc"
        onChange={onChange}
        style={{ display: 'none' }}
      />

      {uploading ? (
        <div className="upload-zone-content">
          <div className="upload-spinner" />
          <p className="upload-zone-text">Uploading and ingesting document...</p>
        </div>
      ) : (
        <div className="upload-zone-content">
          <div className="upload-zone-icon">
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <p className="upload-zone-text">
            Drop a PDF or Word document here, or{' '}
            <span className="upload-zone-link">click to browse</span>
          </p>
          <p className="upload-zone-hint">Supports .pdf and .docx &mdash; max 50 MB</p>
        </div>
      )}

      {error && <p className="upload-error">{error}</p>}
    </div>
  )
}
