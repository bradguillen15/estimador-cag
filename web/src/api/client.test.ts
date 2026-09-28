import { beforeEach, describe, expect, it, vi } from 'vitest'

import { chunkedResponse, DONE_META, jsonResponse, REQUEST } from '../test/fixtures'
import { ApiError, checkHealth, createEstimate, getPromptContext, streamEstimate } from './client'
import type { StreamEvent } from './types'

const fetchMock = vi.fn<typeof fetch>()

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockReset()
})

async function collect(stream: AsyncGenerator<StreamEvent>): Promise<StreamEvent[]> {
  const events: StreamEvent[] = []
  for await (const event of stream) events.push(event)
  return events
}

describe('createEstimate', () => {
  it('posts the request as JSON and returns the parsed response', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ text: '## Estimación', prompt_version: 'v1' }))

    await expect(createEstimate(REQUEST)).resolves.toEqual({ text: '## Estimación', prompt_version: 'v1' })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/estimate')
    expect(init?.method).toBe('POST')
    expect(JSON.parse(init?.body as string)).toEqual(REQUEST)
  })

  it('surfaces the API detail message with the status code', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'El proveedor LLM tardó demasiado en responder.' }, 502))

    const error = await createEstimate(REQUEST).catch((reason: unknown) => reason)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 502,
      message: 'Error HTTP 502: El proveedor LLM tardó demasiado en responder.',
    })
  })

  it('summarises FastAPI validation errors', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: [{ loc: ['body', 'description'], msg: 'String should have at least 20 characters' }] }, 422),
    )

    await expect(createEstimate(REQUEST)).rejects.toThrow(
      'Error HTTP 422: description: String should have at least 20 characters',
    )
  })

  it('falls back to the status text when the error body is not JSON', async () => {
    fetchMock.mockResolvedValue(new Response('<html>oops</html>', { status: 500, statusText: 'Internal Server Error' }))
    await expect(createEstimate(REQUEST)).rejects.toThrow('Error HTTP 500: Internal Server Error')
  })

  it('explains how to start the API when the network request fails', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(createEstimate(REQUEST)).rejects.toThrow(/No se pudo conectar a la API.*uv run uvicorn/)
  })

  it('lets aborts propagate untouched so callers can ignore them', async () => {
    fetchMock.mockRejectedValue(new DOMException('aborted', 'AbortError'))
    await expect(createEstimate(REQUEST)).rejects.toMatchObject({ name: 'AbortError' })
  })
})

describe('streamEstimate', () => {
  it('yields tokens verbatim (spaces and newlines included) and the done metadata', async () => {
    fetchMock.mockResolvedValue(
      chunkedResponse([
        'event: token\ndata: "## Estimación"\n\n',
        'event: token\ndata: "\\n\\n  - con espacios "\n\n',
        `event: done\ndata: ${JSON.stringify(DONE_META)}\n\n`,
      ]),
    )

    await expect(collect(streamEstimate(REQUEST))).resolves.toEqual([
      { type: 'token', text: '## Estimación' },
      { type: 'token', text: '\n\n  - con espacios ' },
      { type: 'done', meta: DONE_META },
    ])
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/estimate/stream')
    expect(new Headers(init?.headers).get('Accept')).toBe('text/event-stream')
  })

  it('reassembles events split across network chunks and CRLF line endings', async () => {
    fetchMock.mockResolvedValue(chunkedResponse(['event: tok', 'en\r\ndata: "Ho', 'la"\r\n', '\r\n: ping\r\n\r\n']))

    await expect(collect(streamEstimate(REQUEST))).resolves.toEqual([{ type: 'token', text: 'Hola' }])
  })

  it('maps error events to a typed error', async () => {
    fetchMock.mockResolvedValue(chunkedResponse(['event: error\ndata: {"detail": "Rate limit"}\n\n']))
    await expect(collect(streamEstimate(REQUEST))).resolves.toEqual([{ type: 'error', detail: 'Rate limit' }])
  })

  it('ignores unknown event types', async () => {
    fetchMock.mockResolvedValue(chunkedResponse(['event: progress\ndata: 42\n\nevent: token\ndata: "x"\n\n']))
    await expect(collect(streamEstimate(REQUEST))).resolves.toEqual([{ type: 'token', text: 'x' }])
  })

  it('throws the API error when the stream request is rejected', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: [{ loc: ['body', 'output_format'], msg: 'Input should be…' }] }, 422))
    await expect(collect(streamEstimate(REQUEST))).rejects.toMatchObject({ status: 422 })
  })
})

describe('checkHealth and getPromptContext', () => {
  it('reports whether the API answers /health', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ status: 'ok' }))
    fetchMock.mockResolvedValueOnce(new Response('', { status: 503 }))
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    expect(await checkHealth()).toBe(true)
    expect(await checkHealth()).toBe(false)
    expect(await checkHealth()).toBe(false)
  })

  it('loads the CAG context', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ prompt_version: 'v1', examples_markdown: '### Ejemplo 1' }))
    await expect(getPromptContext()).resolves.toEqual({ prompt_version: 'v1', examples_markdown: '### Ejemplo 1' })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/context')
  })
})
