import { useCallback, useEffect, useRef, useState } from 'react'

import { createEstimate, streamEstimate } from '../api/client'
import type { EstimationRequest, GenerationMeta } from '../api/types'

export type EstimationStatus = 'idle' | 'loading' | 'streaming' | 'done' | 'error'

export interface EstimationState {
  status: EstimationStatus
  text: string
  meta: GenerationMeta | null
  error: string | null
}

const IDLE: EstimationState = { status: 'idle', text: '', meta: null, error: null }

const isAbort = (error: unknown): boolean => error instanceof DOMException && error.name === 'AbortError'

/** Runs an estimation against /estimate (JSON) or /estimate/stream (SSE). A new run aborts the previous one. */
export function useEstimation() {
  const [state, setState] = useState<EstimationState>(IDLE)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  const run = useCallback(async (request: EstimationRequest, stream: boolean) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setState({ ...IDLE, status: stream ? 'streaming' : 'loading' })

    try {
      if (!stream) {
        const response = await createEstimate(request, controller.signal)
        setState({ status: 'done', text: response.text, meta: { prompt_version: response.prompt_version, cache_hit: response.cache_hit }, error: null })
        return
      }

      // Tokens arrive far faster than the screen refreshes: render at most once per frame.
      let text = ''
      let frame = 0
      const flush = () => {
        frame = 0
        if (controller.signal.aborted) return
        setState((current) => ({ ...current, text }))
      }

      for await (const event of streamEstimate(request, controller.signal)) {
        if (event.type === 'token') {
          text += event.text
          if (!frame) frame = requestAnimationFrame(flush)
        } else if (event.type === 'done') {
          cancelAnimationFrame(frame)
          setState({ status: 'done', text, meta: event.meta, error: null })
        } else {
          cancelAnimationFrame(frame)
          setState({ ...IDLE, status: 'error', error: event.detail })
          return
        }
      }

      cancelAnimationFrame(frame)
      setState((current) => (current.status === 'streaming' ? { ...current, status: 'done', text } : current))
    } catch (error) {
      if (isAbort(error)) return
      setState({ ...IDLE, status: 'error', error: error instanceof Error ? error.message : String(error) })
    }
  }, [])

  return { state, run }
}
