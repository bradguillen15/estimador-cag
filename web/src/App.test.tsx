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
  // The app defaults to English; most tests here assert the Spanish copy, so start from a saved 'es'.
  localStorage.setItem('response-language', 'es')
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

  it('sends the saved language and the newly selected language on the next request', async () => {
    vi.mocked(createEstimate).mockResolvedValue({ text: '## Estimación: Gimnasio', prompt_version: 'v2' })
    const user = await fillForm()

    await user.click(screen.getByRole('button', { name: 'Generar estimación' }))
    await screen.findByRole('heading', { name: 'Estimación: Gimnasio' })
    expect(createEstimate).toHaveBeenLastCalledWith(expect.objectContaining({ language: 'es' }), expect.any(AbortSignal))

    await user.click(screen.getByRole('radio', { name: /English/ }))
    await user.click(screen.getByRole('button', { name: 'Generate estimate' }))
    expect(createEstimate).toHaveBeenLastCalledWith(expect.objectContaining({ language: 'en' }), expect.any(AbortSignal))
  })

  it('starts in English and dark with a fresh browser (no saved preferences)', async () => {
    localStorage.clear()
    vi.mocked(createEstimate).mockResolvedValue({ text: '## Estimate: Gym', prompt_version: 'v3' })
    const user = userEvent.setup()
    render(<App />)

    expect(screen.getByRole('radio', { name: /English/ })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Dark' })).toBeChecked()
    expect(document.documentElement.lang).toBe('en')
    expect(document.documentElement.dataset.theme).toBe('dark')

    await user.type(screen.getByLabelText(/project description/i), DESCRIPTION)
    await user.click(screen.getByRole('button', { name: 'Generate estimate' }))
    expect(createEstimate).toHaveBeenLastCalledWith(expect.objectContaining({ language: 'en' }), expect.any(AbortSignal))
  })

  it('switches the visible UI copy when the language changes', async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Estimador de/)
    expect(screen.getByRole('button', { name: 'Generar estimación' })).toBeInTheDocument()

    await user.click(screen.getByRole('radio', { name: /English/ }))

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/Software/)
    expect(screen.getByRole('button', { name: 'Generate estimate' })).toBeInTheDocument()
    expect(screen.getByLabelText(/project description/i)).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('en')
  })

  it('includes the language in streaming requests too', async () => {
    vi.mocked(streamEstimate).mockReturnValue(streamOf({ type: 'done', meta: DONE_META }))
    const user = await fillForm()

    await user.click(screen.getByRole('radio', { name: /English/ }))
    await user.click(screen.getByRole('switch', { name: /streaming/i }))
    await user.click(screen.getByRole('button', { name: 'Generate estimate' }))

    expect(streamEstimate).toHaveBeenCalledWith(expect.objectContaining({ language: 'en' }), expect.any(AbortSignal))
  })

  it('remembers the response language after a reload', async () => {
    const user = userEvent.setup()
    const { unmount } = render(<App />)
    await user.click(screen.getByRole('radio', { name: /English/ }))
    unmount()

    render(<App />)

    expect(screen.getByRole('radio', { name: /English/ })).toBeChecked()
    expect(screen.getByRole('button', { name: 'Generate estimate' })).toBeInTheDocument()
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
