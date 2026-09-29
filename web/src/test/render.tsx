import { render } from '@testing-library/react'
import type { ReactElement, ReactNode } from 'react'

import type { Locale } from '../i18n/messages'
import { LocaleProvider } from '../i18n/LocaleContext'
import { setLocale } from '../i18n/locale'

/** Wrap UI under test with the same locale provider the app uses. */
export function withLocale(ui: ReactElement, locale: Locale = 'es') {
  setLocale(locale)
  return render(ui, {
    wrapper: ({ children }: { children: ReactNode }) => <LocaleProvider locale={locale}>{children}</LocaleProvider>,
  })
}
