/**
 * API layer for Coverage Assistant
 *
 * All requests are sent to VITE_API_URL (defaults to "" which uses the
 * Vite dev-server proxy at /api → http://localhost:8000).
 *
 * Backend contract (FastAPI):
 *   POST   /api/documents/upload   multipart/form-data  { file }
 *   GET    /api/documents
 *   DELETE /api/documents/:id
 *   POST   /api/analyze            application/json     { text, metadata? }
 */

const API_BASE = (import.meta.env.VITE_API_URL as string) ?? ''

// ─── Types ────────────────────────────────────────────────────────────────────

export type DocumentStatus = 'processing' | 'ready' | 'error'
export type FileType = 'pdf' | 'docx'

export interface ReportDocument {
  id: string
  filename: string
  file_type: FileType
  uploaded_at: string   // ISO 8601
  status: DocumentStatus
  chunk_count?: number
  size_bytes?: number
}

export type ClaimCategory = 'milestone' | 'efficacy' | 'safety' | 'regulatory' | 'other'
export type ClaimStatus =
  | 'new_information'
  | 'refined_detail'
  | 'already_reported'
  | 'contradiction'
  | 'uncertainty'

export interface PreviouslyReported {
  date: string    // e.g. "Mar 15, 2023"
  source: string  // e.g. "XYZ Pharma Press Release"
  summary: string
}

export interface ClaimResult {
  id: string
  claim_text: string
  category: ClaimCategory
  status: ClaimStatus
  title: string
  previously_reported?: PreviouslyReported
  whats_new?: string
  why_it_matters: string
}

export interface AnalysisResult {
  claim_count: number
  claims: ClaimResult[]
  analyzed_at: string       // ISO 8601
  document_text?: string    // extracted plain text returned by the backend (optional)
}

// ─── Document repository endpoints ───────────────────────────────────────────

export async function uploadDocument(file: File): Promise<ReportDocument> {
  const body = new FormData()
  body.append('file', file)

  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: 'POST',
    body,
  })

  if (!res.ok) {
    const msg = await res.text().catch(() => '')
    throw new Error(msg || `Upload failed (${res.status})`)
  }

  return res.json() as Promise<ReportDocument>
}

export async function listDocuments(): Promise<ReportDocument[]> {
  const res = await fetch(`${API_BASE}/api/documents`)

  if (!res.ok) {
    throw new Error(`Could not load documents (${res.status})`)
  }

  return res.json() as Promise<ReportDocument[]>
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })

  if (!res.ok) {
    throw new Error(`Delete failed (${res.status})`)
  }
}

// ─── Draft document analysis endpoint ────────────────────────────────────────
//
// Backend contract (FastAPI):
//   POST /api/analyze/document   multipart/form-data
//     file        - the PDF or DOCX file
//     competitor  - (optional) string
//     drug        - (optional) string
//
//   Response: AnalysisResult (JSON)
//     document_text is optional — include it if the backend extracts the text,
//     and the frontend will display it in the left panel of the analysis view.

export async function analyzeDocument(
  file: File,
  metadata?: { competitor?: string; drug?: string },
): Promise<AnalysisResult> {
  const body = new FormData()
  body.append('file', file)
  if (metadata?.competitor) body.append('competitor', metadata.competitor)
  if (metadata?.drug)       body.append('drug',       metadata.drug)

  const res = await fetch(`${API_BASE}/api/analyze/document`, {
    method: 'POST',
    body,
  })

  if (!res.ok) {
    const msg = await res.text().catch(() => '')
    throw new Error(msg || `Analysis failed (${res.status})`)
  }

  return res.json() as Promise<AnalysisResult>
}

export async function analyzeDraft(payload: {
  text: string
  metadata?: { competitor?: string; drug?: string }
}): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: payload.text,
      competitor: payload.metadata?.competitor,
      drug: payload.metadata?.drug,
    }),
  })
  if (!res.ok) {
    const msg = await res.text().catch(() => '')
    throw new Error(msg || `Analysis failed (${res.status})`)
  }
  return res.json() as Promise<AnalysisResult>
}