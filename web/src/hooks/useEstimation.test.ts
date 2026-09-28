import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, createEstimate, streamEstimate } from '../api/client'
import type { StreamEvent } from '../api/types'
import { DONE_META, REQUEST, streamOf } from '../test/fixtures'
import { useEstimation } from './useEstimation'

vi.mock('../api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/client')>()),
  createEstimate: vi.fn(),
  streamEstimate: vi.fn(),
}))

const createEstimateMock = vi.mocked(createEstimate)
const streamEstimateMock = vi.mocked(streamEstimate)

beforeEach(() => {
  createEstimateMock.mockReset()
  streamEstimateMock.mockReset()
})

describe('useEstimation', () => {
  it('starts idle', () => {
    const { result } = renderHook(() => useEstimation())
    expect(result.current.state).toEqual({ status: 'idle', text: '', meta: null, error: null })
  })

  it('shows loading, then the JSON result with its prompt version', async () => {
    let resolve!: (value: { text: string; prompt_version: string }) => void
    createEstimateMock.mockReturnValue(new Promise((r) => (resolve = r)))
    const { result } = renderHook(() => useEstimation())

    act(() => void result.current.run(REQUEST, false))
    expect(result.current.state.status).toBe('loading')

    await act(async () => resolve({ text: '## Estimación', prompt_version: 'v1' }))
    expect(result.current.state).toEqual({ status: 'done', text: '## Estimación', meta: { prompt_version: 'v1' }, error: null })
    expect(createEstimateMock).toHaveBeenCalledWith(REQUEST, expect.any(AbortSignal))
    expect(streamEstimateMock).not.toHaveBeenCalled()
  })

  it('accumulates streamed tokens and finishes with the done metadata', async () => {
    streamEstimateMock.mockReturnValue(
      streamOf({ type: 'token', text: '## Esti' }, { type: 'token', text: 'mación' }, { type: 'done', meta: DONE_META }),
    )
    const { result } = renderHook(() => useEstimation())

    await act(() => result.current.run(REQUEST, true))

    expect(result.current.state).toEqual({ status: 'done', text: '## Estimación', meta: DONE_META, error: null })
    expect(createEstimateMock).not.toHaveBeenCalled()
  })

  it('marks the stream done even if the server closes it without a done event', async () => {
    streamEstimateMock.mockReturnValue(streamOf({ type: 'token', text: 'parcial' }))
    const { result } = renderHook(() => useEstimation())

    await act(() => result.current.run(REQUEST, true))

    expect(result.current.state).toMatchObject({ status: 'done', text: 'parcial' })
  })

  it('turns a stream error event into an error state', async () => {
    streamEstimateMock.mockReturnValue(streamOf({ type: 'token', text: 'algo' }, { type: 'error', detail: 'Rate limit' }))
    const { result } = renderHook(() => useEstimation())

    await act(() => result.current.run(REQUEST, true))

    expect(result.current.state).toEqual({ status: 'error', text: '', meta: null, error: 'Rate limit' })
  })

  it('shows the message of a failed request', async () => {
    createEstimateMock.mockRejectedValue(new ApiError('Error HTTP 502: El proveedor LLM falló.', 502))
    const { result } = renderHook(() => useEstimation())

    await act(() => result.current.run(REQUEST, false))

    expect(result.current.state).toMatchObject({ status: 'error', error: 'Error HTTP 502: El proveedor LLM falló.' })
  })

  it('aborts the previous request when a new one starts and ignores the abort', async () => {
    const signals: AbortSignal[] = []
    createEstimateMock.mockImplementationOnce(
      (_request, signal) =>
        new Promise((_resolve, reject) => {
          signals.push(signal!)
          signal!.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')))
        }),
    )
    createEstimateMock.mockResolvedValueOnce({ text: 'segunda', prompt_version: 'v1' })
    const { result } = renderHook(() => useEstimation())

    act(() => void result.current.run(REQUEST, false))
    await act(() => result.current.run({ ...REQUEST, detail_level: 'detailed' }, false))

    expect(signals[0].aborted).toBe(true)
    await waitFor(() => expect(result.current.state).toMatchObject({ status: 'done', text: 'segunda' }))
  })

  it('renders streamed text progressively before the stream ends', async () => {
    let release!: () => void
    const gate = new Promise<void>((r) => (release = r))
    streamEstimateMock.mockReturnValue(
      (async function* (): AsyncGenerator<StreamEvent> {
        yield { type: 'token', text: 'Primera parte' }
        await gate
        yield { type: 'done', meta: DONE_META }
      })(),
    )
    const { result } = renderHook(() => useEstimation())

    act(() => void result.current.run(REQUEST, true))

    await waitFor(() => expect(result.current.state).toMatchObject({ status: 'streaming', text: 'Primera parte' }))
    await act(async () => release())
    await waitFor(() => expect(result.current.state.status).toBe('done'))
  })
})
