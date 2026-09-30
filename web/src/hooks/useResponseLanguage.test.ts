import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useResponseLanguage } from './useResponseLanguage'

describe('useResponseLanguage', () => {
  it('defaults to English', () => {
    const { result } = renderHook(() => useResponseLanguage())
    expect(result.current[0]).toBe('en')
  })

  it('persists the selection', () => {
    const { result } = renderHook(() => useResponseLanguage())

    act(() => result.current[1]('es'))

    expect(result.current[0]).toBe('es')
    expect(localStorage.getItem('response-language')).toBe('es')
  })

  it('restores a saved language', () => {
    localStorage.setItem('response-language', 'es')
    const { result } = renderHook(() => useResponseLanguage())
    expect(result.current[0]).toBe('es')
  })

  it('ignores an unsupported saved value', () => {
    localStorage.setItem('response-language', 'fr')
    const { result } = renderHook(() => useResponseLanguage())
    expect(result.current[0]).toBe('en')
  })
})
