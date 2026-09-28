import type { EstimationRequest, GenerationMeta, StreamEvent } from '../api/types'

export const REQUEST: EstimationRequest = {
  description: 'Portal interno para reservar salas con calendario.',
  project_type: 'web_saas',
  detail_level: 'medium',
  output_format: 'line_items',
  language: 'es',
}

export const DONE_META: GenerationMeta = {
  model: 'gpt-4o-mini',
  provider: 'openai',
  input_tokens: 3184,
  output_tokens: 412,
  latency_seconds: 4.2,
  prompt_version: 'v1',
}

/** Builds an async iterable like `streamEstimate` returns. */
export async function* streamOf(...events: StreamEvent[]): AsyncGenerator<StreamEvent> {
  for (const event of events) yield event
}

/** A `fetch` Response whose body arrives in the given raw chunks (to exercise SSE buffering). */
export function chunkedResponse(chunks: string[], init: ResponseInit = { status: 200 }): Response {
  const encoder = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  })
  return new Response(body, init)
}

export const jsonResponse = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
