import { useEffect, useState } from 'react'
import { listDocuments, deleteDocument, ReportDocument } from '../api'
import { UploadZone } from './UploadZone'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function FileTypeBadge({ type }: { type: string }) {
  return (
    <span className={`file-type-badge file-type-${type}`}>
      {type.toUpperCase()}
    </span>
  )
}

function StatusBadge({ status }: { status: ReportDocument['status'] }) {
  const labels: Record<ReportDocument['status'], string> = {
    ready: 'Ready',
    processing: 'Processing',
    error: 'Error',
  }
  return (
    <span className={`status-badge status-badge--${status}`}>
      {status === 'processing' && (
        <span className="status-dot status-dot--pulse" aria-hidden="true" />
      )}
      {labels[status]}
    </span>
  )
}

export function ReportLibrary() {
  const [documents, setDocuments] = useState<ReportDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setFetchError(null)
    try {
      const docs = await listDocuments()
      setDocuments(docs)
    } catch (e) {
      setFetchError(
        e instanceof Error ? e.message : 'Could not load documents. Is the backend running?'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function onUploadComplete(doc: ReportDocument) {
    setDocuments((prev) => [doc, ...prev])
  }

  async function onDelete(id: string) {
    setDeletingId(id)
    try {
      await deleteDocument(id)
      setDocuments((prev) => prev.filter((d) => d.id !== id))
    } catch {
      // Keep the row — deletion failed silently; backend should log it
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="library">
      <div className="library-header">
        <div>
          <h1 className="page-title">Report Library</h1>
          <p className="page-subtitle">
            Upload past competitive intelligence reports. Each document is chunked and
            embedded into the reference database so the Coverage Assistant can compare
            new drafts against prior coverage.
          </p>
        </div>
        <button className="btn btn-ghost" onClick={load} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      <UploadZone onUploadComplete={onUploadComplete} />

      <div className="library-table-wrap">
        <div className="library-table-header">
          <span>Document</span>
          <span>Size</span>
          <span>Uploaded</span>
          <span>Chunks</span>
          <span>Status</span>
          <span />
        </div>

        {loading && (
          <div className="library-state">
            <div className="panel-spinner" />
            <span>Loading documents...</span>
          </div>
        )}

        {!loading && fetchError && (
          <div className="library-state library-state--error">
            {fetchError}
          </div>
        )}

        {!loading && !fetchError && documents.length === 0 && (
          <div className="library-state">
            No documents in the library yet. Upload a past CI report to get started.
          </div>
        )}

        {!loading && !fetchError &&
          documents.map((doc) => (
            <div key={doc.id} className="library-row">
              <div className="library-row-file">
                <FileTypeBadge type={doc.file_type} />
                <span className="library-filename" title={doc.filename}>
                  {doc.filename}
                </span>
              </div>
              <span className="library-cell">
                {doc.size_bytes != null ? formatBytes(doc.size_bytes) : '—'}
              </span>
              <span className="library-cell">{formatDate(doc.uploaded_at)}</span>
              <span className="library-cell">{doc.chunk_count ?? '—'}</span>
              <span className="library-cell">
                <StatusBadge status={doc.status} />
              </span>
              <span className="library-cell library-cell--action">
                <button
                  className="btn btn-ghost btn-sm btn-danger"
                  onClick={() => onDelete(doc.id)}
                  disabled={deletingId === doc.id}
                >
                  {deletingId === doc.id ? 'Removing...' : 'Remove'}
                </button>
              </span>
            </div>
          ))}
      </div>
    </div>
  )
}
