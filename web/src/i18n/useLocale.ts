import { useContext } from 'react'

import { LocaleContext } from './context'
import type { Locale } from './messages'

export function useLocale(): Locale {
  const ctx = useContext(LocaleContext)
  if (!ctx) throw new Error('useLocale must be used within LocaleProvider')
  return ctx.locale
}

export function useT() {
  const ctx = useContext(LocaleContext)
  if (!ctx) throw new Error('useT must be used within LocaleProvider')
  return ctx.t
}
