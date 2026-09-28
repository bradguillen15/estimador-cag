import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useResponseLanguage } from './useResponseLanguage'

describe('useResponseLanguage', () => {
  it('defaults to Spanish', () => {
    const { result } = renderHook(() => useResponseLanguage())
    expect(result.current[0]).toBe('es')
  })

  it('persists the selection', () => {
    const { result } = renderHook(() => useResponseLanguage())

    act(() => result.current[1]('en'))

    expect(result.current[0]).toBe('en')
    expect(localStorage.getItem('response-language')).toBe('en')
  })

  it('restores a saved language', () => {
    localStorage.setItem('response-language', 'en')
    const { result } = renderHook(() => useResponseLanguage())
    expect(result.current[0]).toBe('en')
  })

  it('ignores an unsupported saved value', () => {
    localStorage.setItem('response-language', 'fr')
    const { result } = renderHook(() => useResponseLanguage())
    expect(result.current[0]).toBe('es')
  })
})
