import { useEffect, useState } from 'react'

import { DEFAULT_RESPONSE_LANGUAGE, RESPONSE_LANGUAGES } from '../api/types'
import type { ResponseLanguage } from '../api/types'

const STORAGE_KEY = 'response-language'

const isResponseLanguage = (value: unknown): value is ResponseLanguage =>
  RESPONSE_LANGUAGES.some((language) => language === value)

function readStoredLanguage(): ResponseLanguage {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return isResponseLanguage(stored) ? stored : DEFAULT_RESPONSE_LANGUAGE
  } catch {
    return DEFAULT_RESPONSE_LANGUAGE
  }
}

/**
 * UI locale and model response language (same toggle).
 * Spanish by default; persisted across reloads.
 */
export function useResponseLanguage(): [ResponseLanguage, (language: ResponseLanguage) => void] {
  const [language, setLanguage] = useState<ResponseLanguage>(readStoredLanguage)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, language)
    } catch {
      // Storage blocked (private mode): the choice just won't persist.
    }
  }, [language])

  return [language, setLanguage]
}
