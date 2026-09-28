import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { EstimationState } from '../hooks/useEstimation'
import { DONE_META } from '../test/fixtures'
import { EstimationResult } from './EstimationResult'

const MARKDOWN = `## Estimación: Reservas

| Fase | Horas |
|---|---|
| Diseño | 32 |

**Total estimado: 232 horas**
**Duración estimada: 3-4 semanas**`

const state = (overrides: Partial<EstimationState>): EstimationState => ({
  status: 'idle',
  text: '',
  meta: null,
  error: null,
  ...overrides,
})

describe('EstimationResult', () => {
  it('renders nothing before the first request', () => {
    const { container } = render(<EstimationResult state={state({})} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows a busy placeholder while waiting for a JSON response', () => {
    render(<EstimationResult state={state({ status: 'loading' })} />)

    expect(screen.getByLabelText('Generando estimación')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Estimación' })).toHaveAttribute('aria-busy', 'true')
  })

  it('renders partial text while streaming', () => {
    render(<EstimationResult state={state({ status: 'streaming', text: '## Estimación: Res' })} />)

    expect(screen.getByRole('heading', { name: 'Estimación: Res' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Estimación' })).toHaveAttribute('aria-busy', 'true')
  })

  it('renders the finished Markdown (tables, separate closing lines) and the generation metadata', () => {
    render(<EstimationResult state={state({ status: 'done', text: MARKDOWN, meta: DONE_META })} />)

    expect(screen.getByRole('heading', { name: 'Estimación: Reservas' })).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getByText('Diseño')).toBeInTheDocument()
    const total = screen.getByText('Total estimado: 232 horas')
    // The closing lines must not collapse into one paragraph.
    expect(total.nextElementSibling?.tagName).toBe('BR')

    expect(screen.getByText('v1')).toBeInTheDocument()
    expect(screen.getByText('gpt-4o-mini')).toBeInTheDocument()
    expect(screen.getByText('3184→412 tok · 4.20s')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Estimación' })).toHaveAttribute('aria-busy', 'false')
  })

  it('shows only the prompt version when the JSON endpoint gives no usage data', () => {
    render(<EstimationResult state={state({ status: 'done', text: 'Hecho', meta: { prompt_version: 'v1' } })} />)

    expect(screen.getByText('v1')).toBeInTheDocument()
    expect(screen.queryByText(/tok/)).not.toBeInTheDocument()
  })

  it('shows errors as an alert', () => {
    render(<EstimationResult state={state({ status: 'error', error: 'Error HTTP 502: El proveedor LLM falló.' })} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Error HTTP 502: El proveedor LLM falló.')
  })
})
