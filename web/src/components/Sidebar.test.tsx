import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { checkHealth, getPromptContext } from '../api/client'
import { Sidebar } from './Sidebar'

vi.mock('../api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/client')>()),
  checkHealth: vi.fn(),
  getPromptContext: vi.fn(),
}))

const checkHealthMock = vi.mocked(checkHealth)
const getPromptContextMock = vi.mocked(getPromptContext)

function renderSidebar(overrides: Partial<Parameters<typeof Sidebar>[0]> = {}) {
  const props = {
    streaming: false,
    onStreamingChange: vi.fn(),
    theme: 'light' as const,
    onThemeChange: vi.fn(),
    ...overrides,
  }
  render(<Sidebar {...props} />)
  return props
}

beforeEach(() => {
  checkHealthMock.mockResolvedValue(true)
  getPromptContextMock.mockResolvedValue({ prompt_version: 'v1', examples_markdown: '### Ejemplo 1 — Marketplace B2B' })
})

describe('Sidebar', () => {
  it('reports when the API is reachable', async () => {
    renderSidebar()
    expect(await screen.findByText('API disponible')).toBeInTheDocument()
  })

  it('reports when the API is down', async () => {
    checkHealthMock.mockResolvedValue(false)
    renderSidebar()
    expect(await screen.findByText('API no disponible')).toBeInTheDocument()
  })

  it('shows the CAG examples the server injects, with their prompt version', async () => {
    const user = userEvent.setup()
    renderSidebar()

    await user.click(screen.getByText('Ejemplos estáticos'))

    expect(await screen.findByRole('heading', { name: 'Ejemplo 1 — Marketplace B2B' })).toBeVisible()
    expect(screen.getByText('v1')).toBeInTheDocument()
  })

  it('explains why the examples could not be loaded', async () => {
    getPromptContextMock.mockRejectedValue(new Error('Error HTTP 500: Falta la plantilla'))
    renderSidebar()
    expect(await screen.findByText('Error HTTP 500: Falta la plantilla')).toBeInTheDocument()
  })

  it('toggles streaming and describes the endpoint in use', async () => {
    const user = userEvent.setup()
    const { onStreamingChange } = renderSidebar()
    expect(screen.getByText(/JSON — mismo formulario/)).toBeInTheDocument()

    await user.click(screen.getByRole('switch', { name: /streaming/i }))

    expect(onStreamingChange).toHaveBeenCalledWith(true)
  })

  it('reflects streaming mode when it is on', () => {
    renderSidebar({ streaming: true })
    expect(screen.getByRole('switch', { name: /streaming/i })).toBeChecked()
    expect(screen.getByText(/SSE — mismo formulario/)).toBeInTheDocument()
  })

  it('switches between light and dark themes', async () => {
    const user = userEvent.setup()
    const { onThemeChange } = renderSidebar()
    expect(screen.getByRole('radio', { name: 'Claro' })).toBeChecked()

    await user.click(screen.getByRole('radio', { name: 'Oscuro' }))

    expect(onThemeChange).toHaveBeenCalledWith('dark')
  })
})
