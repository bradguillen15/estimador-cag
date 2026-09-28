import { useEffect, useMemo } from 'react'
import type { ReactNode } from 'react'

import { LocaleContext } from './context'
import { setLocale } from './locale'
import type { Locale, MessageKey } from './messages'
import { translate } from './messages'

export function LocaleProvider({ locale, children }: { locale: Locale; children: ReactNode }) {
  setLocale(locale)

  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])

  const value = useMemo(
    () => ({
      locale,
      t: (key: MessageKey, vars?: Record<string, string | number>) => translate(locale, key, vars),
    }),
    [locale],
  )

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}
