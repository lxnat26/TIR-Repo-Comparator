const API_BASE = (import.meta.env.VITE_API_URL as string) ?? ''

// ─── Document types ───────────────────────────────────────────────────────────

export type DocumentStatus = 'processing' | 'ready' | 'error'
export type FileType = 'pdf' | 'docx'

export interface ReportDocument {
  id: string
  filename: string
  file_type: FileType
  uploaded_at: string
  status: DocumentStatus
  chunk_count?: number
  size_bytes?: number
}

// ─── Claim types (mirrors raw backend JSON) ───────────────────────────────────

export type ClaimType   = 'milestone' | 'efficacy' | 'safety'
export type ClaimStatus = 'new_information' | 'refined_detail' | 'already_reported'

export interface ClaimResult {
  id:               string
  claim_type:       ClaimType
  specific_type:    string
  claim:            string   // "What's new" — the draft claim text
  historical_claim: string   // "Previously reported" — matched historical text
  report_date:      string   // formatted e.g. "Sep 2024"
  classification:   ClaimStatus
  reason:           string   // "Why it matters"
}

export interface AnalysisResult {
  claim_count:   number
  claims:        ClaimResult[]
  analyzed_at:   string
  document_text?: string
}

// ─── Client-side mapping from raw backend shape ───────────────────────────────

const _STATUS_MAP: Record<string, ClaimStatus> = {
  'Already Reported': 'already_reported',
  'Refined Detail':   'refined_detail',
  'New Information':  'new_information',
}

const _VALID_TYPES: ClaimType[] = ['milestone', 'efficacy', 'safety']

function _formatDate(raw: string): string {
  if (!raw || raw === 'Unknown') return ''
  try {
    const parts = raw.split('-')
    const y = parseInt(parts[0])
    const m = parseInt(parts[1] ?? '7') - 1
    const d = new Date(y, m, 1)
    return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
  } catch {
    return raw
  }
}

function _mapClaim(c: Record<string, string>, i: number): ClaimResult {
  return {
    id:               `claim-${i}`,
    claim_type:       _VALID_TYPES.includes(c.claim_type as ClaimType) ? (c.claim_type as ClaimType) : 'milestone',
    specific_type:    c.specific_type ?? '',
    claim:            c.claim ?? '',
    historical_claim: c.historical_claim ?? '',
    report_date:      _formatDate(c.report_date ?? ''),
    classification:   _STATUS_MAP[c.classification] ?? 'already_reported',
    reason:           c.reason ?? '',
  }
}

function _mapResponse(data: Record<string, unknown>): AnalysisResult {
  const raw = (data.claims as Record<string, string>[] | undefined) ?? []
  const claims = raw.map(_mapClaim)
  return {
    claim_count:   claims.length,
    claims,
    analyzed_at:   (data.analyzed_at as string) ?? '',
    document_text: data.document_text as string | undefined,
  }
}

// ─── Document repository endpoints ───────────────────────────────────────────

export async function uploadDocument(file: File): Promise<ReportDocument> {
  const body = new FormData()
  body.append('file', file)
  const res = await fetch(`${API_BASE}/api/documents/upload`, { method: 'POST', body })
  if (!res.ok) {
    const msg = await res.text().catch(() => '')
    throw new Error(msg || `Upload failed (${res.status})`)
  }
  return res.json() as Promise<ReportDocument>
}

export async function listDocuments(): Promise<ReportDocument[]> {
  const res = await fetch(`${API_BASE}/api/documents`)
  if (!res.ok) throw new Error(`Could not load documents (${res.status})`)
  return res.json() as Promise<ReportDocument[]>
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Delete failed (${res.status})`)
}

// ─── Analysis endpoints ───────────────────────────────────────────────────────

export async function analyzeDocument(
  file: File,
  metadata?: { competitor?: string; drug?: string },
): Promise<AnalysisResult> {
  const body = new FormData()
  body.append('file', file)
  if (metadata?.competitor) body.append('competitor', metadata.competitor)
  if (metadata?.drug)       body.append('drug',       metadata.drug)
  const res = await fetch(`${API_BASE}/api/analyze/document`, { method: 'POST', body })
  if (!res.ok) {
    const msg = await res.text().catch(() => '')
    throw new Error(msg || `Analysis failed (${res.status})`)
  }
  return _mapResponse(await res.json() as Record<string, unknown>)
}

export async function analyzeDraft(payload: {
  text: string
  metadata?: { competitor?: string; drug?: string }
}): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text:       payload.text,
      competitor: payload.metadata?.competitor,
      drug:       payload.metadata?.drug,
    }),
  })
  if (!res.ok) {
    const msg = await res.text().catch(() => '')
    throw new Error(msg || `Analysis failed (${res.status})`)
  }
  return _mapResponse(await res.json() as Record<string, unknown>)
}
