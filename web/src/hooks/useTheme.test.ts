import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useTheme } from './useTheme'

describe('useTheme', () => {
  it('defaults to dark', () => {
    const { result } = renderHook(() => useTheme())
    expect(result.current[0]).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('starts from the light theme applied before first paint', () => {
    document.documentElement.dataset.theme = 'light'
    const { result } = renderHook(() => useTheme())
    expect(result.current[0]).toBe('light')
  })

  it('applies and persists the selected theme', () => {
    const { result } = renderHook(() => useTheme())

    act(() => result.current[1]('light'))
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(localStorage.getItem('theme')).toBe('light')

    act(() => result.current[1]('dark'))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('theme')).toBe('dark')
  })
})
