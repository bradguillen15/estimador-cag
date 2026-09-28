import { t } from '../i18n/locale'
import type { EstimationRequest, EstimationResponse, GenerationMeta, PromptContext, StreamEvent } from './types'

/** Empty = same origin (Vite proxy in dev, FastAPI serving web/dist in prod). */
const API_BASE: string = import.meta.env.VITE_API_URL ?? ''

export const API_LABEL = API_BASE || window.location.origin

export class ApiError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, init)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(t('error.connect', { api: API_LABEL }))
  }
  if (!response.ok) throw await toApiError(response)
  return response
}

async function toApiError(response: Response): Promise<ApiError> {
  let detail = response.statusText
  try {
    const body: { detail?: unknown } = await response.json()
    detail = formatDetail(body.detail) ?? detail
  } catch {
    // Non-JSON error body: keep the status text.
  }
  return new ApiError(t('error.http', { status: response.status, detail }), response.status)
}

/** FastAPI returns a string for HTTPException and a list of issues for 422s. */
function formatDetail(detail: unknown): string | undefined {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((issue: { loc?: unknown[]; msg?: string }) => `${issue.loc?.at(-1) ?? ''}: ${issue.msg}`).join('; ')
  }
  return undefined
}

const jsonInit = (body: unknown, signal?: AbortSignal): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
  signal,
})

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`)
    return response.ok
  } catch {
    return false
  }
}

export async function getPromptContext(): Promise<PromptContext> {
  const response = await send('/api/v1/context')
  return response.json()
}

export async function createEstimate(body: EstimationRequest, signal?: AbortSignal): Promise<EstimationResponse> {
  const response = await send('/api/v1/estimate', jsonInit(body, signal))
  return response.json()
}

/** POST /api/v1/estimate/stream and yield its SSE events (EventSource can't POST). */
export async function* streamEstimate(body: EstimationRequest, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
  const response = await send('/api/v1/estimate/stream', {
    ...jsonInit(body, signal),
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
  })
  if (!response.body) throw new ApiError(t('error.streamEmpty'))

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value.replace(/\r\n?/g, '\n')

    let boundary: number
    while ((boundary = buffer.indexOf('\n\n')) !== -1) {
      const event = parseEvent(buffer.slice(0, boundary))
      buffer = buffer.slice(boundary + 2)
      if (event) yield event
    }
  }
}

function parseEvent(block: string): StreamEvent | null {
  let name = 'message'
  const data: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith(':')) continue // keep-alive comment
    const colon = line.indexOf(':')
    const field = colon === -1 ? line : line.slice(0, colon)
    let value = colon === -1 ? '' : line.slice(colon + 1)
    if (value.startsWith(' ')) value = value.slice(1)
    if (field === 'event') name = value
    else if (field === 'data') data.push(value)
  }
  if (data.length === 0) return null

  // The server JSON-encodes every payload, so spaces and newlines inside tokens survive.
  const payload: unknown = JSON.parse(data.join('\n'))
  switch (name) {
    case 'token':
      return { type: 'token', text: payload as string }
    case 'done':
      return { type: 'done', meta: payload as GenerationMeta }
    case 'error':
      return { type: 'error', detail: (payload as { detail?: string }).detail ?? t('error.unknown') }
    default:
      return null
  }
}
