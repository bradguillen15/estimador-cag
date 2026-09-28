import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { checkHealth, createEstimate, getPromptContext, streamEstimate } from './api/client'
import { DONE_META, streamOf } from './test/fixtures'

vi.mock('./api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api/client')>()),
  checkHealth: vi.fn(),
  getPromptContext: vi.fn(),
  createEstimate: vi.fn(),
  streamEstimate: vi.fn(),
}))

const DESCRIPTION = 'App móvil para reservar clases en un gimnasio.'

beforeEach(() => {
  vi.mocked(checkHealth).mockResolvedValue(true)
  vi.mocked(getPromptContext).mockResolvedValue({ prompt_version: 'v1', examples_markdown: '' })
})

async function fillForm() {
  const user = userEvent.setup()
  render(<App />)
  await user.type(screen.getByLabelText(/descripción del proyecto/i), DESCRIPTION)
  return user
}

describe('App', () => {
  it('uses the JSON endpoint by default and shows the estimation', async () => {
    vi.mocked(createEstimate).mockResolvedValue({ text: '## Estimación: Gimnasio', prompt_version: 'v1' })
    const user = await fillForm()

    await user.click(screen.getByRole('button', { name: 'Generar estimación' }))

    expect(await screen.findByRole('heading', { name: 'Estimación: Gimnasio' })).toBeInTheDocument()
    expect(createEstimate).toHaveBeenCalledWith(expect.objectContaining({ description: DESCRIPTION }), expect.any(AbortSignal))
    expect(streamEstimate).not.toHaveBeenCalled()
  })

  it('uses the streaming endpoint when the sidebar switch is on', async () => {
    vi.mocked(streamEstimate).mockReturnValue(
      streamOf({ type: 'token', text: '## Estimación: ' }, { type: 'token', text: 'Streaming' }, { type: 'done', meta: DONE_META }),
    )
    const user = await fillForm()

    await user.click(screen.getByRole('switch', { name: /streaming/i }))
    await user.click(screen.getByRole('button', { name: 'Generar estimación' }))

    expect(await screen.findByRole('heading', { name: 'Estimación: Streaming' })).toBeInTheDocument()
    expect(screen.getByText('gpt-4o-mini')).toBeInTheDocument()
    expect(createEstimate).not.toHaveBeenCalled()
  })

  it('shows API failures and lets the user retry', async () => {
    vi.mocked(createEstimate)
      .mockRejectedValueOnce(new Error('Error HTTP 502: El proveedor LLM tardó demasiado en responder.'))
      .mockResolvedValueOnce({ text: '## Estimación: Reintento', prompt_version: 'v1' })
    const user = await fillForm()
    const submit = screen.getByRole('button', { name: 'Generar estimación' })

    await user.click(submit)
    expect(await screen.findByRole('alert')).toHaveTextContent('tardó demasiado')
    expect(submit).toBeEnabled()

    await user.click(submit)
    expect(await screen.findByRole('heading', { name: 'Estimación: Reintento' })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
